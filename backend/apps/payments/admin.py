from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("referencia", "orden", "pasarela", "estado", "monto", "actualizado_en")
    list_filter = ("estado", "pasarela")
    search_fields = ("referencia",)