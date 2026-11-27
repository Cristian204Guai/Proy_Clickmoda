import io
import shutil
import tempfile
from decimal import Decimal

from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import path
from rest_framework import status
from rest_framework.test import APITestCase

from apps.orders.models import Address, Order, OrderItem
from .admin_views import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminProductDetailView,
    AdminProductImageDeleteView,
    AdminProductImageUploadView,
    AdminProductListCreateView,
)
from .models import Category, Product, ProductImage, ProductVariant

User = get_user_model()

urlpatterns = [
    path(
        "api/v1/admin/categories/",
        AdminCategoryListCreateView.as_view(),
        name="admin-category-list",
    ),
    path(
        "api/v1/admin/categories/<int:pk>/",
        AdminCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
    path(
        "api/v1/admin/products/",
        AdminProductListCreateView.as_view(),
        name="admin-product-list",
    ),
    path(
        "api/v1/admin/products/<int:pk>/",
        AdminProductDetailView.as_view(),
        name="admin-product-detail",
    ),
    path(
        "api/v1/admin/products/<int:pk>/images/",
        AdminProductImageUploadView.as_view(),
        name="admin-product-image-upload",
    ),
    path(
        "api/v1/admin/products/<int:pk>/images/<int:image_id>/",
        AdminProductImageDeleteView.as_view(),
        name="admin-product-image-delete",
    ),
]


def _make_image_file(name="test.png", fmt="PNG", size=(20, 20), color=(30, 64, 175)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=fmt)
    buf.seek(0)
    content_type = {
        "PNG": "image/png",
        "WEBP": "image/webp",
        "JPEG": "image/jpeg",
    }[fmt]
    return SimpleUploadedFile(name, buf.read(), content_type=content_type)


@override_settings(ROOT_URLCONF="apps.catalog.tests_admin")
class AdminCatalogAPITests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media_dir = tempfile.mkdtemp(prefix="clickmoda_test_media_")
        cls._media_override = override_settings(MEDIA_ROOT=cls.temp_media_dir)
        cls._media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_override.disable()
        shutil.rmtree(cls.temp_media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@clickmoda.com",
            password="AdminPassword123!",
            nombre="Admin ClickModa",
            role=User.Role.ADMIN,
        )
        self.client_user = User.objects.create_user(
            email="cliente@clickmoda.com",
            password="ClientPassword123!",
            nombre="Cliente ClickModa",
            role=User.Role.CLIENTE,
        )
        self.cat_camisas = Category.objects.create(
            nombre="Camisas", slug="camisas", orden=1
        )
        self.cat_jeans = Category.objects.create(
            nombre="Jeans", slug="jeans", orden=2
        )

    def test_permissions_unauthenticated_and_non_admin(self):
        endpoints = [
            ("get", "/api/v1/admin/categories/"),
            ("post", "/api/v1/admin/categories/"),
            ("get", f"/api/v1/admin/categories/{self.cat_camisas.pk}/"),
            ("get", "/api/v1/admin/products/"),
            ("post", "/api/v1/admin/products/"),
        ]
        # Sin autenticar -> 401
        for method, url in endpoints:
            resp = getattr(self.client, method)(url)
            self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # Usuario rol CLIENTE -> 403
        self.client.force_authenticate(user=self.client_user)
        for method, url in endpoints:
            resp = getattr(self.client, method)(url)
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_category_crud_and_conflict_on_delete_with_products(self):
        self.client.force_authenticate(user=self.admin_user)

        # Listado ordenado con productos_count
        Product.objects.create(
            nombre="Camisa Lino",
            categoria=self.cat_camisas,
            precio_base=Decimal("89900"),
        )
        list_resp = self.client.get("/api/v1/admin/categories/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 2)
        self.assertEqual(list_resp.data[0]["nombre"], "Camisas")
        self.assertEqual(list_resp.data[0]["productos_count"], 1)

        # Crear categoría autogenerando slug
        create_resp = self.client.post(
            "/api/v1/admin/categories/",
            {"nombre": "Chaquetas Premium", "orden": 3},
            format="json",
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data["slug"], "chaquetas-premium")
        new_cat_id = create_resp.data["id"]

        # Validación de unicidad de nombre y slug
        dup_name = self.client.post(
            "/api/v1/admin/categories/",
            {"nombre": "Chaquetas Premium", "slug": "otro-slug"},
            format="json",
        )
        self.assertEqual(dup_name.status_code, status.HTTP_400_BAD_REQUEST)

        dup_slug = self.client.post(
            "/api/v1/admin/categories/",
            {"nombre": "Otra Categoria", "slug": "chaquetas-premium"},
            format="json",
        )
        self.assertEqual(dup_slug.status_code, status.HTTP_400_BAD_REQUEST)

        # Editar categoría
        patch_resp = self.client.patch(
            f"/api/v1/admin/categories/{new_cat_id}/",
            {"nombre": "Abrigos", "slug": "abrigos", "orden": 0},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data["nombre"], "Abrigos")
        self.assertEqual(patch_resp.data["slug"], "abrigos")

        # Borrar categoría con productos asociados -> 409 Conflict
        conflict_resp = self.client.delete(
            f"/api/v1/admin/categories/{self.cat_camisas.pk}/"
        )
        self.assertEqual(conflict_resp.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            conflict_resp.data["detail"],
            "No se puede eliminar la categoría porque tiene productos asociados.",
        )

        # Borrar categoría sin productos -> 204 No Content
        del_resp = self.client.delete(f"/api/v1/admin/categories/{new_cat_id}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=new_cat_id).exists())

    def test_product_crud_and_estado_filters(self):
        self.client.force_authenticate(user=self.admin_user)

        # Crear producto activo con stock
        create_payload = {
            "nombre": "Camisa Oxford",
            "descripcion": "Tela fresca 100% algodón",
            "categoria": self.cat_camisas.pk,
            "precio_base": 95000,
            "porcentaje_iva": 19,
            "activo": True,
            "variantes": [
                {"talla": "M", "color": "Azul", "color_hex": "#1D4ED8", "stock": 5},
                {"talla": "L", "color": "Blanco", "color_hex": "#FFFFFF", "stock": 0},
            ],
            "imagenes": [
                {"url": "https://cdn.clickmoda.com/oxford-1.jpg", "orden": 0},
            ],
        }
        create_resp = self.client.post(
            "/api/v1/admin/products/", create_payload, format="json"
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        prod_activo_id = create_resp.data["id"]
        self.assertEqual(create_resp.data["estado_display"], "Activo")
        self.assertEqual(create_resp.data["stock_total"], 5)
        self.assertEqual(create_resp.data["tallas_disponibles"], ["M"])
        self.assertEqual(len(create_resp.data["variantes"]), 2)
        self.assertTrue(create_resp.data["variantes"][0]["sku"])

        # Rechazar variantes duplicadas (talla, color)
        dup_var_resp = self.client.post(
            "/api/v1/admin/products/",
            {
                "nombre": "Camisa Duplicada",
                "categoria": self.cat_camisas.pk,
                "precio_base": 50000,
                "variantes": [
                    {"talla": "M", "color": "Negro", "stock": 2},
                    {"talla": "M", "color": "negro", "stock": 3},
                ],
            },
            format="json",
        )
        self.assertEqual(dup_var_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Producto agotado (activo=True, stock=0)
        prod_agotado = Product.objects.create(
            nombre="Jean Agotado",
            descripcion="Denim clásico",
            categoria=self.cat_jeans,
            precio_base=Decimal("120000"),
            activo=True,
        )
        ProductVariant.objects.create(
            producto=prod_agotado,
            talla="M",
            color="Azul",
            sku="CM-AGOTADO-1",
            stock=0,
        )

        # Producto inactivo
        prod_inactivo = Product.objects.create(
            nombre="Jean Descontinuado",
            descripcion="Modelo anterior",
            categoria=self.cat_jeans,
            precio_base=Decimal("90000"),
            activo=False,
        )
        ProductVariant.objects.create(
            producto=prod_inactivo,
            talla="L",
            color="Negro",
            sku="CM-INACTIVO-1",
            stock=10,
        )

        # Filtros por estado
        resp_activo = self.client.get("/api/v1/admin/products/?estado=activo")
        self.assertEqual(resp_activo.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [p["id"] for p in resp_activo.data["results"]], [prod_activo_id]
        )

        resp_agotado = self.client.get("/api/v1/admin/products/?estado=agotado")
        self.assertEqual(resp_agotado.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [p["id"] for p in resp_agotado.data["results"]], [prod_agotado.pk]
        )
        self.assertEqual(resp_agotado.data["results"][0]["estado_display"], "Agotado")

        resp_inactivo = self.client.get("/api/v1/admin/products/?estado=inactivo")
        self.assertEqual(resp_inactivo.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [p["id"] for p in resp_inactivo.data["results"]], [prod_inactivo.pk]
        )
        self.assertEqual(resp_inactivo.data["results"][0]["estado_display"], "Inactivo")

        # Filtro search y category (por slug e id)
        resp_search = self.client.get("/api/v1/admin/products/?search=algodón")
        self.assertEqual(resp_search.data["count"], 1)

        resp_cat = self.client.get(
            f"/api/v1/admin/products/?category={self.cat_jeans.pk}"
        )
        self.assertEqual(resp_cat.data["count"], 2)

        # PATCH conservando imagen real y actualizando URLs/variantes
        uploaded = ProductImage.objects.create(
            producto_id=prod_activo_id,
            imagen=_make_image_file("real.png", "PNG"),
            orden=1,
        )
        patch_resp = self.client.patch(
            f"/api/v1/admin/products/{prod_activo_id}/",
            {
                "nombre": "Camisa Oxford Slim",
                "imagenes": [
                    {"url": "https://cdn.clickmoda.com/oxford-2.jpg", "orden": 0},
                ],
            },
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data["nombre"], "Camisa Oxford Slim")
        self.assertTrue(ProductImage.objects.filter(pk=uploaded.pk).exists())
        self.assertEqual(
            ProductImage.objects.filter(producto_id=prod_activo_id).count(), 2
        )

        # DELETE producto sin órdenes -> 204 No Content
        del_resp = self.client.delete(f"/api/v1/admin/products/{prod_agotado.pk}/")
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=prod_agotado.pk).exists())

    def test_image_upload_validation_and_delete(self):
        self.client.force_authenticate(user=self.admin_user)
        product = Product.objects.create(
            nombre="Chaqueta Urbana",
            categoria=self.cat_camisas,
            precio_base=Decimal("159900"),
        )

        # Subida válida de PNG y WEBP
        png_file = _make_image_file("foto1.png", "PNG")
        webp_file = _make_image_file("foto2.webp", "WEBP")
        upload_resp = self.client.post(
            f"/api/v1/admin/products/{product.pk}/images/",
            {"imagenes": [png_file, webp_file]},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(upload_resp.data), 2)
        self.assertTrue(upload_resp.data[0]["es_archivo"])
        self.assertEqual(upload_resp.data[0]["orden"], 0)
        self.assertEqual(upload_resp.data[1]["orden"], 1)

        img_id = upload_resp.data[0]["id"]
        img_obj = ProductImage.objects.get(pk=img_id)
        stored_path = img_obj.imagen.path

        # Rechazo de archivo > 5 MB
        big_file = SimpleUploadedFile(
            "grande.png", b"0" * (5 * 1024 * 1024 + 1), content_type="image/png"
        )
        big_resp = self.client.post(
            f"/api/v1/admin/products/{product.pk}/images/",
            {"imagen": big_file},
            format="multipart",
        )
        self.assertEqual(big_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Rechazo de archivo de texto disfrazado de .jpg
        fake_jpg = SimpleUploadedFile(
            "falso.jpg", b"<html>not an image</html>", content_type="image/jpeg"
        )
        fake_resp = self.client.post(
            f"/api/v1/admin/products/{product.pk}/images/",
            {"imagen": fake_jpg},
            format="multipart",
        )
        self.assertEqual(fake_resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Eliminar imagen real borra registro y archivo físico
        del_img_resp = self.client.delete(
            f"/api/v1/admin/products/{product.pk}/images/{img_id}/"
        )
        self.assertEqual(del_img_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProductImage.objects.filter(pk=img_id).exists())
        self.assertFalse(img_obj.imagen.storage.exists(stored_path))

    def test_delete_product_with_order_item_deactivates_and_protects_variant(self):
        self.client.force_authenticate(user=self.admin_user)
        product = Product.objects.create(
            nombre="Pantalón Drill",
            categoria=self.cat_jeans,
            precio_base=Decimal("99900"),
            activo=True,
        )
        variant = ProductVariant.objects.create(
            producto=product,
            talla="M",
            color="Negro",
            sku="CM-ORD-01",
            stock=5,
        )
        address = Address.objects.create(
            user=self.client_user,
            nombre_completo="Cliente Prueba",
            telefono="3001234567",
            direccion="Calle 10 #20-30",
            ciudad="Pasto",
        )
        order = Order.objects.create(
            user=self.client_user,
            direccion_envio=address,
            subtotal=Decimal("99900"),
            impuestos=Decimal("18981"),
            total=Decimal("111900"),
        )
        OrderItem.objects.create(
            orden=order,
            variante=variant,
            nombre_producto=product.nombre,
            talla=variant.talla,
            color=variant.color,
            cantidad=1,
            precio_unitario=product.precio_base,
            porcentaje_iva=product.porcentaje_iva,
        )

        # Intentar quitar variante protegida vía PATCH -> 400 Bad Request
        patch_resp = self.client.patch(
            f"/api/v1/admin/products/{product.pk}/",
            {"variantes": []},
            format="json",
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(ProductVariant.objects.filter(pk=variant.pk).exists())

        # DELETE producto con OrderItem -> desactiva y responde 200 OK
        del_resp = self.client.delete(f"/api/v1/admin/products/{product.pk}/")
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(del_resp.data["deactivated"], True)
        product.refresh_from_db()
        self.assertFalse(product.activo)
