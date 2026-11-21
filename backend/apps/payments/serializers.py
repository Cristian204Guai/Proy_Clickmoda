from rest_framework import serializers
from .models import Payment


class PaymentWebhookSimulatorSerializer(serializers.Serializer):
    orden_id = serializers.IntegerField(required=False)
    referencia = serializers.CharField(max_length=80, required=False)
    resultado = serializers.ChoiceField(
        choices=[
            Payment.Status.APROBADO,
            Payment.Status.RECHAZADO,
            Payment.Status.EXPIRADO,
        ],
        default=Payment.Status.APROBADO,
    )

    def validate(self, attrs):
        if not attrs.get("orden_id") and not attrs.get("referencia"):
            raise serializers.ValidationError(
                "Debes enviar 'orden_id' o 'referencia' para procesar el pago."
            )
        return attrs