from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsAdminRole
from .models import Invoice
from .serializers import InvoiceSerializer


class AdminInvoiceSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "id",
            "numero",
            "orden",
            "fecha_emision",
            "adquiriente_nombre",
            "adquiriente_tipo_documento",
            "adquiriente_documento",
            "adquiriente_correo",
            "base_gravable",
            "iva",
            "envio",
            "total",
            "estado",
            "estado_respuesta",
            "cufe",
            "correos_enviados",
        )
        read_only_fields = fields


class AdminInvoiceListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminInvoiceSummarySerializer
    queryset = Invoice.objects.select_related("orden", "resolucion").all()
    search_fields = [
        "numero",
        "cufe",
        "adquiriente_nombre",
        "adquiriente_documento",
        "adquiriente_correo",
    ]
    filterset_fields = ["estado", "estado_respuesta"]
    ordering_fields = ["fecha_emision", "total", "numero"]
    ordering = ["-fecha_emision"]


class AdminInvoiceDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    queryset = Invoice.objects.select_related("orden", "resolucion")
    serializer_class = InvoiceSerializer
