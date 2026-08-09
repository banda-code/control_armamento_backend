from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.organization.models import (
    Institution,
    Position,
    Rank,
    Unit,
)

from .models import User, UserRole


class UserModelTests(TestCase):
    def setUp(self):
        institution = Institution.objects.create(
            name="Armada Boliviana",
            acronym="AB",
        )
        self.unit = Unit.objects.create(
            institution=institution,
            name="Unidad Piloto",
            acronym="UP",
            code="UP-001",
        )
        self.rank = Rank.objects.create(
            name="Teniente de Fragata",
            abbreviation="TF",
            order=1,
        )
        self.position = Position.objects.create(
            name="Encargado de Armamento",
        )

    def test_rejects_non_institutional_email(self):
        user = User(
            tin="12345",
            email="usuario@gmail.com",
            first_name="Juan",
            paternal_last_name="Pérez",
            rank=self.rank,
            position=self.position,
            unit=self.unit,
            role=UserRole.ARMAMENT_OFFICER,
        )

        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_unit_role_requires_unit(self):
        user = User(
            tin="12346",
            email="juan.perez@armada.mil.bo",
            first_name="Juan",
            paternal_last_name="Pérez",
            rank=self.rank,
            position=self.position,
            role=UserRole.ARMAMENT_OFFICER,
        )

        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_command_role_has_global_scope(self):
        user = User(
            tin="12347",
            email="comando@armada.mil.bo",
            first_name="Usuario",
            paternal_last_name="Comando",
            rank=self.rank,
            position=self.position,
            role=UserRole.NAVY_COMMAND,
        )

        self.assertTrue(user.has_global_scope)
