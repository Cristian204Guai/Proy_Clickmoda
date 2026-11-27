from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

# Register your models here.

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "nombre", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("email", "nombre")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos", {"fields": ("nombre", "telefono", "role")}),
        ("Estado", {"fields": ("is_active", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "nombre", "role", "password1", "password2")}),
    )