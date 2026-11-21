from django.core.mail import send_mail
from django.db import models, transaction
from rest_framework.exceptions import ValidationError

from apps.cart.models import Cart
from apps.catalog.models import ProductVariant
from apps.coupons.models import Coupon
from apps.orders.models import Order
from .models import Payment


@transaction.atomic
def procesar_confirmacion_pago(
    *,
    orden_id: int | None = None,
    referencia: str | None = None,
    resultado: str = "APROBADO",
) -> Order:
    """
    Simula el webhook de la pasarela dentro de una transacción atómica:
    - Si resultado == 'APROBADO': bloquea variantes, valida y descuenta stock,
      marca Payment=APROBADO y Order=PAGADA, vacía el carrito y envía correo en consola.
    - Si resultado in ('RECHAZADO', 'EXPIRADO'): marca Payment=RECHAZADO/EXPIRADO,
      Order=CANCELADA y devuelve/libera el stock si había sido descontado.
    """
    # 1. Bloquear la fila de la orden (sin select_related de relaciones reversas para evitar error de FOR UPDATE en PostgreSQL)
    if orden_id:
        orden = (
            Order.objects.select_for_update()
            .filter(pk=orden_id)
            .first()
        )
    else:
        # Si se busca por referencia de pago, buscamos primero el ID de la orden
        orden_id_val = (
            Payment.objects.filter(referencia=referencia)
            .values_list("orden_id", flat=True)
            .first()
        )
        if not orden_id_val:
            raise ValidationError({"detail": "No se encontró la orden o referencia de pago."})

        orden = (
            Order.objects.select_for_update()
            .filter(pk=orden_id_val)
            .first()
        )

    if not orden:
        raise ValidationError({"detail": "No se encontró la orden o referencia de pago."})

    payment = orden.payment
    resultado = resultado.upper().strip()
    items = list(orden.items.all())
    variante_ids = [item.variante_id for item in items]

    # Bloquear en base de datos las variantes involucradas (ordenadas por ID para evitar deadlocks)
    variantes_bloqueadas = {
        v.id: v
        for v in ProductVariant.objects.select_for_update()
        .filter(id__in=variante_ids)
        .order_by("id")
    }

    # --- CASO A: PAGO APROBADO ---
    if resultado == Payment.Status.APROBADO:
        # Idempotencia: si ya estaba pagada y con stock descontado, no repetir descuento
        if orden.estado == Order.Status.PAGADA and orden.stock_descontado:
            return orden

        # Verificar que todas las variantes tengan stock suficiente
        for item in items:
            variante = variantes_bloqueadas[item.variante_id]
            if variante.stock < item.cantidad:
                raise ValidationError(
                    {
                        "detail": (
                            f"No se pudo confirmar el pago: '{item.nombre_producto}' "
                            f"({item.talla} · {item.color}) solo tiene {variante.stock} unidades en stock."
                        )
                    }
                )

        # Descontar stock de cada variante de forma atómica (RF-14)
        for item in items:
            variante = variantes_bloqueadas[item.variante_id]
            variante.stock -= item.cantidad
            variante.save(update_fields=["stock"])

        # Incrementar el contador de uso del cupón si se aplicó uno
        if orden.cupon_codigo:
            Coupon.objects.filter(codigo__iexact=orden.cupon_codigo).update(
                usos_actuales=models.F("usos_actuales") + 1
            )

        # Actualizar estados de Pago y Orden (RF-13)
        payment.estado = Payment.Status.APROBADO
        payment.mensaje_respuesta = "Pago confirmado exitosamente por la pasarela simulada."
        payment.save(update_fields=["estado", "mensaje_respuesta", "actualizado_en"])

        orden.estado = Order.Status.PAGADA
        orden.stock_descontado = True
        orden.save(update_fields=["estado", "stock_descontado"])

        # Vaciar el carrito del cliente o de la sesión tras confirmar el pago
        if orden.user_id:
            Cart.objects.filter(user_id=orden.user_id).delete()
        elif orden.session_key:
            Cart.objects.filter(user=None, session_key=orden.session_key).delete()

        # Enviar correo de confirmación con el resumen del pedido (RF-15)
        destinatario = orden.correo_factura or (orden.user.email if orden.user else "")
        if destinatario:
            lineas = "\n".join(
                f"  - {i.nombre_producto} ({i.talla} · {i.color}) x{i.cantidad}: ${int(i.subtotal):,}"
                for i in items
            )
            send_mail(
                subject=f"ClickModa - Confirmación de tu Pedido #{orden.id}",
                message=(
                    f"Hola {orden.direccion_envio.nombre_completo},\n\n"
                    f"¡Tu pago con referencia {payment.referencia} ha sido APROBADO!\n\n"
                    f"Resumen de tu pedido #{orden.id}:\n{lineas}\n\n"
                    f"Subtotal: ${int(orden.subtotal):,} COP\n"
                    f"Envío: ${int(orden.envio):,} COP\n"
                    f"IVA (19%): ${int(orden.impuestos):,} COP\n"
                    f"Descuento: -${int(orden.descuento):,} COP\n"
                    f"Total pagado: ${int(orden.total):,} COP\n\n"
                    f"Dirección de entrega: {orden.direccion_envio.direccion}, {orden.direccion_envio.ciudad}.\n"
                    f"Gracias por comprar en ClickModa."
                ),
                from_email="no-reply@clickmoda.co",
                recipient_list=[destinatario],
                fail_silently=True,
            )

        return orden

    # --- CASO B: PAGO FALLIDO (RECHAZADO O EXPIRADO) ---
    if resultado in (Payment.Status.RECHAZADO, Payment.Status.EXPIRADO):
        # Si la orden tenía stock descontado previamente, devolverlo a las variantes (RF-14)
        if orden.stock_descontado:
            for item in items:
                variante = variantes_bloqueadas[item.variante_id]
                variante.stock += item.cantidad
                variante.save(update_fields=["stock"])
            orden.stock_descontado = False

        payment.estado = resultado
        payment.mensaje_respuesta = (
            "Pago rechazado o expirado en la pasarela. La reserva de stock fue liberada."
        )
        payment.save(update_fields=["estado", "mensaje_respuesta", "actualizado_en"])

        orden.estado = Order.Status.CANCELADA
        orden.save(update_fields=["estado", "stock_descontado"])
        return orden

    raise ValidationError(
        {"detail": "El resultado debe ser 'APROBADO', 'RECHAZADO' o 'EXPIRADO'."}
    )