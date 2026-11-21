from django.contrib import admin
from .models import Address, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "variante",
        "nombre_producto",
        "talla",
        "color",
        "cantidad",
        "precio_unitario",
        "porcentaje_iva",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "estado",
        "metodo_pago",
        "total",
        "stock_descontado",
        "creado_en",
    )
    list_filter = ("estado", "metodo_pago", "stock_descontado")
    inlines = [OrderItemInline]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "ciudad", "direccion", "telefono")