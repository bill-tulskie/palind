# Migration to add clinical_classification_token back to Submission
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0022_remove_clinical_classification_token"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="clinical_classification_token",
            field=models.CharField(blank=True, max_length=1024, null=False),
        ),
    ]
