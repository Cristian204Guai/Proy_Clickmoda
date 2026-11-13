from decimal import Decimal
from django.conf import settings
from django.db import models
from apps.catalog.models import ProductVariant
from apps.coupons.models import Coupon


class Cart(models.Model):
    ENVIO_FIJO = Decimal("12000")
    IVA_PORCENTAJE = Decimal("0.19")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart",
    )
    session_key = models.CharField(
        max_length=100, null=True, blank=True, db_index=True
    )
    cupon = models.ForeignKey(
        Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name="carts"
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner = self.user.email if self.user else f"Sesión {self.session_key}"
        return f"Carrito de {owner}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variante = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE, related_name="cart_items"
    )
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "variante")
        ordering = ["id"]

    @property
    def subtotal(self) -> Decimal:
        return self.variante.producto.precio_base * self.cantidad