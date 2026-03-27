# Generated migration to add palind_prefix field to Dataset model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("datasets", "0017_remove_submission_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="palind_prefix",
            field=models.CharField(
                blank=True,
                help_text="Prefix used for PALIND identifiers",
                max_length=200,
            ),
        ),
    ]