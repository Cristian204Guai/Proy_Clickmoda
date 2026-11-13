from rest_framework import serializers
from .models import Address, Order, OrderItem


class CheckoutCreateSerializer(serializers.Serializer):
    # Paso Envío (RF-11)
    nombre_completo = serializers.CharField(max_length=150)
    telefono = serializers.CharField(max_length=30)
    direccion = serializers.CharField(max_length=255)
    ciudad = serializers.CharField(max_length=100)

    # Paso Pago (RF-12) - Nunca acepta número de tarjeta ni CVV
    metodo_pago = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    token_pago = serializers.CharField(max_length=120, required=False, allow_blank=True)

    # Facturación electrónica DIAN (RF-16)
    requiere_factura_electronica = serializers.BooleanField(default=True)
    tipo_documento = serializers.CharField(
        max_length=10, required=False, allow_blank=True, default="CC"
    )
    numero_documento = serializers.CharField(
        max_length=30, required=False, allow_blank=True, default=""
    )
    correo_factura = serializers.EmailField(
        required=False, allow_blank=True, default=""
    )


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "variante",
            "nombre_producto",
            "talla",
            "color",
            "cantidad",
            "precio_unitario",
            "porcentaje_iva",
            "subtotal",
        )

    def get_subtotal(self, obj) -> int:
        return int(obj.subtotal)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("id", "nombre_completo", "telefono", "direccion", "ciudad")


class OrderSerializer(serializers.ModelSerializer):
    direccion_envio = AddressSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "estado",
            "metodo_pago",
            "token_pago",
            "subtotal",
            "envio",
            "impuestos",
            "descuento",
            "total",
            "cupon_codigo",
            "requiere_factura_electronica",
            "tipo_documento",
            "numero_documento",
            "correo_factura",
            "direccion_envio",
            "items",
            "creado_en",
        )