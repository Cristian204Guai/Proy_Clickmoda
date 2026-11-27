from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdminRole
from .admin_serializers import AdminUserSerializer, AdminUserUpdateSerializer
from .models import User


class AdminUserListView(generics.ListAPIView):
    """Listado paginado de usuarios para administración con filtros y conteo de órdenes."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    filter_backends = []

    def get_queryset(self):
        qs = User.objects.annotate(ordenes_count=Count("ordenes")).order_by(
            "-date_joined", "-id"
        )

        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(email__icontains=search) | Q(nombre__icontains=search))

        role = self.request.query_params.get("role", "").strip().upper()
        if role in (User.Role.CLIENTE, User.Role.ADMIN):
            qs = qs.filter(role=role)
        elif role:
            qs = qs.none()

        is_active_param = self.request.query_params.get("is_active", "").strip().lower()
        if is_active_param == "true":
            qs = qs.filter(is_active=True)
        elif is_active_param == "false":
            qs = qs.filter(is_active=False)

        return qs


class AdminUserDetailView(APIView):
    """Consulta y actualización controlada (is_active y role) de un usuario."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, pk: int):
        usuario = get_object_or_404(
            User.objects.annotate(ordenes_count=Count("ordenes")),
            pk=pk,
        )
        return Response(AdminUserSerializer(usuario).data)

    @transaction.atomic
    def patch(self, request, pk: int):
        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Bloquear en orden determinístico al usuario objetivo y a los administradores activos
        # para evitar condiciones de carrera y deadlocks al validar el último admin activo.
        locked_users = list(
            User.objects.select_for_update()
            .filter(Q(pk=pk) | Q(role=User.Role.ADMIN, is_active=True))
            .order_by("id")
        )
        target = next((u for u in locked_users if u.pk == pk), None)
        if not target:
            get_object_or_404(User, pk=pk)

        if target.is_superuser and not request.user.is_superuser:
            return Response(
                {"detail": "No tienes permisos para modificar una cuenta superadministrador."},
                status=status.HTTP_403_FORBIDDEN,
            )

        new_is_active = serializer.validated_data.get("is_active")
        new_role = serializer.validated_data.get("role")

        resulting_is_active = target.is_active if new_is_active is None else new_is_active
        resulting_role = target.role if new_role is None else new_role

        if target.pk == request.user.pk:
            if not resulting_is_active:
                return Response(
                    {"detail": "No puedes desactivar tu propia cuenta de administrador."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if resulting_role != User.Role.ADMIN:
                return Response(
                    {"detail": "No puedes retirarte tu propio rol de administrador."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        estaba_admin_activo = target.is_active and target.role == User.Role.ADMIN
        seguira_admin_activo = resulting_is_active and resulting_role == User.Role.ADMIN
        if estaba_admin_activo and not seguira_admin_activo:
            otros_admins_activos = [
                u
                for u in locked_users
                if u.pk != target.pk and u.is_active and u.role == User.Role.ADMIN
            ]
            if not otros_admins_activos:
                return Response(
                    {
                        "detail": (
                            "No se puede desactivar ni degradar al último administrador activo del sistema."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        update_fields = []
        if new_is_active is not None and new_is_active != target.is_active:
            target.is_active = new_is_active
            update_fields.append("is_active")

        if new_role is not None and new_role != target.role:
            target.role = new_role
            update_fields.extend(["role", "is_staff"])

        if update_fields:
            target.save(update_fields=update_fields)

        usuario_refrescado = User.objects.annotate(ordenes_count=Count("ordenes")).get(
            pk=target.pk
        )
        return Response(AdminUserSerializer(usuario_refrescado).data, status=status.HTTP_200_OK)
