from django.db import migrations


def migrate_users_to_personnel(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Personnel = apps.get_model("personnel", "Personnel")

    for user in User.objects.all():
        # Si ya estuviera relacionado, no hacemos nada.
        if user.personnel_id:
            continue

        personnel = Personnel.objects.create(
            tin=user.tin,

            identity_card_number=user.identity_card_number,
            identity_card_complement=user.identity_card_complement,
            identity_card_issued_in=user.identity_card_issued_in,

            first_name=user.first_name,
            paternal_last_name=user.paternal_last_name,
            maternal_last_name=user.maternal_last_name,

            rank_id=user.rank_id,
            position_id=user.position_id,
            unit_id=user.unit_id,
            section_id=user.section_id,

            cossmil_card_number=user.cossmil_card_number,
            cossmil_expiration_date=user.cossmil_expiration_date,

            has_driver_license=user.has_driver_license,
            driver_license_number=user.driver_license_number,
            driver_license_category=user.driver_license_category,
            driver_license_expiration_date=(
                user.driver_license_expiration_date
            ),

            is_active=True,
        )

        user.personnel_id = personnel.id
        user.save(update_fields=["personnel"])


class Migration(migrations.Migration):

    dependencies = [
        ("personnel", "0001_initial"),
        ("accounts", "0003_user_personnel"),
    ]

    operations = [
        migrations.RunPython(
            migrate_users_to_personnel,
            migrations.RunPython.noop,
        ),
    ]