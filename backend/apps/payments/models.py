from django.db import models
from apps.orders.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        EXPIRADO = "EXPIRADO", "Expirado"

    class Gateway(models.TextChoices):
        WOMPI_SIM = "WOMPI_SIM", "Pasarela Simulada (Tarjeta / PSE / Nequi)"
        CONTRA_ENTREGA = "CONTRA_ENTREGA", "Pago Contra Entrega"

    orden = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment"
    )
    pasarela = models.CharField(
        max_length=30, choices=Gateway.choices, default=Gateway.WOMPI_SIM
    )
    referencia = models.CharField(max_length=80, unique=True, db_index=True)
    estado = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDIENTE, db_index=True
    )
    monto = models.DecimalField(max_digits=12, decimal_places=0)
    mensaje_respuesta = models.CharField(max_length=255, blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"Pago {self.referencia} - Orden #{self.orden_id} ({self.estado})"