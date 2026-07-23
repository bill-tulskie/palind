import collections
import csv
import os
import random
import string
import tempfile

from django.core.management import call_command
from django.test import TestCase, Client

from accounts.models import Organization, CustomUser
from datasets.models import Dataset

from .management.commands.preprocess_data import Command as PreprocessDataCommand
from .management.commands.generate_duplicate_records import Command as GenerateDuplicateRecordsCommand
from .models import Disease, DiseaseStats, GlobalStats, count_diseases_prevalence


class TestPrevalenceCounting(TestCase):
    def test_prevalence_count(self):
        random.seed(42)
        client = Client()

        DISEASE_NAMES = string.ascii_uppercase
        PATIENTS_PER_DISEASE = 100

        N_ORGANIZATIONS = 5
        N_USERS_PER_ORGANIZATION = 2
        N_DATASETS_PER_USER = 2
        N_SUBMISSIONS_PER_DATASET = 5

        def random_token(length=1024):
            return "".join(random.choice("01") for _ in range(length))

        # Create random tokens for submissions
        tokens = {
            disease: [random_token() for _ in range(PATIENTS_PER_DISEASE)]
            for disease in DISEASE_NAMES
        }

        # Create diseases
        for letter in DISEASE_NAMES:
            Disease.objects.create(name=letter)

        diseases_submitted = set()
        tokens_submitted = set()
        tokens_submitted_per_disease = collections.defaultdict(set)
        contributors_submitted = set()
        contributors_per_disease = collections.defaultdict(set)

        # Create organizations
        for i in range(N_ORGANIZATIONS):
            organization = Organization.objects.create(name=f"Organization {i}")

            # Create users
            for j in range(N_USERS_PER_ORGANIZATION):
                user = CustomUser.objects.create(
                    email=f"user_{CustomUser.objects.count()}@test.com",
                    organization=organization,
                    is_prevalence_counting_user=True,
                )
                client.force_login(user)

                # Create datasets
                for k in range(N_DATASETS_PER_USER):
                    dataset = Dataset.objects.create(
                        name=f"Dataset {Dataset.objects.count()}",
                        created_by=user,
                        organization=organization,
                    )

                    # Create submissions
                    for l in range(N_SUBMISSIONS_PER_DATASET):
                        disease = random.choice(DISEASE_NAMES)
                        token = random.choice(tokens[disease])

                        # Add to submitted sets for comparison later
                        diseases_submitted.add(disease)
                        tokens_submitted.add(disease + token)
                        tokens_submitted_per_disease[disease].add(token)
                        contributors_submitted.add(organization.pk)
                        contributors_per_disease[disease].add(organization.pk)

                        reponse = client.post(
                            "/v2/submit/",
                            data={
                                "disease_id": disease,
                                "first_name_token": token,
                                "last_name_token": token,
                                "sex_at_birth_token": token,
                                "date_of_birth_token": token,
                            },
                            headers={"Authorization": f"Bearer {dataset.api_token}"},
                            content_type="application/json",
                        )
                        self.assertEqual(reponse.status_code, 200)

        # Count prevalence
        count_diseases_prevalence()

        # Check global stats
        self.assertEqual(GlobalStats.objects.last().n_diseases, len(diseases_submitted))
        self.assertEqual(GlobalStats.objects.last().n_patients, len(tokens_submitted))
        self.assertEqual(
            GlobalStats.objects.last().n_contributors, len(contributors_submitted)
        )

        # Check stats per disease
        for ds in DiseaseStats.objects.all():
            self.assertEqual(
                ds.n_patients, len(tokens_submitted_per_disease[ds.disease.name])
            )
            self.assertEqual(
                ds.n_contributors, len(contributors_per_disease[ds.disease.name])
            )


