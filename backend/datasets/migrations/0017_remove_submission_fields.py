# Generated migration to remove address_at_birth, zip_code_at_birth, state_at_birth, and country_at_birth fields from Submission model

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("datasets", "0016_alter_submission_address_at_bith_token_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="submission",
            name="zip_code_at_birth_token",
        ),
        migrations.RemoveField(
            model_name="submission",
            name="address_at_birth_token",
        ),
        migrations.RemoveField(
            model_name="submission",
            name="state_at_birth_token",
        ),
        migrations.RemoveField(
            model_name="submission",
            name="country_at_birth_token",
        ),
    ]
