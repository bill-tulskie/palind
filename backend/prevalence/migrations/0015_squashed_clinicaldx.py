# Squashed migration to consolidate ClinicalDX changes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prevalence", "0010_disease_snomedct_us_2024_03_01"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClinicalDX",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("umbrella", models.CharField(blank=True, max_length=255)),
                ("gene", models.CharField(blank=True, max_length=255)),
                ("subtype", models.CharField(blank=True, max_length=255)),
                ("label", models.CharField(blank=True, max_length=255)),
                ("clinical_classification", models.CharField(blank=True, max_length=255)),
                ("clinical_dx_code", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Clinical DX",
                "verbose_name_plural": "Clinical DX",
                "ordering": ["umbrella", "gene", "subtype", "label"],
                "unique_together": (("umbrella", "gene", "subtype", "clinical_dx_code"),),
            },
        ),
    ]
