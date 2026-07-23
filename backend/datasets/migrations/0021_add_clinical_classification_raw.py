# Generated migration to add raw clinical_classification field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0020_alter_submission_clinical_classification_token_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="clinical_classification",
            field=models.CharField(blank=True, help_text="Clinical classification (raw string, not tokenized)", max_length=255, verbose_name="Clinical classification (raw)"),
        ),
    ]
