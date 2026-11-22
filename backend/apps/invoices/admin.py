from django.contrib import admin
from .models import Invoice, NumberingResolution


@admin.register(NumberingResolution)
class NumberingResolutionAdmin(admin.ModelAdmin):
    list_display = (
        "numero_resolucion",
        "prefijo",
        "rango_desde",
        "rango_hasta",
        "consecutivo_actual",
        "fecha_desde",
        "fecha_hasta",
        "activa",
    )
    list_filter = ("activa", "ambiente")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "orden",
        "adquiriente_nombre",
        "total",
        "estado",
        "estado_respuesta",
        "fecha_emision",
    )
    list_filter = ("estado", "estado_respuesta")
    search_fields = ("numero", "cufe", "adquiriente_documento", "adquiriente_nombre")
    readonly_fields = ("cufe", "track_id", "firma_digital", "qr_data", "xml_ubl")