from rest_framework import serializers
from .models import Category, Product, ProductImage, ProductVariant


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "nombre", "slug", "orden")


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ("id", "talla", "color", "color_hex", "sku", "stock")


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    es_archivo = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "url", "orden", "es_archivo")

    def get_url(self, obj) -> str:
        return obj.get_resolved_url(self.context.get("request"))

    def get_es_archivo(self, obj) -> bool:
        return bool(obj.imagen)


class ProductSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    categoria_slug = serializers.CharField(source="categoria.slug", read_only=True)
    variantes = ProductVariantSerializer(many=True, read_only=True)
    imagenes = ProductImageSerializer(many=True, read_only=True)
    tallas_disponibles = serializers.SerializerMethodField()
    stock_total = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "nombre",
            "descripcion",
            "categoria",
            "categoria_nombre",
            "categoria_slug",
            "precio_base",
            "porcentaje_iva",
            "activo",
            "creado_en",
            "tallas_disponibles",
            "stock_total",
            "variantes",
            "imagenes",
        )

    def get_tallas_disponibles(self, obj):
        orden_tallas = ["XS", "S", "M", "L", "XL"]
        tallas = {v.talla for v in obj.variantes.all() if v.stock > 0}
        return [t for t in orden_tallas if t in tallas]

    def get_stock_total(self, obj):
        return sum(v.stock for v in obj.variantes.all())