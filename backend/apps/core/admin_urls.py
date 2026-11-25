from django.urls import path

from apps.catalog.admin_views import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminProductDetailView,
    AdminProductImageDeleteView,
    AdminProductImageUploadView,
    AdminProductListCreateView,
)
from apps.core.admin_views import AdminStatsView
from apps.invoices.admin_views import AdminInvoiceDetailView, AdminInvoiceListView
from apps.orders.admin_views import AdminOrderDetailView, AdminOrderListView
from apps.users.admin_views import AdminUserDetailView, AdminUserListView

urlpatterns = [
    path("stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("categories/", AdminCategoryListCreateView.as_view(), name="admin-category-list-create"),
    path("categories/<int:pk>/", AdminCategoryDetailView.as_view(), name="admin-category-detail"),
    path("products/", AdminProductListCreateView.as_view(), name="admin-product-list-create"),
    path("products/<int:pk>/", AdminProductDetailView.as_view(), name="admin-product-detail"),
    path(
        "products/<int:pk>/images/",
        AdminProductImageUploadView.as_view(),
        name="admin-product-image-upload",
    ),
    path(
        "products/<int:pk>/images/<int:image_id>/",
        AdminProductImageDeleteView.as_view(),
        name="admin-product-image-delete",
    ),
    path("orders/", AdminOrderListView.as_view(), name="admin-order-list"),
    path("orders/<int:pk>/", AdminOrderDetailView.as_view(), name="admin-order-detail"),
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("invoices/", AdminInvoiceListView.as_view(), name="admin-invoice-list"),
    path("invoices/<int:pk>/", AdminInvoiceDetailView.as_view(), name="admin-invoice-detail"),
]
