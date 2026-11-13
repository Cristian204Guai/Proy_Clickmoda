from decimal import Decimal
from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    
    class DiscountType(models.TextChoices):
        PORCENTAJE = "PORCENTAJE", "Porcentaje (%)"
        VALOR = "VALOR", "Valor fijo (COP)"

    codigo = models.CharField(max_length=40, unique=True, db_index=True)
    tipo = models.CharField(
        max_length=15, choices=DiscountType.choices, default=DiscountType.PORCENTAJE
    )
    valor = models.DecimalField(max_digits=12, decimal_places=0)
    valido_desde = models.DateTimeField(default=timezone.now)
    valido_hasta = models.DateTimeField()
    usos_maximos = models.PositiveIntegerField(default=100)
    usos_actuales = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cupón"
        verbose_name_plural = "Cupones"

    def __str__(self):
        return f"{self.codigo} ({self.get_tipo_display()}: {self.valor})"

    def es_valido(self) -> tuple[bool, str]:
        ahora = timezone.now()
        if not self.activo:
            return False, "Este cupón está desactivado."
        if ahora < self.valido_desde:
            return False, "Este cupón aún no está vigente."
        if ahora > self.valido_hasta:
            return False, "Este cupón ha expirado."
        if self.usos_actuales >= self.usos_maximos:
            return False, "Este cupón alcanzó su límite máximo de usos."
        return True, ""

    def calcular_descuento(self, subtotal: Decimal) -> Decimal:
        valido, _ = self.es_valido()
        if not valido or subtotal <= 0:
            return Decimal("0")
        if self.tipo == self.DiscountType.PORCENTAJE:
            descuento = (subtotal * self.valor) / Decimal("100")
        else:
            descuento = self.valor
        return min(descuento.quantize(Decimal("1")), subtotal)