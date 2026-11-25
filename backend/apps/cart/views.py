from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ProductVariant
from apps.coupons.models import Coupon
from .models import Cart, CartItem
from .serializers import CartSerializer


def get_or_create_active_cart(request) -> Cart:
    """Obtiene el carrito del usuario autenticado o el de la sesión de visitante."""
    if request.user and request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    session_key = (
        request.headers.get("X-Cart-Session")
        or request.query_params.get("session_key")
        or "anon-default"
    )
    cart, _ = Cart.objects.get_or_create(user=None, session_key=session_key[:100])
    return cart


def serialize_cart(cart: Cart, request=None) -> dict:
    cart_prefetched = (
        Cart.objects.select_related("cupon")
        .prefetch_related(
            "items__variante__producto__imagenes",
        )
        .get(pk=cart.pk)
    )
    context = {"request": request} if request is not None else {}
    return CartSerializer(cart_prefetched, context=context).data


class CartDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cart = get_or_create_active_cart(request)
        return Response(serialize_cart(cart, request))


class CartItemCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cart = get_or_create_active_cart(request)
        variante_id = request.data.get("variante_id")
        cantidad = int(request.data.get("cantidad", 1))

        if cantidad < 1:
            return Response(
                {"detail": "La cantidad debe ser al menos 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variante = get_object_or_404(
            ProductVariant.objects.select_related("producto"),
            pk=variante_id,
            producto__activo=True,
        )

        if variante.stock == 0:
            return Response(
                {"detail": f"La variante {variante.talla} · {variante.color} está agotada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item, created = CartItem.objects.get_or_create(
            cart=cart, variante=variante, defaults={"cantidad": 0}
        )
        nueva_cantidad = item.cantidad + cantidad

        if nueva_cantidad > variante.stock:
            return Response(
                {
                    "detail": (
                        f"Stock insuficiente para {variante.producto.nombre} "
                        f"({variante.talla} · {variante.color}). Disponible: {variante.stock}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.cantidad = nueva_cantidad
        item.save()
        return Response(serialize_cart(cart, request), status=status.HTTP_200_OK)


class CartItemDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, pk: int):
        cart = get_or_create_active_cart(request)
        item = get_object_or_404(
            CartItem.objects.select_related("variante__producto"),
            pk=pk,
            cart=cart,
        )
        cantidad = int(request.data.get("cantidad", 1))

        if cantidad <= 0:
            item.delete()
            return Response(serialize_cart(cart, request), status=status.HTTP_200_OK)

        if item.variante.stock == 0:
            return Response(
                {
                    "detail": f"'{item.variante.producto.nombre}' ({item.variante.talla} · {item.variante.color}) se agotó."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cantidad > item.variante.stock:
            return Response(
                {
                    "detail": (
                        f"Solo hay {item.variante.stock} unidades disponibles de "
                        f"'{item.variante.producto.nombre}' ({item.variante.talla} · {item.variante.color})."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        item.cantidad = cantidad
        item.save()
        return Response(serialize_cart(cart, request), status=status.HTTP_200_OK)

    def delete(self, request, pk: int):
        cart = get_or_create_active_cart(request)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        item.delete()
        return Response(serialize_cart(cart, request), status=status.HTTP_200_OK)


class CartCouponView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cart = get_or_create_active_cart(request)
        codigo = (request.data.get("codigo") or "").strip().upper()

        if not codigo:
            cart.cupon = None
            cart.save(update_fields=["cupon"])
            return Response(serialize_cart(cart, request), status=status.HTTP_200_OK)

        cupon = Coupon.objects.filter(codigo__iexact=codigo).first()
        if not cupon:
            return Response(
                {"detail": "El código de cupón ingresado no existe."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valido, motivo = cupon.es_valido()
        if not valido:
            return Response({"detail": motivo}, status=status.HTTP_400_BAD_REQUEST)

        cart.cupon = cupon
        cart.save(update_fields=["cupon"])
        return Response(serialize_cart(cart, request), status=status.HTTP_200_OK)


class CartMergeView(APIView):
    """RF-10: Fusiona el carrito del visitante (sesión o items locales) al iniciar sesión."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        session_key = request.headers.get("X-Cart-Session") or request.data.get("session_key")
        local_items = request.data.get("items", [])

        # 1. Si existe carrito guardado con session_key de visitante, fusionarlo
        if session_key:
            guest_cart = Cart.objects.filter(user=None, session_key=session_key).first()
            if guest_cart and guest_cart.pk != user_cart.pk:
                for g_item in guest_cart.items.select_related("variante"):
                    if g_item.variante.stock <= 0:
                        continue
                    u_item, created = CartItem.objects.get_or_create(
                        cart=user_cart,
                        variante=g_item.variante,
                        defaults={"cantidad": min(g_item.cantidad, g_item.variante.stock)},
                    )
                    if not created:
                        u_item.cantidad = min(
                            u_item.cantidad + g_item.cantidad, g_item.variante.stock
                        )
                        u_item.save()
                if guest_cart.cupon and not user_cart.cupon:
                    user_cart.cupon = guest_cart.cupon
                    user_cart.save(update_fields=["cupon"])
                guest_cart.delete()

        # 2. Si el frontend envía items adicionales desde localStorage
        for entry in local_items:
            var_id = entry.get("variante_id")
            cant = int(entry.get("cantidad", 1))
            if not var_id or cant < 1:
                continue
            variante = ProductVariant.objects.filter(pk=var_id, producto__activo=True).first()
            if not variante or variante.stock <= 0:
                continue
            u_item, created = CartItem.objects.get_or_create(
                cart=user_cart,
                variante=variante,
                defaults={"cantidad": min(cant, variante.stock)},
            )
            if not created:
                u_item.cantidad = min(u_item.cantidad + cant, variante.stock)
                u_item.save()

        return Response(serialize_cart(user_cart, request), status=status.HTTP_200_OK)