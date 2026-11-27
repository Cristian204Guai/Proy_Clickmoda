import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(method="filter_category")
    size = django_filters.CharFilter(field_name="variantes__talla", lookup_expr="iexact")
    color = django_filters.CharFilter(field_name="variantes__color", lookup_expr="iexact")
    min_price = django_filters.NumberFilter(field_name="precio_base", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="precio_base", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category", "size", "color", "min_price", "max_price"]

    def filter_category(self, queryset, name, value):
        slugs = [s.strip() for s in value.split(",") if s.strip()]
        if not slugs:
            return queryset
        return queryset.filter(categoria__slug__in=slugs)

    def filter_queryset(self, queryset):
        return super().filter_queryset(queryset).distinct()