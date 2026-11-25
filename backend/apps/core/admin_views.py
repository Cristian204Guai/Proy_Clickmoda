from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Product
from apps.core.permissions import IsAdminRole
from apps.orders.models import Order

User = get_user_model()
BOGOTA_TZ = ZoneInfo("America/Bogota")

ESTADOS_VENTA_VALIDOS = (
    Order.Status.PAGADA,
    Order.Status.EN_PREPARACION,
    Order.Status.ENVIADA,
    Order.Status.ENTREGADA,
)


class AdminStatsView(APIView):
    """KPIs principales y órdenes recientes para el panel de administración."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        productos_activos_qs = Product.objects.filter(activo=True).annotate(
            stock_total=Coalesce(Sum("variantes__stock"), 0)
        )
        total_productos = Product.objects.count()
        productos_activos = productos_activos_qs.filter(stock_total__gt=0).count()
        productos_agotados = productos_activos_qs.filter(stock_total=0).count()

        hoy = timezone.localdate(timezone=BOGOTA_TZ)
        inicio_hoy = datetime.combine(hoy, time.min, tzinfo=BOGOTA_TZ)
        fin_hoy = inicio_hoy + timedelta(days=1)

        inicio_mes = datetime(hoy.year, hoy.month, 1, tzinfo=BOGOTA_TZ)
        if hoy.month == 12:
            fin_mes = datetime(hoy.year + 1, 1, 1, tzinfo=BOGOTA_TZ)
        else:
            fin_mes = datetime(hoy.year, hoy.month + 1, 1, tzinfo=BOGOTA_TZ)

        ordenes_hoy = Order.objects.filter(
            creado_en__gte=inicio_hoy,
            creado_en__lt=fin_hoy,
        ).count()

        ventas_mes = Order.objects.filter(
            creado_en__gte=inicio_mes,
            creado_en__lt=fin_mes,
            estado__in=ESTADOS_VENTA_VALIDOS,
        ).aggregate(
            total_ventas=Coalesce(
                Sum("total"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=0),
            )
        )[
            "total_ventas"
        ]

        total_usuarios = User.objects.count()

        recientes = (
            Order.objects.select_related("direccion_envio")
            .order_by("-creado_en", "-id")[:5]
        )
        ordenes_recientes = [
            {
                "id": orden.id,
                "cliente_nombre": orden.direccion_envio.nombre_completo,
                "estado": orden.estado,
                "total": int(orden.total),
                "creado_en": timezone.localtime(orden.creado_en, BOGOTA_TZ).isoformat(),
            }
            for orden in recientes
        ]

        return Response(
            {
                "total_productos": total_productos,
                "productos_activos": productos_activos,
                "productos_agotados": productos_agotados,
                "ordenes_hoy": ordenes_hoy,
                "ventas_mes": int(ventas_mes),
                "total_usuarios": total_usuarios,
                "ordenes_recientes": ordenes_recientes,
            }
        )
