from django.conf import settings
from django.db import models
from apps.catalog.models import ProductVariant


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direcciones",
    )
    nombre_completo = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30)
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Dirección"
        verbose_name_plural = "Direcciones"

    def __str__(self):
        return f"{self.nombre_completo} - {self.direccion} ({self.ciudad})"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de pago"
        PAGADA = "PAGADA", "Pagada"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        ENVIADA = "ENVIADA", "Enviada"
        ENTREGADA = "ENTREGADA", "Entregada"
        CANCELADA = "CANCELADA", "Cancelada"

    class PaymentMethod(models.TextChoices):
        TARJETA = "TARJETA", "Tarjeta crédito / débito"
        PSE = "PSE", "PSE (Débito bancario)"
        NEQUI_DAVIPLATA = "NEQUI_DAVIPLATA", "Nequi / Daviplata"
        CONTRA_ENTREGA = "CONTRA_ENTREGA", "Contra entrega"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes",
    )
    session_key = models.CharField(max_length=100, blank=True, default="")
    direccion_envio = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name="ordenes"
    )
    estado = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDIENTE, db_index=True
    )
    metodo_pago = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.TARJETA
    )
    # Solo se guarda el token de la pasarela o referencia, JAMÁS tarjeta ni CVV
    token_pago = models.CharField(max_length=120, blank=True, default="")

    subtotal = models.DecimalField(max_digits=12, decimal_places=0)
    envio = models.DecimalField(max_digits=12, decimal_places=0, default=12000)
    impuestos = models.DecimalField(max_digits=12, decimal_places=0)
    descuento = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=0)
    cupon_codigo = models.CharField(max_length=40, blank=True, default="")

    # Datos para Facturación Electrónica DIAN (RF-16)
    requiere_factura_electronica = models.BooleanField(default=True)
    tipo_documento = models.CharField(max_length=10, blank=True, default="CC")
    numero_documento = models.CharField(max_length=30, blank=True, default="")
    correo_factura = models.EmailField(blank=True, default="")

    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Orden #{self.pk} - {self.estado} (${self.total})"


class OrderItem(models.Model):
    orden = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variante = models.ForeignKey(
        ProductVariant, on_delete=models.PROTECT, related_name="order_items"
    )
    nombre_producto = models.CharField(max_length=180)
    talla = models.CharField(max_length=5)
    color = models.CharField(max_length=50)
    cantidad = models.PositiveIntegerField()
    # Regla sección 5: guardar precio unitario e IVA vigentes al momento de la compra
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)
    porcentaje_iva = models.PositiveSmallIntegerField(default=19)

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad