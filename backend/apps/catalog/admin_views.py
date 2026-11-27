from django.db import transaction
from django.db.models import Count, Max, ProtectedError, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole
from apps.orders.models import OrderItem
from .admin_serializers import (
    AdminCategorySerializer,
    AdminProductSerializer,
    validate_uploaded_image,
)
from .models import Category, Product, ProductImage
from .serializers import ProductImageSerializer


class AdminCategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.annotate(
            productos_count=Count("productos")
        ).order_by("orden", "nombre")


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdminCategorySerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Category.objects.annotate(
            productos_count=Count("productos")
        ).order_by("orden", "nombre")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.productos.exists():
            return Response(
                {
                    "detail": (
                        "No se puede eliminar la categoría porque tiene productos asociados."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        try:
            instance.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "No se puede eliminar la categoría porque tiene productos asociados."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminProductListCreateView(generics.ListCreateAPIView):
    serializer_class = AdminProductSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filter_backends = []

    def get_queryset(self):
        queryset = (
            Product.objects.select_related("categoria")
            .prefetch_related("variantes", "imagenes")
            .annotate(stock_total=Coalesce(Sum("variantes__stock"), 0))
            .order_by("-creado_en", "-id")
        )

        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )

        category = (self.request.query_params.get("category") or "").strip()
        if category:
            if category.isdigit():
                queryset = queryset.filter(categoria_id=int(category))
            else:
                queryset = queryset.filter(categoria__slug=category)

        estado = (self.request.query_params.get("estado") or "").strip().lower()
        if estado == "activo":
            queryset = queryset.filter(activo=True, stock_total__gt=0)
        elif estado == "agotado":
            queryset = queryset.filter(activo=True, stock_total=0)
        elif estado == "inactivo":
            queryset = queryset.filter(activo=False)

        return queryset


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdminProductSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Product.objects.select_related("categoria")
            .prefetch_related("variantes", "imagenes")
            .annotate(stock_total=Coalesce(Sum("variantes__stock"), 0))
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if OrderItem.objects.filter(variante__producto=instance).exists():
            instance.activo = False
            instance.save(update_fields=["activo"])
            return Response(
                {
                    "detail": "El producto tiene órdenes asociadas y fue desactivado.",
                    "deactivated": True,
                },
                status=status.HTTP_200_OK,
            )
        try:
            with transaction.atomic():
                uploaded_images = [
                    img.imagen for img in instance.imagenes.all() if img.imagen
                ]
                instance.delete()
                for img_field in uploaded_images:
                    img_field.delete(save=False)
        except ProtectedError:
            instance.activo = False
            instance.save(update_fields=["activo"])
            return Response(
                {
                    "detail": "El producto tiene órdenes asociadas y fue desactivado.",
                    "deactivated": True,
                },
                status=status.HTTP_200_OK,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminProductImageUploadView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk: int):
        product = get_object_or_404(Product, pk=pk)
        files = request.FILES.getlist("imagenes") or request.FILES.getlist("imagen")
        if not files:
            return Response(
                {"detail": "Debes adjuntar al menos una imagen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for file_obj in files:
            validate_uploaded_image(file_obj)

        with transaction.atomic():
            max_orden = product.imagenes.aggregate(max_orden=Max("orden"))["max_orden"]
            siguiente_orden = 0 if max_orden is None else max_orden + 1
            created = []
            for file_obj in files:
                img = ProductImage.objects.create(
                    producto=product,
                    imagen=file_obj,
                    orden=siguiente_orden,
                )
                created.append(img)
                siguiente_orden += 1

        serializer = ProductImageSerializer(
            created, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminProductImageDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, pk: int, image_id: int):
        img = get_object_or_404(ProductImage, pk=image_id, producto_id=pk)
        if img.imagen:
            img.imagen.delete(save=False)
        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
