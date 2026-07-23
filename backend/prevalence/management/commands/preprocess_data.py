import csv
import json
import os
import re
from collections import defaultdict
from argparse import RawTextHelpFormatter

from django.core.management.base import BaseCommand
from prevalence.models import ClinicalDX


class Command(BaseCommand):

    def run_from_argv(self, argv):
        if "--help-extended" in argv:
            self.stdout.write(self.get_extended_help_text())
            return
        super().run_from_argv(argv)

    def get_extended_help_text(self):
        return (
            "Extended help for preprocess_data\n"
            "\n"
            "field_city_of_birth normalization and exception handling:\n"
            "  1) Comma-delimited values\n"
            "     - Example: 'Boston, MA' -> 'Boston'\n"
            "     - Removes the comma and trailing state/country qualifier.\n"
            "\n"
            "  2) Washington, DC special case\n"
            "     - Example: 'Washington, DC' -> 'Washington DC'\n"
            "     - Removes only the comma and preserves 'DC'.\n"
            "\n"
            "  3) Parenthesized qualifiers\n"
            "     - Example: 'Paris (France)' -> 'Paris'\n"
            "     - Removes the trailing parenthesized qualifier.\n"
            "\n"
            "  4) Single-character placeholders\n"
            "     - Example: '?' or '.' -> ''\n"
            "     - Treated as missing city and written as blank in output.\n"
            "\n"
            "  5) Blank/null values\n"
            "     - Remain blank in output.\n"
            "\n"
            "missing-required / curated-city output behavior:\n"
            "  - Rows skipped for missing required fields are recorded in --missing-required.\n"
            "  - Rows with normalized city values are recorded in --curated-city\n"
            "    with an explanation of the normalization applied.\n"
            "\n"
            "Usage:\n"
            "  ./manage.py preprocess_data --help-extended\n"
        )

    def add_arguments(self, parser):
        parser.formatter_class = RawTextHelpFormatter
        parser.description = (
            "Preprocess a source CSV dataset for Upload and PALIND generation.\n"
            "\n"
            "Usage:\n"
            "  ./manage.py preprocess_data --csv INPUT.csv --out OUTPUT.csv "
            "--missing-required MISSING_REQUIRED.csv --curated-city CURATED_CITY.csv [--json OUTPUT.json]\n"
            "\n"
            "Expected input fields:\n"
            "  ownerId (ignored)\n"
            "  field_city_of_birth\n"
            "  field_clinical\n"
            "  field_date_of_birth\n"
            "  field_account_first_name\n"
            "  field_gender_at_birth\n"
            "  field_diagnosis_gene\n"
            "  field_account_last_name\n"
            "  field_account_middle_name (optional)\n"
            "  uid\n"
            "  mail (ignored)\n"
            "\n"
            "Output fields written to --out / --json:\n"
            "  id\n"
            "  disease_id\n"
            "  first_name\n"
            "  last_name\n"
            "  date_of_birth\n"
            "  middle_name\n"
            "  sex_at_birth\n"
            "  city_at_birth\n"
            "  clinical_classification\n"
            "\n"
            "Input to output mappings:\n"
            "  uid -> id\n"
            "  field_clinical -> lookup in prevalence_clinicaldx.label -> clinical_classification\n"
            "  field_diagnosis_gene -> disease_id\n"
            "  field_account_first_name -> first_name\n"
            "  field_account_last_name -> last_name\n"
            "  field_date_of_birth -> date_of_birth\n"
            "  field_account_middle_name -> middle_name\n"
            "  field_gender_at_birth -> sex_at_birth\n"
            "  field_city_of_birth -> city_at_birth\n"
            "\n"
            "Outputs:\n"
            "  --out: CSV file containing normalized prevalence upload rows\n"
            "  --json: optional JSON representation of the same normalized rows\n"
            "  --missing-required: CSV file with skipped records missing required fields\n"
            "  --curated-city: CSV file with city_at_birth normalization notes\n"
        )
        parser.add_argument('--csv', type=str, required=True, help='Path to input CSV file')
        parser.add_argument('--out', type=str, required=True, help='Path to output CSV file')
        parser.add_argument('--json', type=str, help='Path to output JSON file (optional)')
        parser.add_argument('--missing-required', type=str, required=True, help='Path to output file for rows skipped due to missing required fields')
        parser.add_argument('--curated-city', type=str, required=True, help='Path to output file for city_at_birth normalization notes')
        parser.add_argument('--help-extended', action='store_true', help='Show extended help for city normalization and exit')

    def handle(self, *args, **options):
        input_path = options['csv']
        output_csv_path = options['out']
        output_json_path = options['json'] or output_csv_path.replace('.csv', '.json')
        missing_required_path = options['missing_required']
        curated_city_path = options['curated_city']

        if not os.path.exists(input_path):
            self.stderr.write(self.style.ERROR(f"Input file not found: {input_path}"))
            return

        data = self.csv_to_json_array(input_path)
        header = data[0].keys() if data else []
        (
            valid,
            skipped,
            missing_required_rows,
            curated_city_rows,
            missing_fields,
            skip_stats,
        ) = self.transform_data(data, header)

        if missing_fields:
            self.stdout.write(self.style.WARNING(
                f"The following expected columns were missing from input: {', '.join(missing_fields)}"
            ))

        self.write_csv(valid, output_csv_path)
        self.write_json(valid, output_json_path)
        self.write_missing_required_csv(missing_required_rows, missing_required_path)
        self.write_curated_city_csv(curated_city_rows, curated_city_path)

        # Print summary
        self.stdout.write(self.style.SUCCESS(f"\nSummary:"))
        self.stdout.write(f"  Total records processed: {len(data)}")
        self.stdout.write(f"  Records written to output: {len(valid)}")
        self.stdout.write(f"  Records skipped: {len(skipped)}")

        if skipped:
            self.stdout.write("\nReasons for skipping:")
            for reason, count in skip_stats.items():
                self.stdout.write(f"  {count} record(s) missing: {reason}")

    def csv_to_json_array(self, file_path):
        with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            return [dict(row) for row in reader if any(row.values())]

    def transform_data(self, data, input_headers):
        output_columns = [
            "id", "disease_id", "first_name", "last_name", "date_of_birth",
            "middle_name", "sex_at_birth", "city_at_birth",
            "clinical_classification"
        ]

        # Required input fields (middle name is optional)
        required_input_fields = [
            "field_city_of_birth", "field_date_of_birth",
            "field_account_first_name", "field_gender_at_birth",
            "field_diagnosis_gene",
            "field_account_last_name"
        ]

        # Mapping from input field names to output column names
        mapping = {
            "uid": "id",
            "field_diagnosis_gene": "disease_id",
            "field_account_first_name": "first_name",
            "field_account_last_name": "last_name",
            "field_date_of_birth": "date_of_birth",
            "field_account_middle_name": "middle_name",  # optional
            "field_gender_at_birth": "sex_at_birth"
        }

        # Build case-insensitive label -> clinical_classification lookup.
        clinical_lookup = {}
        for dx in ClinicalDX.objects.exclude(label="").values("label", "clinical_classification"):
            label_key = (dx["label"] or "").strip().lower()
            if label_key and label_key not in clinical_lookup:
                clinical_lookup[label_key] = (dx["clinical_classification"] or "").strip()

        # Track missing fields in header (except optional middle name)
        missing_fields = [
            field for field in required_input_fields + list(mapping.keys())
            if field not in input_headers and field != "field_account_middle_name"
        ]

        valid_rows = []
        skipped_rows = []
        missing_required_rows = []
        curated_city_rows = []
        skip_stats = defaultdict(int)

        for row in data:
            missing_reason = []

            for field in required_input_fields:
                if not row.get(field, "").strip():
                    missing_reason.append(field)

            clinical_label = (row.get("field_clinical", "") or "").strip()
            if clinical_label:
                clinical_classification = clinical_lookup.get(clinical_label.lower(), "not_found")
            else:
                clinical_classification = ""

            if missing_reason:
                reason_key = ", ".join(missing_reason)
                skip_stats[reason_key] += 1
                skipped_record = {
                    "uid": row.get("uid", ""),
                    "mail": row.get("mail", ""),
                    "reason": "; ".join(missing_reason)
                }
                skipped_rows.append(skipped_record)
                missing_required_rows.append(skipped_record)
                continue

            original_city = (row.get("field_city_of_birth", "") or "").strip()
            normalized_city, city_note = self.normalize_city_of_birth(original_city)

            new_row = {col: "" for col in output_columns}
            for old_key, new_key in mapping.items():
                new_row[new_key] = row.get(old_key, "")
            new_row["city_at_birth"] = normalized_city
            new_row["clinical_classification"] = clinical_classification
            valid_rows.append(new_row)

            if city_note:
                curated_city_rows.append({
                    "uid": row.get("uid", ""),
                    "mail": row.get("mail", ""),
                    "reason": (
                        f"Normalized field_city_of_birth from '{original_city}' to '{normalized_city}': {city_note}"
                    ),
                })

        return (
            valid_rows,
            skipped_rows,
            missing_required_rows,
            curated_city_rows,
            missing_fields,
            skip_stats,
        )

    def normalize_city_of_birth(self, city_value):
        city = (city_value or "").strip()
        if not city:
            return "", ""

        # Placeholder markers like '?' or '.' are treated as missing city values.
        if len(city) == 1:
            return "", "single-character placeholder city value treated as blank"

        normalized = city
        notes = []

        # Remove trailing parenthesized country/state text: "City (Country)" -> "City"
        without_parenthetical = re.sub(r"\s*\([^)]*\)\s*$", "", normalized).strip()
        if without_parenthetical != normalized:
            normalized = without_parenthetical
            notes.append("removed trailing parenthesized qualifier")

        # Handle comma-delimited qualifiers: "City, State/Country" -> "City"
        if "," in normalized:
            left, right = [part.strip() for part in normalized.split(",", 1)]
            if left.lower() == "washington" and right.upper() == "DC":
                normalized = "Washington DC"
                notes.append("removed comma for Washington, DC while keeping DC")
            else:
                normalized = left
                notes.append("removed comma-delimited state/country")

        return normalized, "; ".join(notes)

    def write_csv(self, data, output_path):
        if not data:
            self.stderr.write(self.style.WARNING("No valid data to write to CSV."))
            return
        with open(output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    def write_json(self, data, output_path):
        if not data:
            self.stderr.write(self.style.WARNING("No valid data to write to JSON."))
            return
        with open(output_path, mode='w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def write_missing_required_csv(self, data, output_path):
        if not data:
            self.stdout.write(self.style.WARNING("No rows with missing required fields to write."))
            return
        with open(output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["uid", "mail", "reason"])
            writer.writeheader()
            writer.writerows(data)

    def write_curated_city_csv(self, data, output_path):
        if not data:
            self.stdout.write(self.style.WARNING("No curated city_at_birth rows to write."))
            return
        with open(output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["uid", "mail", "reason"])
            writer.writeheader()
            writer.writerows(data)