class TestPreprocessDataCommand(TestCase):
    def setUp(self):
        self.command = PreprocessDataCommand()

    def test_normalize_city_of_birth_rules(self):
        city, note = self.command.normalize_city_of_birth("Boston, MA")
        self.assertEqual(city, "Boston")
        self.assertIn("removed comma-delimited state/country", note)

        city, note = self.command.normalize_city_of_birth("Washington, DC")
        self.assertEqual(city, "Washington DC")
        self.assertIn("keeping DC", note)

        city, note = self.command.normalize_city_of_birth("Paris (France)")
        self.assertEqual(city, "Paris")
        self.assertIn("parenthesized qualifier", note)

        city, note = self.command.normalize_city_of_birth("Chicago")
        self.assertEqual(city, "Chicago")
        self.assertEqual(note, "")

        city, note = self.command.normalize_city_of_birth("?")
        self.assertEqual(city, "")
        self.assertIn("single-character placeholder", note)

    def test_transform_data_logs_city_normalization_notes(self):
        data = [
            {
                "ownerId": "owner-a",
                "field_city_of_birth": "Boston, MA",
                "field_clinical": "",
                "field_date_of_birth": "1990-01-01",
                "field_account_first_name": "Alice",
                "field_gender_at_birth": "F",
                "field_diagnosis_gene": "DOID:1",
                "field_account_last_name": "Smith",
                "field_account_middle_name": "",
                "uid": "u1",
                "mail": "a@example.com",
            },
            {
                "ownerId": "owner-b",
                "field_city_of_birth": "Chicago",
                "field_clinical": "",
                "field_date_of_birth": "1991-01-01",
                "field_account_first_name": "Bob",
                "field_gender_at_birth": "M",
                "field_diagnosis_gene": "DOID:2",
                "field_account_last_name": "Jones",
                "field_account_middle_name": "",
                "uid": "u2",
                "mail": "b@example.com",
            },
        ]

        input_headers = data[0].keys()
        (
            valid,
            skipped,
            missing_required_rows,
            curated_city_rows,
            missing_fields,
            skip_stats,
        ) = self.command.transform_data(data, input_headers)

        self.assertEqual(len(valid), 2)
        self.assertEqual(len(skipped), 0)
        self.assertEqual(missing_fields, [])
        self.assertEqual(dict(skip_stats), {})
        self.assertEqual(valid[0]["city_at_birth"], "Boston")
        self.assertEqual(valid[1]["city_at_birth"], "Chicago")

        self.assertEqual(len(missing_required_rows), 0)

        normalization_notes = [
            r for r in curated_city_rows if "Normalized field_city_of_birth" in r["reason"]
        ]
        self.assertEqual(len(normalization_notes), 1)
        self.assertEqual(normalization_notes[0]["uid"], "u1")

    def test_extended_help_text_mentions_city_exception_rules(self):
        help_text = self.command.get_extended_help_text()
        self.assertIn("Washington, DC", help_text)
        self.assertIn("Single-character placeholders", help_text)
        self.assertIn("Paris (France)", help_text)
        self.assertIn("--help-extended", help_text)


class TestGenerateDuplicateRecordsCommand(TestCase):
    def setUp(self):
        self.command = GenerateDuplicateRecordsCommand()

    def _write_input_csv(self, path):
        fieldnames = [
            "id",
            "disease_id",
            "first_name",
            "last_name",
            "date_of_birth",
            "middle_name",
            "sex_at_birth",
            "city_at_birth",
            "clinical_classification",
        ]
        rows = [
            {
                "id": "r1",
                "disease_id": "DOID:1",
                "first_name": "William",
                "last_name": "Smith",
                "date_of_birth": "1990-01-01",
                "middle_name": "Elizabeth",
                "sex_at_birth": "M",
                "city_at_birth": "Boston",
                "clinical_classification": "Class A",
            },
            {
                "id": "r2",
                "disease_id": "DOID:2",
                "first_name": "Alice",
                "last_name": "Jones",
                "date_of_birth": "1992-02-02",
                "middle_name": "",
                "sex_at_birth": "F",
                "city_at_birth": "Chicago",
                "clinical_classification": "Class B",
            },
        ]
        with open(path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _read_output_csv(self, path):
        with open(path, mode="r", newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_generate_duplicate_records_expands_and_transforms_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            in_path = os.path.join(tmpdir, "input.csv")
            out_path = os.path.join(tmpdir, "output.csv")
            self._write_input_csv(in_path)

            call_command(
                "generate_duplicate_records",
                csv=in_path,
                out=out_path,
                seed=42,
            )

            rows = self._read_output_csv(out_path)

        self.assertEqual(len(rows), 8)

        rows_by_id = {row["id"]: row for row in rows}
        for expected_id in [
            "r1",
            "r1-first",
            "r1-middle",
            "r1-middle2",
            "r2",
            "r2-first",
            "r2-middle",
            "r2-middle2",
        ]:
            self.assertIn(expected_id, rows_by_id)

        # Record with middle name present.
        self.assertEqual(rows_by_id["r1"]["first_name"], "William")
        self.assertEqual(rows_by_id["r1-first"]["first_name"], "Bill")
        self.assertEqual(rows_by_id["r1-middle"]["middle_name"], "Beth")
        self.assertEqual(rows_by_id["r1-middle2"]["middle_name"], "E")

        # Record with middle name absent.
        self.assertEqual(rows_by_id["r2"]["middle_name"], "")
        self.assertNotEqual(rows_by_id["r2-middle"]["middle_name"].lower(), "alice")
        self.assertNotEqual(rows_by_id["r2-middle"]["middle_name"].lower(), "jones")

        middle2_value = rows_by_id["r2-middle2"]["middle_name"]
        self.assertTrue(
            middle2_value == "" or (len(middle2_value) == 1 and middle2_value.isalpha())
        )

    def test_middle_name_generation_is_distinct_from_first_and_last(self):
        generated = self.command.generate_distinct_middle_name("Lee", "Ray")
        self.assertNotEqual(generated.lower(), "lee")
        self.assertNotEqual(generated.lower(), "ray")
