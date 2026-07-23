# Migration to remove clinical_classification_token from Submission
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("datasets", "0021_add_clinical_classification_raw"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="submission",
            name="clinical_classification_token",
        ),
    ]
