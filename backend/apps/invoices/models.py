import uuid

from django.db import models
from django.db.models import F, Q
from rest_framework.exceptions import ValidationError

from apps.orders.models import Order


class NumberingResolution(models.Model):
    """Resolución de autorización de numeración de facturación expedida por la DIAN (simulada)."""

    class Ambiente(models.TextChoices):
        PRODUCCION = "1", "Producción"
        PRUEBAS = "2", "Pruebas / Habilitación"

    numero_resolucion = models.CharField(max_length=30)
    prefijo = models.CharField(max_length=4)
    rango_desde = models.PositiveBigIntegerField()
    rango_hasta = models.PositiveBigIntegerField()
    # Último consecutivo utilizado (0 = aún no se ha emitido ninguna factura)
    consecutivo_actual = models.PositiveBigIntegerField(default=0)
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    clave_tecnica = models.CharField(max_length=64)
    ambiente = models.CharField(
        max_length=1, choices=Ambiente.choices, default=Ambiente.PRUEBAS
    )
    activa = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resolución de numeración"
        verbose_name_plural = "Resoluciones de numeración"
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["activa"],
                condition=Q(activa=True),
                name="una_resolucion_activa",
            ),
            models.CheckConstraint(
                condition=Q(rango_desde__lte=F("rango_hasta")),
                name="rango_resolucion_valido",
            ),
        ]

    def __str__(self):
        return (
            f"Res. {self.numero_resolucion} · {self.prefijo} "
            f"{self.rango_desde}-{self.rango_hasta}"
        )

    def tomar_siguiente_consecutivo(self, fecha) -> int:
        """
        Reserva el siguiente número de la resolución.
        Debe invocarse sobre una fila bloqueada con select_for_update() dentro de una transacción.
        """
        if not self.activa:
            raise ValidationError({"detail": "La resolución de numeración no está activa."})
        if not (self.fecha_desde <= fecha <= self.fecha_hasta):
            raise ValidationError(
                {
                    "detail": (
                        f"La resolución {self.numero_resolucion} no está vigente "
                        f"({self.fecha_desde} a {self.fecha_hasta})."
                    )
                }
            )
        siguiente = max(self.consecutivo_actual + 1, self.rango_desde)
        if siguiente > self.rango_hasta:
            raise ValidationError(
                {
                    "detail": (
                        f"Se agotó el rango autorizado de la resolución {self.numero_resolucion} "
                        f"({self.prefijo}{self.rango_desde} - {self.prefijo}{self.rango_hasta})."
                    )
                }
            )
        self.consecutivo_actual = siguiente
        self.save(update_fields=["consecutivo_actual"])
        return siguiente


class Invoice(models.Model):
    """Factura electrónica de venta simulada (UBL 2.1 / Anexo técnico DIAN)."""

    class Status(models.TextChoices):
        EMITIDA = "EMITIDA", "Emitida"
        ANULADA = "ANULADA", "Anulada (nota crédito simulada)"

    class StepStatus(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        LISTO = "LISTO", "Listo"
        APROBADA = "APROBADA", "Aprobada"
        ERROR = "ERROR", "Error"

    orden = models.OneToOneField(
        Order, on_delete=models.PROTECT, related_name="factura"
    )
    resolucion = models.ForeignKey(
        NumberingResolution, on_delete=models.PROTECT, related_name="facturas"
    )
    prefijo = models.CharField(max_length=4)
    consecutivo = models.PositiveBigIntegerField()
    numero = models.CharField(max_length=24, unique=True)
    fecha_emision = models.DateTimeField(db_index=True)

    # Emisor (facturador electrónico) congelado al momento de la emisión
    emisor_nit = models.CharField(max_length=20)
    emisor_dv = models.CharField(max_length=1, blank=True, default="")
    emisor_razon_social = models.CharField(max_length=150)

    # Adquiriente congelado al momento de la emisión
    adquiriente_nombre = models.CharField(max_length=150)
    adquiriente_tipo_documento = models.CharField(max_length=10, default="CC")
    adquiriente_documento = models.CharField(max_length=30)
    adquiriente_correo = models.EmailField(blank=True, default="")
    adquiriente_consumidor_final = models.BooleanField(default=False)

    # Totales discriminados (2 decimales, como exige UBL 2.1)
    subtotal_bruto = models.DecimalField(max_digits=14, decimal_places=2)
    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    base_gravable = models.DecimalField(max_digits=14, decimal_places=2)
    iva = models.DecimalField(max_digits=14, decimal_places=2)
    envio = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    detalle_lineas = models.JSONField(default=list)
    detalle_impuestos = models.JSONField(default=list)

    # Elementos técnicos del documento electrónico
    cufe = models.CharField(max_length=96, unique=True)
    qr_data = models.TextField()
    xml_ubl = models.TextField()
    firma_digital = models.CharField(max_length=128)
    track_id = models.UUIDField(default=uuid.uuid4, editable=False)

    estado = models.CharField(
        max_length=10, choices=Status.choices, default=Status.EMITIDA, db_index=True
    )
    estado_xml = models.CharField(
        max_length=10, choices=StepStatus.choices, default=StepStatus.PENDIENTE
    )
    estado_firma = models.CharField(
        max_length=10, choices=StepStatus.choices, default=StepStatus.PENDIENTE
    )
    estado_envio = models.CharField(
        max_length=10, choices=StepStatus.choices, default=StepStatus.PENDIENTE
    )
    estado_respuesta = models.CharField(
        max_length=10, choices=StepStatus.choices, default=StepStatus.PENDIENTE
    )
    codigo_respuesta_dian = models.CharField(max_length=5, blank=True, default="")
    mensaje_respuesta_dian = models.CharField(max_length=255, blank=True, default="")

    correos_enviados = models.PositiveIntegerField(default=0)
    ultimo_envio_correo = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Factura electrónica"
        verbose_name_plural = "Facturas electrónicas"
        ordering = ["-fecha_emision"]
        constraints = [
            models.UniqueConstraint(
                fields=["resolucion", "consecutivo"],
                name="consecutivo_unico_por_resolucion",
            )
        ]

    def __str__(self):
        return f"Factura {self.numero} - Orden #{self.orden_id} ({self.estado})"
