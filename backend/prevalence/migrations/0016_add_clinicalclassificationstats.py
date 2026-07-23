# Generated migration for ClinicalClassificationStats
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("prevalence", "0015_squashed_clinicaldx"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClinicalClassificationStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clinical_classification", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("n_contributors", models.PositiveIntegerField(default=0)),
                ("n_patients", models.PositiveIntegerField(default=0)),
                ("confidence", models.CharField(choices=[("low", "low"), ("medium", "medium"), ("high", "high")], max_length=20)),
                ("disease", models.ForeignKey(on_delete=models.deletion.CASCADE, to="prevalence.disease")),
                ("global_stats", models.ForeignKey(on_delete=models.deletion.CASCADE, to="prevalence.globalstats")),
            ],
            options={
                "verbose_name": " Clinical Classification Stats",
                "verbose_name_plural": " Clinical Classification Stats",
            },
        ),
    ]
