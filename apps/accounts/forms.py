from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = (
            "email",
            "personnel",
            "role",
            "is_active",
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get(
            "password1"
        )
        password2 = self.cleaned_data.get(
            "password2"
        )

        if (
            password1
            and password2
            and password1 != password2
        ):
            raise forms.ValidationError(
                "Las contraseñas no coinciden."
            )

        return password2

    def clean_personnel(self):
        personnel = self.cleaned_data.get(
            "personnel"
        )

        if not personnel:
            raise forms.ValidationError(
                "Debe seleccionar al personal militar "
                "asociado a esta cuenta."
            )

        if not personnel.is_active:
            raise forms.ValidationError(
                "El personal militar seleccionado "
                "no se encuentra activo."
            )

        if User.objects.filter(
            personnel=personnel
        ).exists():
            raise forms.ValidationError(
                "Este personal militar ya tiene "
                "una cuenta de usuario asociada."
            )

        return personnel

    def save(self, commit=True):
        user = super().save(
            commit=False
        )

        user.set_password(
            self.cleaned_data["password1"]
        )

        if commit:
            user.save()

        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Contraseña",
        help_text=(
            "Las contraseñas no se almacenan "
            "en texto plano. Utilice la opción "
            "de cambio de contraseña."
        ),
    )

    class Meta:
        model = User
        fields = "__all__"

    def clean_personnel(self):
        personnel = self.cleaned_data.get(
            "personnel"
        )

        # Un superusuario técnico puede existir
        # sin Personnel asociado.
        if (
            not personnel
            and self.instance.is_superuser
        ):
            return personnel

        if not personnel:
            raise forms.ValidationError(
                "La cuenta debe estar asociada "
                "a un registro de personal militar."
            )

        existing_user = User.objects.filter(
            personnel=personnel
        ).exclude(
            pk=self.instance.pk
        ).first()

        if existing_user:
            raise forms.ValidationError(
                "Este personal militar ya está "
                "asociado a otra cuenta."
            )

        return personnel

    def clean_password(self):
        return self.initial["password"]