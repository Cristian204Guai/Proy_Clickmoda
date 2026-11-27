from django.contrib import admin
from .models import Category, Product, ProductImage, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden")
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio_base", "porcentaje_iva", "activo")
    list_filter = ("activo", "categoria")
    search_fields = ("nombre", "descripcion")
    inlines = [ProductVariantInline, ProductImageInline]