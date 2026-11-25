from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer
from .serializers import PaymentWebhookSimulatorSerializer
from .services import procesar_confirmacion_pago


class PaymentWebhookSimulatorView(APIView):
    """
    Endpoint simulador de confirmación de pago (Sección 6: POST /api/v1/payments/webhook/).
    Ejecuta una transacción atómica que confirma el pago y descuenta stock,
    o cancela la orden y libera/devuelve el stock si se simula un fallo.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PaymentWebhookSimulatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        orden = procesar_confirmacion_pago(
            orden_id=data.get("orden_id"),
            referencia=data.get("referencia"),
            resultado=data["resultado"],
        )

        orden_actualizada = (
            Order.objects.select_related("direccion_envio", "payment", "factura")
            .prefetch_related("items")
            .get(pk=orden.pk)
        )
        return Response(
            OrderSerializer(orden_actualizada).data, status=status.HTTP_200_OK
        )