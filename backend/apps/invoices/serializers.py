from rest_framework import serializers
from .models import Invoice, NumberingResolution


class NumberingResolutionSerializer(serializers.ModelSerializer):
    rango_autorizado_texto = serializers.SerializerMethodField()

    class Meta:
        model = NumberingResolution
        fields = (
            "id",
            "numero_resolucion",
            "prefijo",
            "rango_desde",
            "rango_hasta",
            "fecha_desde",
            "fecha_hasta",
            "ambiente",
            "rango_autorizado_texto",
        )

    def get_rango_autorizado_texto(self, obj) -> str:
        return f"{obj.prefijo}-{obj.rango_desde:06d} a {obj.prefijo}-{obj.rango_hasta:06d}"


class InvoiceSerializer(serializers.ModelSerializer):
    resolucion = NumberingResolutionSerializer(read_only=True)
    emisor_direccion = serializers.SerializerMethodField()
    metodo_pago_label = serializers.CharField(
        source="orden.get_metodo_pago_display", read_only=True
    )

    class Meta:
        model = Invoice
        fields = (
            "id",
            "orden",
            "numero",
            "prefijo",
            "consecutivo",
            "fecha_emision",
            "emisor_nit",
            "emisor_dv",
            "emisor_razon_social",
            "emisor_direccion",
            "adquiriente_nombre",
            "adquiriente_tipo_documento",
            "adquiriente_documento",
            "adquiriente_correo",
            "adquiriente_consumidor_final",
            "metodo_pago_label",
            "subtotal_bruto",
            "descuento",
            "base_gravable",
            "iva",
            "envio",
            "total",
            "detalle_lineas",
            "detalle_impuestos",
            "cufe",
            "qr_data",
            "firma_digital",
            "track_id",
            "estado",
            "estado_xml",
            "estado_firma",
            "estado_envio",
            "estado_respuesta",
            "codigo_respuesta_dian",
            "mensaje_respuesta_dian",
            "correos_enviados",
            "ultimo_envio_correo",
            "resolucion",
        )

    def get_emisor_direccion(self, _obj) -> str:
        from django.conf import settings
        return getattr(settings, "CLICKMODA_EMISOR", {}).get(
            "DIRECCION", "Calle 18 # 24-50, Pasto - Nariño"
        )