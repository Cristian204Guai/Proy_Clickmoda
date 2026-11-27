from rest_framework import serializers

from .models import User


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializador de lectura administrativa de usuarios."""

    ordenes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "nombre",
            "telefono",
            "role",
            "is_active",
            "is_superuser",
            "date_joined",
            "ordenes_count",
        )
        read_only_fields = fields

    def get_ordenes_count(self, obj) -> int:
        annotated = getattr(obj, "ordenes_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.ordenes.count()


class AdminUserUpdateSerializer(serializers.Serializer):
    """Serializador restringido para actualizar estado activo y rol de un usuario."""

    is_active = serializers.BooleanField(required=False)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
