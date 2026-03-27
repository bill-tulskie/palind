import csv
import json
import os
from collections import defaultdict
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Preprocess data for the prevalence database"

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, required=True, help='Path to input CSV file')
        parser.add_argument('--out', type=str, required=True, help='Path to output CSV file')
        parser.add_argument('--json', type=str, help='Path to output JSON file (optional)')
        parser.add_argument('--no-profile', type=str, required=True, help='Path to output file for skipped records')

    def handle(self, *args, **options):
        input_path = options['csv']
        output_csv_path = options['out']
        output_json_path = options['json'] or output_csv_path.replace('.csv', '.json')
        no_profile_path = options['no_profile']

        if not os.path.exists(input_path):
            self.stderr.write(self.style.ERROR(f"Input file not found: {input_path}"))
            return

        data = self.csv_to_json_array(input_path)
        header = data[0].keys() if data else []
        valid, skipped, missing_fields, skip_stats = self.transform_data(data, header)

        if missing_fields:
            self.stdout.write(self.style.WARNING(
                f"The following expected columns were missing from input: {', '.join(missing_fields)}"
            ))

        self.write_csv(valid, output_csv_path)
        self.write_json(valid, output_json_path)
        self.write_no_profile_csv(skipped, no_profile_path)

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
            "middle_name", "sex_at_birth", "city_at_birth"
        ]

        # Required input fields (middle name is optional)
        required_input_fields = [
            "field_city_of_birth", "field_clinical", "field_date_of_birth",
            "field_account_first_name", "field_gender_at_birth",
            "field_account_last_name"
        ]

        # Mapping from input field names to output column names
        mapping = {
            "ownerId": "id",
            "field_diagnosis_gene": "disease_id",
            "field_account_first_name": "first_name",
            "field_account_last_name": "last_name",
            "field_date_of_birth": "date_of_birth",
            "field_account_middle_name": "middle_name",  # optional
            "field_gender_at_birth": "sex_at_birth",
            "field_city_of_birth": "city_at_birth"
        }

        # Track missing fields in header (except optional middle name)
        missing_fields = [
            field for field in required_input_fields + list(mapping.keys())
            if field not in input_headers and field != "field_account_middle_name"
        ]

        valid_rows = []
        skipped_rows = []
        skip_stats = defaultdict(int)

        for row in data:
            missing_reason = []

            for field in required_input_fields:
                if not row.get(field, "").strip():
                    missing_reason.append(field)

            if missing_reason:
                reason_key = ", ".join(missing_reason)
                skip_stats[reason_key] += 1
                skipped_rows.append({
                    "ownerId": row.get("ownerId", ""),
                    "uid": row.get("uid", ""),
                    "mail": row.get("mail", ""),
                    "reason": "; ".join(missing_reason)
                })
                continue

            new_row = {col: "" for col in output_columns}
            for old_key, new_key in mapping.items():
                new_row[new_key] = row.get(old_key, "")
            valid_rows.append(new_row)

        return valid_rows, skipped_rows, missing_fields, skip_stats

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

    def write_no_profile_csv(self, data, output_path):
        if not data:
            self.stdout.write(self.style.WARNING("No skipped records to write."))
            return
        with open(output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["ownerId", "uid", "mail", "reason"])
            writer.writeheader()
            writer.writerows(data)