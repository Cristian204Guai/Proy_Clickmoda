from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductVariant
from apps.core.permissions import IsAdminRole
from apps.payments.services import procesar_confirmacion_pago
from .admin_serializers import AdminOrderSerializer, AdminOrderStatusSerializer
from .models import Order

ALLOWED_ORDER_TRANSITIONS = {
    Order.Status.PENDIENTE: {Order.Status.PAGADA, Order.Status.CANCELADA},
    Order.Status.PAGADA: {Order.Status.EN_PREPARACION, Order.Status.CANCELADA},
    Order.Status.EN_PREPARACION: {Order.Status.ENVIADA, Order.Status.CANCELADA},
    Order.Status.ENVIADA: {Order.Status.ENTREGADA},
    Order.Status.ENTREGADA: set(),
    Order.Status.CANCELADA: set(),
}


def _get_order_detail_queryset():
    return Order.objects.select_related(
        "direccion_envio", "payment", "factura", "user"
    ).prefetch_related("items")


class AdminOrderListView(generics.ListAPIView):
    """Listado paginado de órdenes para administradores con filtros de estado y búsqueda."""

    serializer_class = AdminOrderSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filter_backends = []

    def get_queryset(self):
        qs = _get_order_detail_queryset().order_by("-creado_en", "-id")

        estado = self.request.query_params.get("estado", "").strip().upper()
        if estado:
            qs = qs.filter(estado=estado)

        search = self.request.query_params.get("search", "").strip()
        if search:
            q = (
                Q(direccion_envio__nombre_completo__icontains=search)
                | Q(correo_factura__icontains=search)
                | Q(user__email__icontains=search)
            )
            if search.isascii() and search.isdigit():
                q |= Q(pk=int(search))
            qs = qs.filter(q)

        return qs


class AdminOrderDetailView(APIView):
    """Detalle y actualización de estado de una orden desde administración."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, pk: int):
        orden = get_object_or_404(_get_order_detail_queryset(), pk=pk)
        return Response(AdminOrderSerializer(orden).data)

    @transaction.atomic
    def patch(self, request, pk: int):
        serializer = AdminOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nuevo_estado = serializer.validated_data["estado"]

        orden = get_object_or_404(Order.objects.select_for_update(), pk=pk)

        if orden.estado == nuevo_estado:
            orden_actualizada = _get_order_detail_queryset().get(pk=orden.pk)
            return Response(
                AdminOrderSerializer(orden_actualizada).data,
                status=status.HTTP_200_OK,
            )

        transiciones_permitidas = ALLOWED_ORDER_TRANSITIONS.get(orden.estado, set())
        if nuevo_estado not in transiciones_permitidas:
            return Response(
                {
                    "detail": (
                        f"Transición de estado no permitida: '{orden.estado}' -> '{nuevo_estado}'."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if orden.estado == Order.Status.PENDIENTE and nuevo_estado == Order.Status.PAGADA:
            procesar_confirmacion_pago(orden_id=orden.id, resultado="APROBADO")
        elif nuevo_estado == Order.Status.CANCELADA:
            if orden.stock_descontado:
                items = list(orden.items.all())
                variante_ids = sorted({item.variante_id for item in items})
                variantes_bloqueadas = {
                    v.id: v
                    for v in ProductVariant.objects.select_for_update()
                    .filter(id__in=variante_ids)
                    .order_by("id")
                }
                for item in items:
                    variante = variantes_bloqueadas[item.variante_id]
                    variante.stock += item.cantidad
                    variante.save(update_fields=["stock"])
                orden.stock_descontado = False

            orden.estado = Order.Status.CANCELADA
            orden.save(update_fields=["estado", "stock_descontado"])
        else:
            orden.estado = nuevo_estado
            orden.save(update_fields=["estado"])

        orden_actualizada = _get_order_detail_queryset().get(pk=orden.pk)
        return Response(
            AdminOrderSerializer(orden_actualizada).data,
            status=status.HTTP_200_OK,
        )
