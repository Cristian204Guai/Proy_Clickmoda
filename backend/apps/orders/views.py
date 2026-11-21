import uuid
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cart.models import Cart
from apps.cart.views import get_or_create_active_cart
from .models import Address, Order, OrderItem
from .serializers import CheckoutCreateSerializer, OrderSerializer
from apps.payments.models import Payment


class OrderListCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if request.user and request.user.is_authenticated:
            ordenes = (Order.objects.filter(user=request.user).select_related(
                "direccion_envio", "payment").prefetch_related("items"))
        else:
            session_key = request.headers.get("X-Cart-Session") or ""
            ordenes = (Order.objects.filter(
                user=None, session_key=session_key
            ).select_related("direccion_envio", "payment").prefetch_related("items"))
        return Response(OrderSerializer(ordenes, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = get_or_create_active_cart(request)
        cart_items = list(cart.items.select_related("variante__producto"))

        if not cart_items:
            return Response(
                {"detail": "Tu carrito está vacío."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validar stock antes de crear la orden (RF-13)
        for item in cart_items:
            if item.variante.stock < item.cantidad:
                return Response(
                    {
                        "detail": (
                            f"Stock insuficiente para '{item.variante.producto.nombre}' "
                            f"({item.variante.talla} · {item.variante.color}). "
                            f"Disponible: {item.variante.stock}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        subtotal = sum(
            (i.variante.producto.precio_base * i.cantidad for i in cart_items),
            Decimal("0"),
        )
        envio = Cart.ENVIO_FIJO
        impuestos = (subtotal * Cart.IVA_PORCENTAJE).quantize(Decimal("1"))
        descuento = (
            cart.cupon.calcular_descuento(subtotal) if cart.cupon else Decimal("0")
        )
        total = max(Decimal("0"), subtotal - descuento) + envio

        user = request.user if request.user and request.user.is_authenticated else None
        direccion = Address.objects.create(
            user=user,
            nombre_completo=data["nombre_completo"],
            telefono=data["telefono"],
            direccion=data["direccion"],
            ciudad=data["ciudad"],
        )

        orden = Order.objects.create(
            user=user,
            session_key=cart.session_key or "",
            direccion_envio=direccion,
            estado=Order.Status.PENDIENTE,
            metodo_pago=data["metodo_pago"],
            token_pago=data.get("token_pago", ""),
            # RF-13: stock_descontado se establece en False al crear la orden
            stock_descontado=False,
            subtotal=subtotal,
            envio=envio,
            impuestos=impuestos,
            descuento=descuento,
            total=total,
            cupon_codigo=cart.cupon.codigo if cart.cupon else "",
            requiere_factura_electronica=data["requiere_factura_electronica"],
            tipo_documento=data.get("tipo_documento", "CC"),
            numero_documento=data.get("numero_documento", ""),
            correo_factura=data.get("correo_factura", "")
            or (user.email if user else ""),
        )


        # Crear OrderItems congelando el precio_unitario y porcentaje_iva al momento de la compra
        for item in cart_items:
            OrderItem.objects.create(
                orden=orden,
                variante=item.variante,
                nombre_producto=item.variante.producto.nombre,
                talla=item.variante.talla,
                color=item.variante.color,
                cantidad=item.cantidad,
                precio_unitario=item.variante.producto.precio_base,
                porcentaje_iva=item.variante.producto.porcentaje_iva,
            )


        # Crear la transacción de pago en estado PENDIENTE (Sección 6: POST /orders crea orden y transacción)
        pasarela = (
            Payment.Gateway.CONTRA_ENTREGA
            if orden.metodo_pago == Order.PaymentMethod.CONTRA_ENTREGA
            else Payment.Gateway.WOMPI_SIM
        )
        referencia = f"CM-PAY-{orden.pk:04d}-{uuid.uuid4().hex[:6].upper()}"
        Payment.objects.create(
            orden=orden,
            pasarela=pasarela,
            referencia=referencia,
            estado=Payment.Status.PENDIENTE,
            monto=orden.total,
            mensaje_respuesta="Transacción iniciada, esperando confirmación de pasarela.",
        )
        orden_completa = (
            Order.objects.select_related("direccion_envio", "payment")
            .prefetch_related("items")
            .get(pk=orden.pk)
        )

        return Response(OrderSerializer(orden_completa).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk: int):
        orden = get_object_or_404(
            Order.objects.select_related("direccion_envio", "payment").prefetch_related("items"), pk=pk
        )
        return Response(OrderSerializer(orden).data)