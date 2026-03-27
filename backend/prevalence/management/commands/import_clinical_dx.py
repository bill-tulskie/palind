import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from prevalence.models import ClinicalDiagnosis


class Command(BaseCommand):
    help = "Import clinical diagnosis values from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default="data/disease-ontologies/clinical_dx.csv",
            type=str,
            help="Path to the clinical diagnosis CSV file",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        imported_count = 0
        updated_count = 0

        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required_columns = {"label", "clinical_dx_code"}
            if not required_columns.issubset(set(reader.fieldnames or [])):
                raise CommandError(
                    "CSV must include columns: label, clinical_dx_code"
                )

            with transaction.atomic():
                for row in reader:
                    label = (row.get("label") or "").strip()
                    clinical_dx_code = (row.get("clinical_dx_code") or "").strip()

                    if not label or not clinical_dx_code:
                        continue

                    _, created = ClinicalDiagnosis.objects.update_or_create(
                        clinical_dx_code=clinical_dx_code,
                        defaults={"label": label},
                    )
                    if created:
                        imported_count += 1
                    else:
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Clinical diagnoses import complete. "
                f"Created: {imported_count}, Updated: {updated_count}, "
                f"Total: {ClinicalDiagnosis.objects.count()}"
            )
        )
