from django.db import models


class Category(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Product(models.Model):
    nombre = models.CharField(max_length=180, db_index=True)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="productos"
    )
    precio_base = models.DecimalField(max_digits=12, decimal_places=0, db_index=True)
    porcentaje_iva = models.PositiveSmallIntegerField(default=19)
    activo = models.BooleanField(default=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["activo", "precio_base"]),
            models.Index(fields=["activo", "-creado_en"]),
        ]

    def __str__(self):
        return self.nombre


class ProductVariant(models.Model):
    class Size(models.TextChoices):
        XS = "XS", "XS"
        S = "S", "S"
        M = "M", "M"
        L = "L", "L"
        XL = "XL", "XL"

    producto = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variantes"
    )
    talla = models.CharField(max_length=5, choices=Size.choices, db_index=True)
    color = models.CharField(max_length=50, db_index=True)
    color_hex = models.CharField(max_length=7, default="#1F2937")
    sku = models.CharField(max_length=64, unique=True)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("producto", "talla", "color")
        ordering = ["id"]

    def __str__(self):
        return f"{self.producto.nombre} ({self.talla} - {self.color})"


class ProductImage(models.Model):
    producto = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="imagenes"
    )
    url = models.CharField(max_length=500)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "id"]

    def __str__(self):
        return f"Imagen {self.orden} de {self.producto.nombre}"