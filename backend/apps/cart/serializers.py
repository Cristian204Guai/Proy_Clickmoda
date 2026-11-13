from decimal import Decimal
from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    variante_id = serializers.IntegerField(source="variante.id", read_only=True)
    producto_id = serializers.IntegerField(source="variante.producto.id", read_only=True)
    nombre_producto = serializers.CharField(source="variante.producto.nombre", read_only=True)
    talla = serializers.CharField(source="variante.talla", read_only=True)
    color = serializers.CharField(source="variante.color", read_only=True)
    color_hex = serializers.CharField(source="variante.color_hex", read_only=True)
    precio_unitario = serializers.DecimalField(
        source="variante.producto.precio_base",
        max_digits=12,
        decimal_places=0,
        read_only=True,
    )
    stock_disponible = serializers.IntegerField(source="variante.stock", read_only=True)
    imagen_url = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    sin_stock = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            "id",
            "variante_id",
            "producto_id",
            "nombre_producto",
            "talla",
            "color",
            "color_hex",
            "precio_unitario",
            "cantidad",
            "stock_disponible",
            "imagen_url",
            "subtotal",
            "sin_stock",
        )

    def get_imagen_url(self, obj) -> str:
        primera = obj.variante.producto.imagenes.first()
        return primera.url if primera else "#CBD5E1"

    def get_subtotal(self, obj) -> int:
        return int(obj.subtotal)

    def get_sin_stock(self, obj) -> bool:
        return obj.variante.stock == 0 or obj.cantidad > obj.variante.stock


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_unidades = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    envio = serializers.SerializerMethodField()
    iva = serializers.SerializerMethodField()
    descuento = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    cupon_codigo = serializers.SerializerMethodField()
    alertas_stock = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "id",
            "items",
            "total_unidades",
            "subtotal",
            "envio",
            "iva",
            "descuento",
            "total",
            "cupon_codigo",
            "alertas_stock",
        )

    def _calc_subtotal(self, obj: Cart) -> Decimal:
        return sum(
            (item.variante.producto.precio_base * item.cantidad for item in obj.items.all()),
            Decimal("0"),
        )

    def get_total_unidades(self, obj: Cart) -> int:
        return sum(item.cantidad for item in obj.items.all())

    def get_subtotal(self, obj: Cart) -> int:
        return int(self._calc_subtotal(obj))

    def get_envio(self, obj: Cart) -> int:
        return int(Cart.ENVIO_FIJO) if obj.items.exists() else 0

    def get_iva(self, obj: Cart) -> int:
        subtotal = self._calc_subtotal(obj)
        return int((subtotal * Cart.IVA_PORCENTAJE).quantize(Decimal("1")))

    def get_descuento(self, obj: Cart) -> int:
        if not obj.cupon:
            return 0
        subtotal = self._calc_subtotal(obj)
        return int(obj.cupon.calcular_descuento(subtotal))

    def get_total(self, obj: Cart) -> int:
        subtotal = self._calc_subtotal(obj)
        if subtotal == 0:
            return 0
        descuento = Decimal(self.get_descuento(obj))
        envio = Decimal(self.get_envio(obj))
        return int(max(Decimal("0"), subtotal - descuento) + envio)

    def get_cupon_codigo(self, obj: Cart) -> str | None:
        if obj.cupon and obj.cupon.es_valido()[0]:
            return obj.cupon.codigo
        return None

    def get_alertas_stock(self, obj: Cart) -> list[str]:
        alertas = []
        for item in obj.items.all():
            if item.variante.stock == 0:
                alertas.append(
                    f"La prenda '{item.variante.producto.nombre}' ({item.variante.talla} · {item.variante.color}) se agotó."
                )
            elif item.cantidad > item.variante.stock:
                alertas.append(
                    f"Solo quedan {item.variante.stock} unidades de '{item.variante.producto.nombre}' ({item.variante.talla} · {item.variante.color})."
                )
        return alertas