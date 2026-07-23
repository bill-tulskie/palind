import datasets.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("datasets", "0018_add_dataset_palind_prefix"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="gene_token",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Gene name or identifier",
                max_length=1024,
                validators=[datasets.models.validate_token],
                verbose_name="Gene",
            ),
        ),
        migrations.AddField(
            model_name="submission",
            name="clinical_classification_token",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Clinical classification",
                max_length=1024,
                validators=[datasets.models.validate_token],
                verbose_name="Clinical classification",
            ),
        ),
    ]
