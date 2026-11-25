import re
import uuid
from PIL import Image, UnidentifiedImageError
from django.db import transaction
from django.db.models import ProtectedError, Sum
from django.db.models.functions import Coalesce
from django.utils.text import slugify
from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductVariant
from .serializers import ProductImageSerializer, ProductVariantSerializer

MAX_UPLOAD_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_uploaded_image(file_obj):
    """Valida tamaño máximo (5 MB) y contenido real con Pillow (JPEG, PNG o WEBP)."""
    if file_obj is None:
        raise serializers.ValidationError("Archivo de imagen inválido.")

    if file_obj.size > MAX_UPLOAD_IMAGE_SIZE:
        raise serializers.ValidationError(
            "La imagen supera el tamaño máximo permitido de 5 MB."
        )

    try:
        file_obj.seek(0)
        with Image.open(file_obj) as img:
            img_format = img.format
            img.verify()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
    ) as exc:
        raise serializers.ValidationError(
            "El archivo no es una imagen válida o está corrupto."
        ) from exc

    if img_format not in ALLOWED_IMAGE_FORMATS:
        raise serializers.ValidationError(
            "Formato de imagen no permitido. Solo se aceptan JPEG, PNG y WEBP."
        )

    file_obj.seek(0)
    return file_obj


class AdminCategorySerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(max_length=100)
    slug = serializers.SlugField(max_length=110, required=False, allow_blank=True)
    productos_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "nombre", "slug", "orden", "productos_count")

    def get_productos_count(self, obj) -> int:
        if hasattr(obj, "productos_count"):
            return obj.productos_count
        return obj.productos.count()

    def validate_nombre(self, value: str) -> str:
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre de la categoría es obligatorio.")
        qs = Category.objects.filter(nombre__iexact=nombre)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una categoría con este nombre.")
        return nombre

    def validate(self, attrs):
        if self.instance is None:
            slug = (attrs.get("slug") or "").strip()
            if not slug:
                slug = slugify(attrs["nombre"])
            if not slug:
                raise serializers.ValidationError(
                    {"slug": "No se pudo generar un slug válido a partir del nombre."}
                )
            attrs["slug"] = slug
        elif "slug" in attrs:
            slug = (attrs.get("slug") or "").strip()
            if not slug:
                slug = slugify(attrs.get("nombre", self.instance.nombre))
            if not slug:
                raise serializers.ValidationError(
                    {"slug": "El slug de la categoría no puede estar vacío."}
                )
            attrs["slug"] = slug

        if "slug" in attrs:
            qs = Category.objects.filter(slug__iexact=attrs["slug"])
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"slug": "Ya existe una categoría con este slug."}
                )

        return attrs


class AdminProductVariantInputSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    talla = serializers.ChoiceField(choices=ProductVariant.Size.choices)
    color = serializers.CharField(max_length=50)
    color_hex = serializers.CharField(max_length=7, required=False, default="#1F2937")
    sku = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    stock = serializers.IntegerField(min_value=0, required=False, default=0)

    class Meta:
        model = ProductVariant
        fields = ("id", "talla", "color", "color_hex", "sku", "stock")

    def validate_color(self, value: str) -> str:
        color = value.strip()
        if not color:
            raise serializers.ValidationError("El color de la variante es obligatorio.")
        return color

    def validate_color_hex(self, value: str) -> str:
        hex_val = (value or "#1F2937").strip()
        if not re.fullmatch(r"#[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?", hex_val):
            raise serializers.ValidationError(
                "El color hexadecimal debe tener formato #RGB o #RRGGBB."
            )
        return hex_val


class AdminProductImageInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    orden = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attrs):
        if "id" not in attrs:
            url = (attrs.get("url") or "").strip()
            if not url:
                raise serializers.ValidationError(
                    {"url": "La URL de la imagen es obligatoria."}
                )
            attrs["url"] = url
        return attrs


class AdminProductSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    categoria_slug = serializers.CharField(source="categoria.slug", read_only=True)
    estado_display = serializers.SerializerMethodField()
    stock_total = serializers.SerializerMethodField()
    tallas_disponibles = serializers.SerializerMethodField()
    variantes = AdminProductVariantInputSerializer(many=True, required=False)
    imagenes = AdminProductImageInputSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = (
            "id",
            "nombre",
            "descripcion",
            "categoria",
            "categoria_nombre",
            "categoria_slug",
            "precio_base",
            "porcentaje_iva",
            "activo",
            "estado_display",
            "stock_total",
            "tallas_disponibles",
            "variantes",
            "imagenes",
            "creado_en",
        )
        read_only_fields = ("id", "creado_en")

    def get_stock_total(self, obj) -> int:
        if hasattr(obj, "stock_total"):
            return obj.stock_total
        return sum(v.stock for v in obj.variantes.all())

    def get_estado_display(self, obj) -> str:
        if not obj.activo:
            return "Inactivo"
        if self.get_stock_total(obj) > 0:
            return "Activo"
        return "Agotado"

    def get_tallas_disponibles(self, obj):
        orden_tallas = ["XS", "S", "M", "L", "XL"]
        tallas = {v.talla for v in obj.variantes.all() if v.stock > 0}
        return [t for t in orden_tallas if t in tallas]

    def validate_nombre(self, value: str) -> str:
        nombre = value.strip()
        if not nombre:
            raise serializers.ValidationError("El nombre del producto es obligatorio.")
        return nombre

    def validate_precio_base(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "El precio base debe ser mayor o igual a 0."
            )
        return value

    def validate_porcentaje_iva(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "El porcentaje de IVA debe estar entre 0 y 100."
            )
        return value

    def validate_variantes(self, value):
        seen_pairs = set()
        seen_skus = set()
        existing_by_id = {}
        existing_by_key = {}
        if self.instance is not None:
            for v in self.instance.variantes.all():
                existing_by_id[v.pk] = v
                existing_by_key[(v.talla, v.color.strip().lower())] = v

        for item in value:
            pair = (item["talla"], item["color"].strip().lower())
            if pair in seen_pairs:
                raise serializers.ValidationError(
                    f"Variante duplicada para talla {item['talla']} y color {item['color']}."
                )
            seen_pairs.add(pair)

            var_id = item.get("id")
            if var_id is not None and self.instance is not None and var_id not in existing_by_id:
                raise serializers.ValidationError(
                    f"La variante con id {var_id} no pertenece a este producto."
                )

            sku = (item.get("sku") or "").strip()
            if sku:
                if sku in seen_skus:
                    raise serializers.ValidationError(
                        f"SKU duplicado en la solicitud: {sku}."
                    )
                seen_skus.add(sku)
                qs = ProductVariant.objects.filter(sku=sku)
                if var_id is not None:
                    qs = qs.exclude(pk=var_id)
                elif self.instance is not None and pair in existing_by_key:
                    qs = qs.exclude(pk=existing_by_key[pair].pk)
                if qs.exists():
                    raise serializers.ValidationError(
                        f"Ya existe una variante registrada con el SKU '{sku}'."
                    )
        return value

    def _generate_unique_sku(self, product: Product, color: str, talla: str) -> str:
        color_code = re.sub(r"[^A-Z0-9]", "", slugify(color).upper())[:4] or "CLR"
        while True:
            candidate = (
                f"CM-{product.pk:04d}-{color_code}-{talla.upper()}-{uuid.uuid4().hex[:4].upper()}"
            )[:64]
            if not ProductVariant.objects.filter(sku=candidate).exists():
                return candidate

    def _reload_product(self, pk: int) -> Product:
        return (
            Product.objects.select_related("categoria")
            .prefetch_related("variantes", "imagenes")
            .annotate(stock_total=Coalesce(Sum("variantes__stock"), 0))
            .get(pk=pk)
        )

    @transaction.atomic
    def create(self, validated_data):
        variantes_data = validated_data.pop("variantes", [])
        imagenes_data = validated_data.pop("imagenes", [])

        product = Product.objects.create(**validated_data)

        for v_data in variantes_data:
            v_copy = dict(v_data)
            v_copy.pop("id", None)
            sku = (v_copy.pop("sku", "") or "").strip()
            if not sku:
                sku = self._generate_unique_sku(
                    product, v_copy["color"], v_copy["talla"]
                )
            ProductVariant.objects.create(producto=product, sku=sku, **v_copy)

        for idx, img_data in enumerate(imagenes_data):
            ProductImage.objects.create(
                producto=product,
                url=img_data["url"],
                orden=img_data.get("orden", idx),
            )

        return self._reload_product(product.pk)

    @transaction.atomic
    def update(self, instance, validated_data):
        variantes_data = validated_data.pop("variantes", None)
        imagenes_data = validated_data.pop("imagenes", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if variantes_data is not None:
            existing_by_id = {v.pk: v for v in instance.variantes.all()}
            existing_by_key = {
                (v.talla, v.color.strip().lower()): v for v in instance.variantes.all()
            }

            claimed_ids = set()
            resolved_items = []
            for item in variantes_data:
                var_id = item.get("id")
                if var_id is not None:
                    if var_id not in existing_by_id:
                        raise serializers.ValidationError(
                            {"variantes": f"La variante con id {var_id} no pertenece a este producto."}
                        )
                    target = existing_by_id[var_id]
                    claimed_ids.add(target.pk)
                else:
                    target = None
                resolved_items.append((item, target))

            final_items = []
            for item, target in resolved_items:
                if target is None:
                    key = (item["talla"], item["color"].strip().lower())
                    candidate = existing_by_key.get(key)
                    if candidate is not None and candidate.pk not in claimed_ids:
                        target = candidate
                        claimed_ids.add(target.pk)
                final_items.append((item, target))

            for pk, variant in existing_by_id.items():
                if pk not in claimed_ids:
                    try:
                        variant.delete()
                    except ProtectedError as exc:
                        raise serializers.ValidationError(
                            {
                                "variantes": (
                                    f"No se puede eliminar la variante {variant.talla} - "
                                    f"{variant.color} porque tiene órdenes asociadas. "
                                    "Puedes dejar su stock en 0 en su lugar."
                                )
                            }
                        ) from exc

            for item, target in final_items:
                sku = (item.get("sku") or "").strip()
                if target is not None:
                    target.talla = item["talla"]
                    target.color = item["color"]
                    target.color_hex = item.get("color_hex", target.color_hex)
                    target.stock = item.get("stock", target.stock)
                    if sku:
                        target.sku = sku
                    target.save()
                else:
                    if not sku:
                        sku = self._generate_unique_sku(
                            instance, item["color"], item["talla"]
                        )
                    ProductVariant.objects.create(
                        producto=instance,
                        talla=item["talla"],
                        color=item["color"],
                        color_hex=item.get("color_hex", "#1F2937"),
                        sku=sku,
                        stock=item.get("stock", 0),
                    )

        if imagenes_data is not None:
            existing_imgs = {img.pk: img for img in instance.imagenes.all()}
            kept_img_ids = set()

            for idx, img_data in enumerate(imagenes_data):
                img_id = img_data.get("id")
                if img_id is not None:
                    if img_id not in existing_imgs:
                        raise serializers.ValidationError(
                            {"imagenes": f"La imagen con id {img_id} no pertenece a este producto."}
                        )
                    img_obj = existing_imgs[img_id]
                    if "orden" in img_data:
                        img_obj.orden = img_data["orden"]
                    if not img_obj.imagen and img_data.get("url"):
                        img_obj.url = img_data["url"].strip()
                    img_obj.save()
                    kept_img_ids.add(img_id)
                else:
                    ProductImage.objects.create(
                        producto=instance,
                        url=img_data["url"],
                        orden=img_data.get("orden", idx),
                    )

            for pk, img_obj in existing_imgs.items():
                if not img_obj.imagen and pk not in kept_img_ids:
                    img_obj.delete()

        return self._reload_product(instance.pk)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["variantes"] = ProductVariantSerializer(
            instance.variantes.all(), many=True, context=self.context
        ).data
        data["imagenes"] = ProductImageSerializer(
            instance.imagenes.all(), many=True, context=self.context
        ).data
        return data
