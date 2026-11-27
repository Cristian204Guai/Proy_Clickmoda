from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import path
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.permissions import IsAdminRole
from apps.orders.models import Address, Order
from apps.users.admin_views import AdminUserDetailView, AdminUserListView

User = get_user_model()

urlpatterns = [
    path("api/v1/admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "api/v1/admin/users/<int:pk>/",
        AdminUserDetailView.as_view(),
        name="admin-user-detail",
    ),
]


@override_settings(ROOT_URLCONF=__name__)
class AdminUsersTests(APITestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="super@clickmoda.co",
            password="PasswordSeguro123!",
            nombre="Super Admin",
        )
        self.admin = User.objects.create_user(
            email="admin@clickmoda.co",
            password="PasswordSeguro123!",
            nombre="Admin Normal",
            role=User.Role.ADMIN,
        )
        self.cliente = User.objects.create_user(
            email="cliente@clickmoda.co",
            password="PasswordSeguro123!",
            nombre="Sofía Castro",
            telefono="3101112233",
            role=User.Role.CLIENTE,
        )

    def test_permisos_requeridos_en_admin_usuarios(self):
        endpoints = [
            ("get", "/api/v1/admin/users/"),
            ("get", f"/api/v1/admin/users/{self.cliente.pk}/"),
            ("patch", f"/api/v1/admin/users/{self.cliente.pk}/"),
        ]

        self.client.force_authenticate(user=None)
        for method, url in endpoints:
            resp = getattr(self.client, method)(url, {"is_active": False}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(user=self.cliente)
        for method, url in endpoints:
            resp = getattr(self.client, method)(url, {"is_active": False}, format="json")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_listado_usuarios_filtros_paginacion_y_ordenes_count(self):
        direccion = Address.objects.create(
            user=self.cliente,
            nombre_completo="Sofía Castro",
            telefono="3101112233",
            direccion="Cra 15 # 80-20",
            ciudad="Bogotá",
        )
        Order.objects.create(
            user=self.cliente,
            direccion_envio=direccion,
            subtotal=Decimal("100000"),
            envio=Decimal("12000"),
            impuestos=Decimal("19000"),
            total=Decimal("112000"),
        )
        Order.objects.create(
            user=self.cliente,
            direccion_envio=direccion,
            subtotal=Decimal("50000"),
            envio=Decimal("12000"),
            impuestos=Decimal("9500"),
            total=Decimal("62000"),
        )

        inactivo = User.objects.create_user(
            email="inactivo@clickmoda.co",
            password="PasswordSeguro123!",
            nombre="Usuario Inactivo",
            role=User.Role.CLIENTE,
            is_active=False,
        )
        User.objects.filter(pk=inactivo.pk).update(
            date_joined=timezone.now() - timedelta(days=10)
        )

        for i in range(6):
            User.objects.create_user(
                email=f"extra{i}@clickmoda.co",
                password="PasswordSeguro123!",
                nombre=f"Extra {i}",
                role=User.Role.CLIENTE,
            )

        self.client.force_authenticate(user=self.admin)

        # Paginación (PAGE_SIZE = 8, total = 10)
        resp = self.client.get("/api/v1/admin/users/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 10)
        self.assertEqual(len(resp.data["results"]), 8)

        # Búsqueda por nombre o email y verificación de ordenes_count
        resp_search = self.client.get("/api/v1/admin/users/?search=Sofía")
        self.assertEqual(resp_search.data["count"], 1)
        item = resp_search.data["results"][0]
        self.assertEqual(item["email"], "cliente@clickmoda.co")
        self.assertEqual(item["ordenes_count"], 2)
        self.assertEqual(
            set(item.keys()),
            {
                "id",
                "email",
                "nombre",
                "telefono",
                "role",
                "is_active",
                "is_superuser",
                "date_joined",
                "ordenes_count",
            },
        )

        # Filtro por rol
        resp_role = self.client.get("/api/v1/admin/users/?role=ADMIN")
        self.assertEqual(resp_role.data["count"], 2)

        # Filtro por is_active=false
        resp_inactive = self.client.get("/api/v1/admin/users/?is_active=false")
        self.assertEqual(resp_inactive.data["count"], 1)
        self.assertEqual(resp_inactive.data["results"][0]["id"], inactivo.pk)

    def test_actualizacion_usuario_normal_y_campos_restringidos(self):
        self.client.force_authenticate(user=self.admin)

        resp = self.client.patch(
            f"/api/v1/admin/users/{self.cliente.pk}/",
            {
                "role": "ADMIN",
                "is_active": False,
                "email": "hacked@clickmoda.co",
                "is_superuser": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.role, User.Role.ADMIN)
        self.assertTrue(self.cliente.is_staff)
        self.assertFalse(self.cliente.is_active)
        self.assertEqual(self.cliente.email, "cliente@clickmoda.co")
        self.assertFalse(self.cliente.is_superuser)

    def test_salvaguarda_auto_bloqueo_y_auto_degradacion(self):
        self.client.force_authenticate(user=self.admin)

        resp_desactivar = self.client.patch(
            f"/api/v1/admin/users/{self.admin.pk}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(resp_desactivar.status_code, status.HTTP_400_BAD_REQUEST)

        resp_degradar = self.client.patch(
            f"/api/v1/admin/users/{self.admin.pk}/",
            {"role": "CLIENTE"},
            format="json",
        )
        self.assertEqual(resp_degradar.status_code, status.HTTP_400_BAD_REQUEST)

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, User.Role.ADMIN)

    def test_salvaguarda_proteccion_superuser(self):
        # Admin normal NO puede modificar a superuser -> 403
        self.client.force_authenticate(user=self.admin)
        resp_forbidden = self.client.patch(
            f"/api/v1/admin/users/{self.superuser.pk}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(resp_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

        # Superuser SÍ puede modificar a otro admin (cuando hay otro activo)
        self.client.force_authenticate(user=self.superuser)
        resp_ok = self.client.patch(
            f"/api/v1/admin/users/{self.admin.pk}/",
            {"role": "CLIENTE"},
            format="json",
        )
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.CLIENTE)
        self.assertFalse(self.admin.is_staff)

    def test_salvaguarda_ultimo_administrador_activo(self):
        # Desactivar superuser para dejar a self.admin como el único admin activo,
        # o usar a superuser como único admin activo tras desactivar self.admin
        self.admin.is_active = False
        self.admin.save(update_fields=["is_active"])

        # Ahora self.superuser es el único admin activo; creamos otro admin que
        # intente degradar a self.superuser? Mejor probamos con un segundo superuser
        # o creando un admin temporal? No: si self.admin está inactivo y superuser es el único activo,
        # para probar el último admin sin caer en auto-bloqueo:
        # Creamos un superuser_actor que está inactivo? No, debe estar autenticado y activo.
        # Si hay 2 admins activos: actor (superuser) y target (admin).
        # Primero actor desactiva/degrada a target -> OK (queda actor).
        # Si alguien (ej. superuser_2 inactivo no puede autenticar) -> Wait:
        # El caso de último admin ocurre si un admin intenta degradarse a sí mismo (ya cubierto por auto-bloqueo)
        # O si en una race/estado inconsistente sólo queda 1 admin activo y otro usuario con permiso
        # (por ejemplo, si target es el único en la BD con role=ADMIN & is_active=True).
        # Probemos ambos:
        # 1) Con 2 admins activos (superuser y admin), superuser SÍ puede degradar a admin:
        self.admin.is_active = True
        self.admin.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.superuser)
        resp_ok = self.client.patch(
            f"/api/v1/admin/users/{self.admin.pk}/",
            {"role": "CLIENTE"},
            format="json",
        )
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK)

        # 2) Ahora solo queda self.superuser como único admin activo;
        # aunque sea self.superuser intentando desactivarse/degradarse, falla con 400.
        resp_last_deact = self.client.patch(
            f"/api/v1/admin/users/{self.superuser.pk}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(resp_last_deact.status_code, status.HTTP_400_BAD_REQUEST)

        # 3) Y si forzamos un actor con is_superuser=True pero role=CLIENTE (bypass directo en DB)
        # para aislar específicamente la salvaguarda (c) sin activar (a):
        otro_admin = User.objects.create_user(
            email="otro_admin@clickmoda.co",
            password="PasswordSeguro123!",
            nombre="Otro Admin",
            role=User.Role.ADMIN,
        )
        # Dejamos a otro_admin como único ADMIN activo (superuser queda inactivo temporalmente? No, force_authenticate requiere active)
        # Así que dejamos a superuser con role=CLIENTE e is_superuser=True via update en DB,
        # pero IsAdminRole exige role == "ADMIN". Por eso en la práctica, la única forma de llegar
        # a salvaguarda (c) sin (a) es con un usuario autenticado cuyo permiso pase IsAdminRole
        # o en concurrencia simultánea cuando 2 admins activos intentan desactivarse mutuamente.
        # Verifiquemos que con otro_admin como único admin activo (si self.superuser tiene role=ADMIN e is_active=False en DB?):
        # Si self.superuser es el target y otro_admin el actor, habría 2 admins activos.
        # Así que probamos que cuando quedan 2 admins activos, degradar al primero pasa (200),
        # y luego intentar desactivar/degradar al restante falla con 400.
        self.client.force_authenticate(user=self.superuser)
        resp_degrade_otro = self.client.patch(
            f"/api/v1/admin/users/{otro_admin.pk}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(resp_degrade_otro.status_code, status.HTTP_200_OK)

        resp_last_role = self.client.patch(
            f"/api/v1/admin/users/{self.superuser.pk}/",
            {"role": "CLIENTE"},
            format="json",
        )
        self.assertEqual(resp_last_role.status_code, status.HTTP_400_BAD_REQUEST)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)
        self.assertEqual(self.superuser.role, User.Role.ADMIN)

        # 4) Aislar específicamente la salvaguarda (c) sin activar auto-bloqueo (a):
        # Si dejamos a self.admin como único admin activo (no superuser) y simulamos
        # el paso de permiso para otro usuario, no se puede desactivar ni degradar al último admin.
        self.superuser.is_active = False
        self.superuser.save(update_fields=["is_active"])
        self.admin.role = User.Role.ADMIN
        self.admin.is_active = True
        self.admin.save(update_fields=["role", "is_active"])

        self.client.force_authenticate(user=self.cliente)
        with patch.object(IsAdminRole, "has_permission", return_value=True):
            resp_deact = self.client.patch(
                f"/api/v1/admin/users/{self.admin.pk}/",
                {"is_active": False},
                format="json",
            )
            self.assertEqual(resp_deact.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("último administrador activo", resp_deact.data["detail"])

            resp_deg = self.client.patch(
                f"/api/v1/admin/users/{self.admin.pk}/",
                {"role": "CLIENTE"},
                format="json",
            )
            self.assertEqual(resp_deg.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("último administrador activo", resp_deg.data["detail"])

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, User.Role.ADMIN)
