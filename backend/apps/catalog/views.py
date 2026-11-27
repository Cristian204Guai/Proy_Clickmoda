from rest_framework import generics, permissions
from .filters import ProductFilter
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["creado_en", "precio_base"]
    ordering = ["-creado_en"]

    def get_queryset(self):
        return (
            Product.objects.filter(activo=True)
            .select_related("categoria")
            .prefetch_related("variantes", "imagenes")
        )


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Product.objects.filter(activo=True)
            .select_related("categoria")
            .prefetch_related("variantes", "imagenes")
        )