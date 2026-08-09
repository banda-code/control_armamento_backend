from rest_framework import serializers

from .models import Institution, Position, Rank, Section, Unit


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "acronym",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UnitSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(
        source="institution.name",
        read_only=True,
    )
    parent_name = serializers.CharField(
        source="parent.name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = Unit
        fields = [
            "id",
            "institution",
            "institution_name",
            "name",
            "acronym",
            "code",
            "parent",
            "parent_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution_name",
            "parent_name",
            "created_at",
            "updated_at",
        ]


class RankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rank
        fields = [
            "id",
            "name",
            "abbreviation",
            "order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = [
            "id",
            "name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SectionSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(
        source="unit.name",
        read_only=True,
    )

    class Meta:
        model = Section
        fields = [
            "id",
            "unit",
            "unit_name",
            "name",
            "code",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "unit_name",
            "created_at",
            "updated_at",
        ]
