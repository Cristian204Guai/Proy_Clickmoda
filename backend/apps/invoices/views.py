from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Invoice
from .serializers import InvoiceSerializer
from .services import generar_pdf_muestra, reenviar_factura_por_correo


def _obtener_factura_autorizada(request, pk: int) -> Invoice:
    factura = get_object_or_404(
        Invoice.objects.select_related("orden", "resolucion"), pk=pk
    )
    orden = factura.orden

    if request.user and request.user.is_authenticated:
        if getattr(request.user, "is_admin_role", False):
            return factura
        if orden.user_id and orden.user_id != request.user.id:
            raise PermissionDenied("No tienes permiso para acceder a esta factura.")
        return factura

    session_key = request.headers.get("X-Cart-Session") or ""
    if orden.user_id is not None:
        raise PermissionDenied("Debes iniciar sesión para consultar esta factura.")
    if orden.session_key and session_key and orden.session_key != session_key:
        raise PermissionDenied("Esta factura pertenece a otra sesión de compra.")
    return factura


class InvoiceDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk: int):
        factura = _obtener_factura_autorizada(request, pk)
        return Response(InvoiceSerializer(factura).data)


class InvoicePdfDownloadView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk: int):
        factura = _obtener_factura_autorizada(request, pk)
        pdf_bytes = generar_pdf_muestra(factura)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{factura.numero}.pdf"'
        return response


class InvoiceXmlDownloadView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk: int):
        factura = _obtener_factura_autorizada(request, pk)
        response = HttpResponse(
            factura.xml_ubl, content_type="application/xml; charset=utf-8"
        )
        response["Content-Disposition"] = f'attachment; filename="{factura.numero}.xml"'
        return response


class InvoiceResendEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk: int):
        factura = _obtener_factura_autorizada(request, pk)
        correo = request.data.get("correo")
        destino = reenviar_factura_por_correo(factura, correo_destino=correo)
        return Response(
            {
                "detail": f"Factura {factura.numero} reenviada a {destino}.",
                "correos_enviados": factura.correos_enviados,
                "ultimo_envio_correo": factura.ultimo_envio_correo,
            },
            status=status.HTTP_200_OK,
        )