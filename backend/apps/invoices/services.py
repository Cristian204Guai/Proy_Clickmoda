import hashlib
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order
from .models import Invoice, NumberingResolution


def obtener_resolucion_activa_bloqueada() -> NumberingResolution:
    """
    Obtiene y bloquea (select_for_update) la resolución activa.
    Si no existe ninguna en base de datos, crea una resolución sandbox por defecto.
    """
    resolucion = (
        NumberingResolution.objects.select_for_update()
        .filter(activa=True)
        .first()
    )
    if resolucion:
        return resolucion

    hoy = timezone.localdate()
    return NumberingResolution.objects.create(
        numero_resolucion="18764000001234",
        prefijo="FE",
        rango_desde=1,
        rango_hasta=5000,
        consecutivo_actual=0,
        fecha_desde=hoy - timedelta(days=1),
        fecha_hasta=hoy + timedelta(days=365),
        clave_tecnica="fc8eac422eba16e22ffd8c6f94b3f40a6e38162c",
        ambiente=NumberingResolution.Ambiente.PRUEBAS,
        activa=True,
    )


def _generar_xml_ubl(invoice_data: dict) -> str:
    """Genera un documento XML simulado siguiendo la estructura UBL 2.1 de la DIAN."""
    lineas_xml = []
    for idx, linea in enumerate(invoice_data["lineas"], start=1):
        lineas_xml.append(
            f"""  <cac:InvoiceLine>
    <cbc:ID>{idx}</cbc:ID>
    <cbc:InvoicedQuantity unitCode="EA">{linea['cantidad']}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="COP">{linea['base_linea']:.2f}</cbc:LineExtensionAmount>
    <cac:TaxTotal>
      <cbc:TaxAmount currencyID="COP">{linea['iva_linea']:.2f}</cbc:TaxAmount>
      <cac:TaxSubtotal>
        <cbc:TaxableAmount currencyID="COP">{linea['base_linea']:.2f}</cbc:TaxableAmount>
        <cbc:TaxAmount currencyID="COP">{linea['iva_linea']:.2f}</cbc:TaxAmount>
        <cac:TaxCategory>
          <cbc:Percent>{linea['porcentaje_iva']:.2f}</cbc:Percent>
          <cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme>
        </cac:TaxCategory>
      </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:Item><cbc:Description>{escape(linea['descripcion'])}</cbc:Description></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="COP">{linea['valor_unitario_sin_iva']:.2f}</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:sts="dian:gov:co:facturaelectronica:Structures-2-1">
  <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
  <cbc:ProfileID>DIAN 2.1: Factura Electrónica de Venta</cbc:ProfileID>
  <cbc:ID>{escape(invoice_data['numero'])}</cbc:ID>
  <cbc:UUID schemeName="CUFE-SHA384">{invoice_data['cufe']}</cbc:UUID>
  <cbc:IssueDate>{invoice_data['fecha_iso'][:10]}</cbc:IssueDate>
  <cbc:IssueTime>{invoice_data['fecha_iso'][11:19]}-05:00</cbc:IssueTime>
  <cbc:InvoiceTypeCode>01</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <sts:DianExtensions>
    <sts:InvoiceControl>
      <sts:InvoiceAuthorization>{escape(invoice_data['resolucion_numero'])}</sts:InvoiceAuthorization>
      <sts:AuthorizedInvoices>
        <sts:Prefix>{escape(invoice_data['prefijo'])}</sts:Prefix>
        <sts:From>{invoice_data['rango_desde']}</sts:From>
        <sts:To>{invoice_data['rango_hasta']}</sts:To>
      </sts:AuthorizedInvoices>
    </sts:InvoiceControl>
  </sts:DianExtensions>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName>{escape(invoice_data['emisor_razon_social'])}</cbc:RegistrationName>
        <cbc:CompanyID>{escape(invoice_data['emisor_nit'])}</cbc:CompanyID>
      </cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyTaxScheme>
        <cbc:RegistrationName>{escape(invoice_data['adquiriente_nombre'])}</cbc:RegistrationName>
        <cbc:CompanyID>{escape(invoice_data['adquiriente_documento'])}</cbc:CompanyID>
      </cac:PartyTaxScheme>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="COP">{invoice_data['iva']:.2f}</cbc:TaxAmount>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="COP">{invoice_data['base_gravable']:.2f}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="COP">{invoice_data['base_gravable']:.2f}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="COP">{invoice_data['total']:.2f}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="COP">{invoice_data['total']:.2f}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
{chr(10).join(lineas_xml)}
</Invoice>
"""


@transaction.atomic
def emitir_factura_para_orden(orden: Order) -> Invoice:
    """
    Emite automáticamente la factura electrónica simulada ante la DIAN al confirmarse el pago.
    Idempotente: si la orden ya tiene factura emitida, la retorna sin duplicarla.
    """
    existente = Invoice.objects.filter(orden=orden).first()
    if existente:
        return existente

    resolucion = obtener_resolucion_activa_bloqueada()
    ahora = timezone.localtime(timezone.now())
    fecha_local = ahora.date()
    consecutivo = resolucion.tomar_siguiente_consecutivo(fecha_local)
    numero = f"{resolucion.prefijo}-{consecutivo:06d}"

    emisor_raw = getattr(
        settings,
        "CLICKMODA_EMISOR",
        {},
    )
    emisor = {
        "NIT": emisor_raw.get("NIT", "901456789"),
        "DV": emisor_raw.get("DV", "4"),
        "RAZON_SOCIAL": (
            emisor_raw.get("RAZON_SOCIAL")
            or emisor_raw.get("RazonSocial")
            or "ClickModa Colombia S.A.S."
        ),
    }

    consumidor_final = not bool(orden.requiere_factura_electronica and orden.numero_documento.strip())
    adquiriente_nombre = (
        "Consumidor Final" if consumidor_final else orden.direccion_envio.nombre_completo
    )
    adquiriente_tipo_doc = "CC" if consumidor_final else (orden.tipo_documento or "CC")
    adquiriente_doc = (
        "222222222222" if consumidor_final else orden.numero_documento.strip()
    )
    adquiriente_correo = orden.correo_factura or (orden.user.email if orden.user else "")

    # Discriminación de totales e impuestos congruente con Order
    subtotal_bruto = Decimal(orden.subtotal).quantize(Decimal("0.01"))
    descuento = Decimal(orden.descuento).quantize(Decimal("0.01"))
    iva = Decimal(orden.impuestos).quantize(Decimal("0.01"))
    envio = Decimal(orden.envio).quantize(Decimal("0.01"))
    total = Decimal(orden.total).quantize(Decimal("0.01"))
    base_gravable = max(Decimal("0.00"), subtotal_bruto - descuento - iva).quantize(
        Decimal("0.01")
    )

    detalle_lineas = []
    for item in orden.items.all():
        iva_pct = Decimal(item.porcentaje_iva)
        factor_iva = Decimal("1") + (iva_pct / Decimal("100"))
        valor_unit_sin_iva = (Decimal(item.precio_unitario) / factor_iva).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        total_linea = Decimal(item.subtotal).quantize(Decimal("0.01"))
        base_linea = (valor_unit_sin_iva * item.cantidad).quantize(Decimal("0.01"))
        iva_linea = (total_linea - base_linea).quantize(Decimal("0.01"))

        detalle_lineas.append(
            {
                "descripcion": f"{item.nombre_producto} ({item.talla} · {item.color})",
                "cantidad": item.cantidad,
                "valor_unitario_sin_iva": float(valor_unit_sin_iva),
                "porcentaje_iva": int(item.porcentaje_iva),
                "base_linea": float(base_linea),
                "iva_linea": float(iva_linea),
                "total_linea": float(total_linea),
            }
        )

    detalle_impuestos = [
        {
            "codigo": "01",
            "nombre": "IVA",
            "tarifa": 19,
            "base_gravable": float(base_gravable),
            "valor": float(iva),
        }
    ]

    # Cálculo de CUFE simulado (SHA-384 = 96 caracteres hexadecimales)
    fecha_iso = ahora.isoformat()
    cadena_cufe = (
        f"{numero}{fecha_iso}{base_gravable:.2f}01{iva:.2f}040.00030.00"
        f"{total:.2f}{emisor['NIT']}{adquiriente_doc}{resolucion.clave_tecnica}{resolucion.ambiente}"
    )
    cufe = hashlib.sha384(cadena_cufe.encode("utf-8")).hexdigest()

    qr_data = (
        f"NumFac={numero}\n"
        f"FecFac={ahora.strftime('%Y-%m-%d')}\n"
        f"HorFac={ahora.strftime('%H:%M:%S-05:00')}\n"
        f"NitFac={emisor['NIT']}\n"
        f"DocAdq={adquiriente_doc}\n"
        f"ValFac={base_gravable:.2f}\n"
        f"ValIva={iva:.2f}\n"
        f"ValOtroIm=0.00\n"
        f"ValTotal={total:.2f}\n"
        f"CUFE={cufe}\n"
        f"https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={cufe}"
    )

    xml_ubl = _generar_xml_ubl(
        {
            "numero": numero,
            "cufe": cufe,
            "fecha_iso": fecha_iso,
            "resolucion_numero": resolucion.numero_resolucion,
            "prefijo": resolucion.prefijo,
            "rango_desde": resolucion.rango_desde,
            "rango_hasta": resolucion.rango_hasta,
            "emisor_razon_social": emisor["RAZON_SOCIAL"],
            "emisor_nit": emisor["NIT"],
            "adquiriente_nombre": adquiriente_nombre,
            "adquiriente_documento": adquiriente_doc,
            "base_gravable": base_gravable,
            "iva": iva,
            "total": total,
            "lineas": detalle_lineas,
        }
    )

    firma_digital = hashlib.sha256(
        f"{xml_ubl}|{resolucion.clave_tecnica}".encode("utf-8")
    ).hexdigest()

    factura = Invoice.objects.create(
        orden=orden,
        resolucion=resolucion,
        prefijo=resolucion.prefijo,
        consecutivo=consecutivo,
        numero=numero,
        fecha_emision=ahora,
        emisor_nit=emisor["NIT"],
        emisor_dv=emisor["DV"],
        emisor_razon_social=emisor["RAZON_SOCIAL"],
        adquiriente_nombre=adquiriente_nombre,
        adquiriente_tipo_documento=adquiriente_tipo_doc,
        adquiriente_documento=adquiriente_doc,
        adquiriente_correo=adquiriente_correo,
        adquiriente_consumidor_final=consumidor_final,
        subtotal_bruto=subtotal_bruto,
        descuento=descuento,
        base_gravable=base_gravable,
        iva=iva,
        envio=envio,
        total=total,
        detalle_lineas=detalle_lineas,
        detalle_impuestos=detalle_impuestos,
        cufe=cufe,
        qr_data=qr_data,
        xml_ubl=xml_ubl,
        firma_digital=firma_digital,
        estado=Invoice.Status.EMITIDA,
        estado_xml=Invoice.StepStatus.LISTO,
        estado_firma=Invoice.StepStatus.LISTO,
        estado_envio=Invoice.StepStatus.LISTO,
        estado_respuesta=Invoice.StepStatus.APROBADA,
        codigo_respuesta_dian="00",
        mensaje_respuesta_dian="Validada por la DIAN (Simulador Sandbox UBL 2.1).",
    )
    return factura


def _limpiar_texto_pdf(texto: str) -> str:
    """Convierte a ASCII seguro y escapa paréntesis para sintaxis PDF 1.4."""
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
        "ñ": "n", "Ñ": "N", "·": "-",
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    texto_ascii = texto.encode("ascii", "replace").decode("ascii")
    return texto_ascii.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def generar_pdf_muestra(invoice: Invoice) -> bytes:
    """Genera un archivo PDF 1.4 válido de muestra en Python puro (sin dependencias externas)."""
    fecha_fmt = timezone.localtime(invoice.fecha_emision).strftime("%d/%m/%Y %H:%M")
    lineas_texto = [
        f"CLICKMODA - FACTURA ELECTRONICA DE VENTA {invoice.numero}",
        f"Emisor: {invoice.emisor_razon_social} | NIT: {invoice.emisor_nit}-{invoice.emisor_dv}",
        f"Fecha de emision: {fecha_fmt} | Estado DIAN: {invoice.estado_respuesta}",
        "--------------------------------------------------------------------------",
        f"Adquiriente: {invoice.adquiriente_nombre}",
        f"Documento: {invoice.adquiriente_tipo_documento} {invoice.adquiriente_documento} | Correo: {invoice.adquiriente_correo or 'N/A'}",
        f"Forma de pago: Contado ({invoice.orden.get_metodo_pago_display()}) | Moneda: COP",
        "--------------------------------------------------------------------------",
        "DETALLE DE PRENDAS:",
    ]

    for item in invoice.detalle_lineas:
        lineas_texto.append(
            f" * {item['descripcion']} x{item['cantidad']} | Unit sin IVA: ${item['valor_unitario_sin_iva']:,.0f} | IVA {item['porcentaje_iva']}% | Total: ${item['total_linea']:,.0f}"
        )

    lineas_texto.extend(
        [
            "--------------------------------------------------------------------------",
            f"Base gravable (Subtotal sin IVA): ${invoice.base_gravable:,.0f} COP",
            f"IVA (19%):                        ${invoice.iva:,.0f} COP",
            f"Descuento:                       -${invoice.descuento:,.0f} COP",
            f"Envio:                            ${invoice.envio:,.0f} COP",
            f"TOTAL FACTURA:                    ${invoice.total:,.0f} COP",
            "--------------------------------------------------------------------------",
            f"Resolucion DIAN: {invoice.resolucion.numero_resolucion} ({invoice.prefijo}-{invoice.resolucion.rango_desde:06d} a {invoice.prefijo}-{invoice.resolucion.rango_hasta:06d})",
            f"CUFE (1/2): {invoice.cufe[:48]}",
            f"CUFE (2/2): {invoice.cufe[48:]}",
            f"TrackID DIAN: {invoice.track_id}",
        ]
    )

    comandos = ["BT", "/F1 10 Tf", "40 760 Td", "15 TL"]
    for idx, linea in enumerate(lineas_texto):
        limpia = _limpiar_texto_pdf(linea)
        if idx == 0:
            comandos.append(f"({limpia}) Tj")
        else:
            comandos.append(f"T* ({limpia}) Tj")
    comandos.append("ET")
    stream_bytes = "\n".join(comandos).encode("latin-1")

    objetos = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n",
        f"4 0 obj << /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
        + stream_bytes
        + b"\nendstream\nendobj\n",
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objetos:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def reenviar_factura_por_correo(invoice: Invoice, correo_destino: str | None = None) -> str:
    """Simula el envío/reenvío de la factura electrónica por correo (RF-19)."""
    destino = (correo_destino or invoice.adquiriente_correo or "").strip()
    if not destino:
        destino = "consumidor-final@clickmoda.co"

    send_mail(
        subject=f"ClickModa - Factura Electrónica {invoice.numero}",
        message=(
            f"Estimado(a) {invoice.adquiriente_nombre},\n\n"
            f"Adjuntamos los datos de tu Factura Electrónica de Venta {invoice.numero}:\n"
            f"- Fecha de emisión: {timezone.localtime(invoice.fecha_emision).strftime('%d/%m/%Y %H:%M')}\n"
            f"- Base gravable: ${invoice.base_gravable:,.0f} COP\n"
            f"- IVA (19%): ${invoice.iva:,.0f} COP\n"
            f"- Envío: ${invoice.envio:,.0f} COP\n"
            f"- Total: ${invoice.total:,.0f} COP\n"
            f"- CUFE: {invoice.cufe}\n"
            f"- Estado DIAN: {invoice.estado_respuesta}\n\n"
            f"Gracias por comprar en ClickModa."
        ),
        from_email="facturacion@clickmoda.co",
        recipient_list=[destino],
        fail_silently=True,
    )

    invoice.correos_enviados += 1
    invoice.ultimo_envio_correo = timezone.now()
    invoice.save(update_fields=["correos_enviados", "ultimo_envio_correo"])
    return destino