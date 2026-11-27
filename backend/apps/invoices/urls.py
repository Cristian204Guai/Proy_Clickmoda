from django.urls import path
from .views import (
    InvoiceDetailView,
    InvoicePdfDownloadView,
    InvoiceResendEmailView,
    InvoiceXmlDownloadView,
)

urlpatterns = [
    path("<int:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("<int:pk>/pdf/", InvoicePdfDownloadView.as_view(), name="invoice-pdf"),
    path("<int:pk>/xml/", InvoiceXmlDownloadView.as_view(), name="invoice-xml"),
    path("<int:pk>/resend/", InvoiceResendEmailView.as_view(), name="invoice-resend"),
]