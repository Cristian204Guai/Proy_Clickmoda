from rest_framework import serializers

from .models import Order
from .serializers import OrderSerializer


class AdminOrderSerializer(OrderSerializer):
    """Serializador administrativo de órdenes con el correo del cliente."""

    cliente_email = serializers.SerializerMethodField()

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ("cliente_email",)

    def get_cliente_email(self, obj) -> str:
        if obj.user and obj.user.email:
            return obj.user.email
        return obj.correo_factura or ""


class AdminOrderStatusSerializer(serializers.Serializer):
    """Valida el nuevo estado enviado al actualizar una orden desde admin."""

    estado = serializers.ChoiceField(choices=Order.Status.choices)
