from django.contrib import admin
from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "tipo",
        "valor",
        "valido_hasta",
        "usos_actuales",
        "usos_maximos",
        "activo",
    )
    search_fields = ("codigo",)
    list_filter = ("tipo", "activo")