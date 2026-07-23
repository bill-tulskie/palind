import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from prevalence.models import ClinicalDX


class Command(BaseCommand):
    help = "Import ClinicalDX data values from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default="data/clinical_dx_data.csv",
            type=str,
            help="Path to the ClinicalDX CSV file",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        imported_count = 0
        updated_count = 0

        with csv_path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required_columns = {
                "umbrella",
                "gene",
                "subtype",
                "label",
                "clinical_classification",
                "clinical_dx_code",
            }
            if not required_columns.issubset(set(reader.fieldnames or [])):
                raise CommandError(
                    "CSV must include columns: umbrella, gene, subtype, label, clinical_classification, clinical_dx_code"
                )

            with transaction.atomic():
                for row in reader:
                    umbrella = (row.get("umbrella") or "").strip()
                    gene = (row.get("gene") or "").strip()
                    subtype = (row.get("subtype") or "").strip()
                    label = (row.get("label") or "").strip()
                    clinical_classification = (row.get("clinical_classification") or "").strip()
                    clinical_dx_code = (row.get("clinical_dx_code") or "").strip()

                    clinical_dx, created = ClinicalDX.objects.update_or_create(
                        umbrella=umbrella,
                        gene=gene,
                        subtype=subtype,
                        clinical_dx_code=clinical_dx_code,
                        defaults={
                            "label": label,
                            "clinical_classification": clinical_classification,
                        },
                    )
                    if created:
                        imported_count += 1
                    else:
                        updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "ClinicalDX import complete. "
                f"Created: {imported_count}, Updated: {updated_count}, "
                f"Total: {ClinicalDX.objects.count()}"
            )
        )
