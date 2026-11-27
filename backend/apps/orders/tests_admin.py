from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import path
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product, ProductVariant
from apps.core.admin_views import AdminStatsView
from apps.invoices.models import Invoice
from apps.orders.admin_views import AdminOrderDetailView, AdminOrderListView
from apps.orders.models import Address, Order, OrderItem
from apps.payments.models import Payment

User = get_user_model()
BOGOTA_TZ = ZoneInfo("America/Bogota")

urlpatterns = [
    path("api/v1/admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("api/v1/admin/orders/", AdminOrderListView.as_view(), name="admin-order-list"),
    path(
        "api/v1/admin/orders/<int:pk>/",
        AdminOrderDetailView.as_view(),
        name="admin-order-detail",
    ),
]


@override_settings(ROOT_URLCONF=__name__)
class AdminDashboardAndOrdersTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@clickmoda.co",
            password="PasswordSeguro123!",
            nombre="Admin Principal",
            role=User.Role.ADMIN,
        )
        self.cliente = User.objects.create_user(
            email="cliente@clickmoda.co",
            password="PasswordSeguro123!",
            nombre="Cliente Demo",
            role=User.Role.CLIENTE,
        )
        self.categoria = Category.objects.create(nombre="Chaquetas", slug="chaquetas")

        self.producto_activo = Product.objects.create(
            nombre="Chaqueta Denim",
            categoria=self.categoria,
            precio_base=Decimal("180000"),
            activo=True,
        )
        self.variante_disponible = ProductVariant.objects.create(
            producto=self.producto_activo,
            talla="M",
            color="Azul",
            sku="CHQ-M-AZU",
            stock=5,
        )
        self.variante_extra = ProductVariant.objects.create(
            producto=self.producto_activo,
            talla="L",
            color="Negro",
            sku="CHQ-L-NEG",
            stock=3,
        )

        self.producto_agotado = Product.objects.create(
            nombre="Camisa Lino",
            categoria=self.categoria,
            precio_base=Decimal("95000"),
            activo=True,
        )
        ProductVariant.objects.create(
            producto=self.producto_agotado,
            talla="S",
            color="Blanco",
            sku="CAM-S-BLA",
            stock=0,
        )

        self.producto_inactivo = Product.objects.create(
            nombre="Abrigo Descontinuado",
            categoria=self.categoria,
            precio_base=Decimal("250000"),
            activo=False,
        )
        ProductVariant.objects.create(
            producto=self.producto_inactivo,
            talla="M",
            color="Gris",
            sku="ABR-M-GRI",
            stock=10,
        )

    def _crear_orden(
        self,
        *,
        user=None,
        nombre_envio="Laura Gómez",
        correo_factura="laura@ejemplo.com",
        estado=Order.Status.PENDIENTE,
        stock_descontado=False,
        total=Decimal("192000"),
        cantidad=2,
        variante=None,
    ) -> Order:
        variante = variante or self.variante_disponible
        direccion = Address.objects.create(
            user=user,
            nombre_completo=nombre_envio,
            telefono="3001234567",
            direccion="Calle 10 # 20-30",
            ciudad="Bogotá",
        )
        subtotal = variante.producto.precio_base * cantidad
        orden = Order.objects.create(
            user=user,
            direccion_envio=direccion,
            estado=estado,
            metodo_pago=Order.PaymentMethod.TARJETA,
            stock_descontado=stock_descontado,
            subtotal=subtotal,
            envio=Decimal("12000"),
            impuestos=Decimal("30000"),
            descuento=Decimal("0"),
            total=total,
            correo_factura=correo_factura,
        )
        OrderItem.objects.create(
            orden=orden,
            variante=variante,
            nombre_producto=variante.producto.nombre,
            talla=variante.talla,
            color=variante.color,
            cantidad=cantidad,
            precio_unitario=variante.producto.precio_base,
            porcentaje_iva=19,
        )
        Payment.objects.create(
            orden=orden,
            pasarela=Payment.Gateway.WOMPI_SIM,
            referencia=f"TEST-REF-{orden.pk}",
            estado=(
                Payment.Status.APROBADO
                if estado in (Order.Status.PAGADA, Order.Status.EN_PREPARACION, Order.Status.ENVIADA, Order.Status.ENTREGADA)
                else Payment.Status.PENDIENTE
            ),
            monto=total,
        )
        return orden

    def test_permisos_requeridos_en_dashboard_y_ordenes(self):
        orden = self._crear_orden(user=self.cliente)

        endpoints = [
            ("get", "/api/v1/admin/stats/"),
            ("get", "/api/v1/admin/orders/"),
            ("get", f"/api/v1/admin/orders/{orden.pk}/"),
            ("patch", f"/api/v1/admin/orders/{orden.pk}/"),
        ]

        # Usuario anónimo -> 401
        self.client.force_authenticate(user=None)
        for method, url in endpoints:
            resp = getattr(self.client, method)(url, {"estado": "CANCELADA"}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # Usuario cliente -> 403
        self.client.force_authenticate(user=self.cliente)
        for method, url in endpoints:
            resp = getattr(self.client, method)(url, {"estado": "CANCELADA"}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_stats_kpis_y_ordenes_recientes(self):
        hoy = timezone.localdate(timezone=BOGOTA_TZ)
        if hoy.month == 1:
            fecha_mes_anterior = datetime(hoy.year - 1, 12, 15, 12, 0, tzinfo=BOGOTA_TZ)
        else:
            fecha_mes_anterior = datetime(hoy.year, hoy.month - 1, 15, 12, 0, tzinfo=BOGOTA_TZ)

        # Órdenes válidas del mes actual y de hoy
        o_pagada = self._crear_orden(
            user=self.cliente, estado=Order.Status.PAGADA, total=Decimal("100000")
        )
        o_prep = self._crear_orden(
            user=self.cliente, estado=Order.Status.EN_PREPARACION, total=Decimal("150000")
        )
        o_enviada = self._crear_orden(
            user=self.cliente, estado=Order.Status.ENVIADA, total=Decimal("200000")
        )
        o_entregada = self._crear_orden(
            user=self.cliente, estado=Order.Status.ENTREGADA, total=Decimal("50000")
        )
        # No deben sumar en ventas_mes
        o_pendiente = self._crear_orden(
            user=self.cliente, estado=Order.Status.PENDIENTE, total=Decimal("999000")
        )
        o_cancelada = self._crear_orden(
            user=self.cliente, estado=Order.Status.CANCELADA, total=Decimal("888000")
        )
        # Orden de mes anterior: no cuenta en ordenes_hoy ni ventas_mes
        o_mes_anterior = self._crear_orden(
            user=self.cliente, estado=Order.Status.ENTREGADA, total=Decimal("500000")
        )
        Order.objects.filter(pk=o_mes_anterior.pk).update(creado_en=fecha_mes_anterior)

        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/v1/admin/stats/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        data = resp.json()
        self.assertEqual(data["total_productos"], 3)
        self.assertEqual(data["productos_activos"], 1)
        self.assertEqual(data["productos_agotados"], 1)
        self.assertEqual(data["ordenes_hoy"], 6)
        self.assertEqual(data["ventas_mes"], 500000)
        self.assertEqual(data["total_usuarios"], 2)
        self.assertEqual(len(data["ordenes_recientes"]), 5)
        self.assertEqual(
            set(data["ordenes_recientes"][0].keys()),
            {"id", "cliente_nombre", "estado", "total", "creado_en"},
        )
        self.assertEqual(
            [o["id"] for o in data["ordenes_recientes"]],
            [o_cancelada.id, o_pendiente.id, o_entregada.id, o_enviada.id, o_prep.id],
        )

    def test_listado_ordenes_paginacion_filtros_y_busqueda(self):
        o1 = self._crear_orden(
            user=self.cliente,
            nombre_envio="Carlos Martínez",
            correo_factura="carlos@factura.co",
            estado=Order.Status.PAGADA,
        )
        o2 = self._crear_orden(
            user=None,
            nombre_envio="María Invitada",
            correo_factura="maria.invitada@mail.com",
            estado=Order.Status.PENDIENTE,
        )
        for i in range(8):
            self._crear_orden(
                user=self.cliente,
                nombre_envio=f"Extra {i}",
                estado=Order.Status.ENVIADA,
            )

        self.client.force_authenticate(user=self.admin)

        # Paginación por defecto (PAGE_SIZE = 8)
        resp = self.client.get("/api/v1/admin/orders/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 10)
        self.assertEqual(len(resp.data["results"]), 8)

        # Filtro por estado
        resp_estado = self.client.get("/api/v1/admin/orders/?estado=PENDIENTE")
        self.assertEqual(resp_estado.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_estado.data["count"], 1)
        self.assertEqual(resp_estado.data["results"][0]["id"], o2.id)
        self.assertEqual(resp_estado.data["results"][0]["cliente_email"], "maria.invitada@mail.com")

        # Búsqueda por ID numérico
        resp_id = self.client.get(f"/api/v1/admin/orders/?search={o1.id}")
        self.assertEqual(resp_id.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item["id"] == o1.id for item in resp_id.data["results"]))

        # Búsqueda por nombre de envío
        resp_nombre = self.client.get("/api/v1/admin/orders/?search=Carlos")
        self.assertEqual(resp_nombre.data["count"], 1)
        self.assertEqual(resp_nombre.data["results"][0]["id"], o1.id)

        # Búsqueda por correo de factura
        resp_correo_fac = self.client.get("/api/v1/admin/orders/?search=maria.invitada")
        self.assertEqual(resp_correo_fac.data["count"], 1)
        self.assertEqual(resp_correo_fac.data["results"][0]["id"], o2.id)

        # Búsqueda por email del usuario
        resp_user_email = self.client.get("/api/v1/admin/orders/?search=cliente@clickmoda.co")
        self.assertEqual(resp_user_email.data["count"], 9)
        self.assertEqual(resp_user_email.data["results"][0]["cliente_email"], "cliente@clickmoda.co")

    def test_transicion_pendiente_a_pagada_via_webhook_descuenta_stock_y_emite_factura(self):
        orden = self._crear_orden(
            user=self.cliente,
            estado=Order.Status.PENDIENTE,
            stock_descontado=False,
            cantidad=2,
        )

        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "PAGADA"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["estado"], "PAGADA")
        self.assertTrue(resp.data["stock_descontado"])
        self.assertIsNotNone(resp.data["factura_id"])
        self.assertTrue(Invoice.objects.filter(orden=orden).exists())

        self.variante_disponible.refresh_from_db()
        self.assertEqual(self.variante_disponible.stock, 3)

        orden.payment.refresh_from_db()
        self.assertEqual(orden.payment.estado, Payment.Status.APROBADO)

    def test_flujo_completo_transiciones_y_idempotencia(self):
        orden = self._crear_orden(
            user=self.cliente,
            estado=Order.Status.PAGADA,
            stock_descontado=True,
        )
        self.client.force_authenticate(user=self.admin)

        # Idempotencia en mismo estado
        resp_idem = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "PAGADA"},
            format="json",
        )
        self.assertEqual(resp_idem.status_code, status.HTTP_200_OK)

        for siguiente in ("EN_PREPARACION", "ENVIADA", "ENTREGADA"):
            resp = self.client.patch(
                f"/api/v1/admin/orders/{orden.pk}/",
                {"estado": siguiente},
                format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertEqual(resp.data["estado"], siguiente)

        # Estado final ENTREGADA rechaza cambios con 400
        resp_final = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "CANCELADA"},
            format="json",
        )
        self.assertEqual(resp_final.status_code, status.HTTP_400_BAD_REQUEST)

        # Idempotencia en estado final
        resp_final_idem = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "ENTREGADA"},
            format="json",
        )
        self.assertEqual(resp_final_idem.status_code, status.HTTP_200_OK)

    def test_cancelacion_devuelve_stock_cuando_estaba_descontado(self):
        # Caso 1: Orden EN_PREPARACION con stock_descontado=True -> devuelve stock
        orden = self._crear_orden(
            user=self.cliente,
            estado=Order.Status.EN_PREPARACION,
            stock_descontado=True,
            cantidad=2,
        )
        stock_inicial = self.variante_disponible.stock

        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "CANCELADA"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["estado"], "CANCELADA")
        self.assertFalse(resp.data["stock_descontado"])

        self.variante_disponible.refresh_from_db()
        self.assertEqual(self.variante_disponible.stock, stock_inicial + 2)

        # Estado final CANCELADA rechaza cambio a PAGADA
        resp_reabrir = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "PAGADA"},
            format="json",
        )
        self.assertEqual(resp_reabrir.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelacion_desde_pendiente_no_altera_stock_y_rechaza_transiciones_invalidas(self):
        orden = self._crear_orden(
            user=self.cliente,
            estado=Order.Status.PENDIENTE,
            stock_descontado=False,
            cantidad=2,
        )
        stock_inicial = self.variante_disponible.stock
        self.client.force_authenticate(user=self.admin)

        # Transición inválida PENDIENTE -> ENVIADA
        resp_invalida = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "ENVIADA"},
            format="json",
        )
        self.assertEqual(resp_invalida.status_code, status.HTTP_400_BAD_REQUEST)

        # Cancelar PENDIENTE no suma stock porque no estaba descontado
        resp_cancel = self.client.patch(
            f"/api/v1/admin/orders/{orden.pk}/",
            {"estado": "CANCELADA"},
            format="json",
        )
        self.assertEqual(resp_cancel.status_code, status.HTTP_200_OK)
        self.variante_disponible.refresh_from_db()
        self.assertEqual(self.variante_disponible.stock, stock_inicial)
