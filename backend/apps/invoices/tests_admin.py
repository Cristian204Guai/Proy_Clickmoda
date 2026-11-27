from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase, force_authenticate

from apps.catalog.models import Category, Product, ProductVariant
from apps.orders.models import Address, Order, OrderItem
from .admin_views import AdminInvoiceDetailView, AdminInvoiceListView
from .models import Invoice
from .services import emitir_factura_para_orden

User = get_user_model()


class AdminInvoiceTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.list_view = AdminInvoiceListView.as_view()
        self.detail_view = AdminInvoiceDetailView.as_view()

        self.admin_user = User.objects.create_superuser(
            email="admin@clickmoda.co",
            password="AdminPassword123!",
            nombre="Admin ClickModa",
        )
        self.client_user = User.objects.create_user(
            email="cliente@clickmoda.co",
            password="ClientPassword123!",
            nombre="Cliente Prueba",
        )

        categoria = Category.objects.create(
            nombre="Camisas", slug="camisas", orden=1
        )
        producto = Product.objects.create(
            nombre="Camisa Lino Premium",
            descripcion="Camisa de lino manga larga",
            categoria=categoria,
            precio_base=Decimal("100000"),
            porcentaje_iva=19,
            activo=True,
        )
        variante = ProductVariant.objects.create(
            producto=producto,
            talla=ProductVariant.Size.M,
            color="Blanco",
            sku="CAM-LINO-M-BLA",
            stock=20,
        )

        dir_1 = Address.objects.create(
            user=self.client_user,
            nombre_completo="Laura Martínez",
            telefono="3001112233",
            direccion="Calle 10 # 20-30",
            ciudad="Pasto",
        )
        self.orden_1 = Order.objects.create(
            user=self.client_user,
            direccion_envio=dir_1,
            estado=Order.Status.PAGADA,
            metodo_pago=Order.PaymentMethod.TARJETA,
            subtotal=Decimal("100000"),
            envio=Decimal("12000"),
            impuestos=Decimal("15966"),
            descuento=Decimal("0"),
            total=Decimal("112000"),
            requiere_factura_electronica=True,
            tipo_documento="CC",
            numero_documento="1085123456",
            correo_factura="laura@clickmoda.co",
        )
        OrderItem.objects.create(
            orden=self.orden_1,
            variante=variante,
            nombre_producto=producto.nombre,
            talla=variante.talla,
            color=variante.color,
            cantidad=1,
            precio_unitario=producto.precio_base,
            porcentaje_iva=producto.porcentaje_iva,
        )
        self.factura_1 = emitir_factura_para_orden(self.orden_1)

        dir_2 = Address.objects.create(
            user=self.client_user,
            nombre_completo="Carlos Pérez",
            telefono="3004445566",
            direccion="Carrera 25 # 15-10",
            ciudad="Bogotá",
        )
        self.orden_2 = Order.objects.create(
            user=self.client_user,
            direccion_envio=dir_2,
            estado=Order.Status.PAGADA,
            metodo_pago=Order.PaymentMethod.PSE,
            subtotal=Decimal("200000"),
            envio=Decimal("12000"),
            impuestos=Decimal("31933"),
            descuento=Decimal("0"),
            total=Decimal("212000"),
            requiere_factura_electronica=True,
            tipo_documento="NIT",
            numero_documento="900987654",
            correo_factura="carlos@empresa.co",
        )
        OrderItem.objects.create(
            orden=self.orden_2,
            variante=variante,
            nombre_producto=producto.nombre,
            talla=variante.talla,
            color=variante.color,
            cantidad=2,
            precio_unitario=producto.precio_base,
            porcentaje_iva=producto.porcentaje_iva,
        )
        self.factura_2 = emitir_factura_para_orden(self.orden_2)
        self.factura_2.estado = Invoice.Status.ANULADA
        self.factura_2.estado_respuesta = Invoice.StepStatus.ERROR
        self.factura_2.save(update_fields=["estado", "estado_respuesta"])

    def test_rechaza_acceso_anonimo_401(self):
        request_list = self.factory.get("/api/v1/admin/invoices/")
        response_list = self.list_view(request_list)
        self.assertEqual(response_list.status_code, status.HTTP_401_UNAUTHORIZED)

        request_detail = self.factory.get(
            f"/api/v1/admin/invoices/{self.factura_1.pk}/"
        )
        response_detail = self.detail_view(request_detail, pk=self.factura_1.pk)
        self.assertEqual(response_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rechaza_acceso_cliente_403(self):
        request_list = self.factory.get("/api/v1/admin/invoices/")
        force_authenticate(request_list, user=self.client_user)
        response_list = self.list_view(request_list)
        self.assertEqual(response_list.status_code, status.HTTP_403_FORBIDDEN)

        request_detail = self.factory.get(
            f"/api/v1/admin/invoices/{self.factura_1.pk}/"
        )
        force_authenticate(request_detail, user=self.client_user)
        response_detail = self.detail_view(request_detail, pk=self.factura_1.pk)
        self.assertEqual(response_detail.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_puede_listar_y_filtrar_facturas(self):
        # Listado completo ordenado por -fecha_emision
        request = self.factory.get("/api/v1/admin/invoices/")
        force_authenticate(request, user=self.admin_user)
        response = self.list_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], self.factura_2.id)
        self.assertEqual(response.data["results"][1]["id"], self.factura_1.id)

        campos_esperados = {
            "id",
            "numero",
            "orden",
            "fecha_emision",
            "adquiriente_nombre",
            "adquiriente_tipo_documento",
            "adquiriente_documento",
            "adquiriente_correo",
            "base_gravable",
            "iva",
            "envio",
            "total",
            "estado",
            "estado_respuesta",
            "cufe",
            "correos_enviados",
        }
        self.assertEqual(set(response.data["results"][0].keys()), campos_esperados)

        # Filtro por numero (search)
        req_num = self.factory.get(
            "/api/v1/admin/invoices/", {"search": self.factura_1.numero}
        )
        force_authenticate(req_num, user=self.admin_user)
        res_num = self.list_view(req_num)
        self.assertEqual(res_num.status_code, status.HTTP_200_OK)
        self.assertEqual(res_num.data["count"], 1)
        self.assertEqual(res_num.data["results"][0]["id"], self.factura_1.id)

        # Filtro por adquiriente_documento (search)
        req_doc = self.factory.get(
            "/api/v1/admin/invoices/", {"search": self.factura_1.adquiriente_documento}
        )
        force_authenticate(req_doc, user=self.admin_user)
        res_doc = self.list_view(req_doc)
        self.assertEqual(res_doc.status_code, status.HTTP_200_OK)
        self.assertEqual(res_doc.data["count"], 1)
        self.assertEqual(res_doc.data["results"][0]["id"], self.factura_1.id)

        # Filtro por cufe, adquiriente_nombre y adquiriente_correo (search)
        for termino, esperado_id in [
            (self.factura_2.cufe[:16], self.factura_2.id),
            ("Laura", self.factura_1.id),
            ("carlos@empresa.co", self.factura_2.id),
        ]:
            req_s = self.factory.get("/api/v1/admin/invoices/", {"search": termino})
            force_authenticate(req_s, user=self.admin_user)
            res_s = self.list_view(req_s)
            self.assertEqual(res_s.status_code, status.HTTP_200_OK)
            self.assertEqual(res_s.data["count"], 1)
            self.assertEqual(res_s.data["results"][0]["id"], esperado_id)

        # Filtro por estado_respuesta
        req_resp = self.factory.get(
            "/api/v1/admin/invoices/",
            {"estado_respuesta": Invoice.StepStatus.APROBADA},
        )
        force_authenticate(req_resp, user=self.admin_user)
        res_resp = self.list_view(req_resp)
        self.assertEqual(res_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(res_resp.data["count"], 1)
        self.assertEqual(res_resp.data["results"][0]["id"], self.factura_1.id)

        # Filtro por estado EMITIDA y ANULADA
        for estado_val, esperado_id in [
            (Invoice.Status.EMITIDA, self.factura_1.id),
            (Invoice.Status.ANULADA, self.factura_2.id),
        ]:
            req_estado = self.factory.get(
                "/api/v1/admin/invoices/", {"estado": estado_val}
            )
            force_authenticate(req_estado, user=self.admin_user)
            res_estado = self.list_view(req_estado)
            self.assertEqual(res_estado.status_code, status.HTTP_200_OK)
            self.assertEqual(res_estado.data["count"], 1)
            self.assertEqual(res_estado.data["results"][0]["id"], esperado_id)

    def test_admin_detalle_y_descarga_pdf_xml_y_reenvio(self):
        # Detalle completo mediante AdminInvoiceDetailView
        request_detail = self.factory.get(
            f"/api/v1/admin/invoices/{self.factura_1.pk}/"
        )
        force_authenticate(request_detail, user=self.admin_user)
        res_detail = self.detail_view(request_detail, pk=self.factura_1.pk)
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["id"], self.factura_1.id)
        self.assertEqual(res_detail.data["numero"], self.factura_1.numero)
        self.assertEqual(res_detail.data["cufe"], self.factura_1.cufe)
        self.assertIn("detalle_lineas", res_detail.data)
        self.assertIn("detalle_impuestos", res_detail.data)
        self.assertIn("resolucion", res_detail.data)

        # Rutas existentes /api/v1/invoices/<id>/...
        self.client.force_authenticate(user=self.admin_user)

        res_pdf = self.client.get(f"/api/v1/invoices/{self.factura_1.pk}/pdf/")
        self.assertEqual(res_pdf.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pdf["Content-Type"], "application/pdf")
        self.assertTrue(res_pdf.content.startswith(b"%PDF-1.4"))

        res_xml = self.client.get(f"/api/v1/invoices/{self.factura_1.pk}/xml/")
        self.assertEqual(res_xml.status_code, status.HTTP_200_OK)
        self.assertIn("application/xml", res_xml["Content-Type"])
        self.assertIn("UBL 2.1", res_xml.content.decode("utf-8"))

        res_resend = self.client.post(
            f"/api/v1/invoices/{self.factura_1.pk}/resend/",
            {"correo": "auditoria@clickmoda.co"},
            format="json",
        )
        self.assertEqual(res_resend.status_code, status.HTTP_200_OK)
        self.assertEqual(res_resend.data["correos_enviados"], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("auditoria@clickmoda.co", mail.outbox[0].to)
        self.assertIn(self.factura_1.numero, mail.outbox[0].subject)

        self.factura_1.refresh_from_db()
        self.assertEqual(self.factura_1.correos_enviados, 1)
