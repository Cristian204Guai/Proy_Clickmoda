from django.urls import path
from .views import PaymentWebhookSimulatorView

urlpatterns = [
    path("webhook/", PaymentWebhookSimulatorView.as_view(), name="payment-webhook"),
]