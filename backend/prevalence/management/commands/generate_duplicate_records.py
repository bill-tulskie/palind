import csv
import os
import random
from argparse import RawTextHelpFormatter

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate duplicate records with controlled name variations from preprocess_data output CSV"

    FIRST_NAME_NICKNAMES = {
        "abigail": "abby",
        "alexander": "alex",
        "alexandra": "alex",
        "andrew": "andy",
        "anthony": "tony",
        "benjamin": "ben",
        "catherine": "kate",
        "charles": "charlie",
        "christopher": "chris",
        "daniel": "dan",
        "david": "dave",
        "edward": "eddie",
        "elizabeth": "liz",
        "emily": "em",
        "george": "georgie",
        "james": "jim",
        "jennifer": "jen",
        "jessica": "jess",
        "john": "jack",
        "joseph": "joe",
        "katherine": "katie",
        "margaret": "maggie",
        "matthew": "matt",
        "michael": "mike",
        "nicholas": "nick",
        "patricia": "pat",
        "rebecca": "becky",
        "richard": "rick",
        "robert": "rob",
        "samantha": "sam",
        "stephanie": "steph",
        "thomas": "tom",
        "victoria": "vicky",
        "william": "bill",
    }

    MIDDLE_NAME_NICKNAMES = {
        "alexander": "alex",
        "alexandra": "ally",
        "andrew": "andy",
        "ann": "annie",
        "benjamin": "ben",
        "christopher": "chris",
        "daniel": "danny",
        "edward": "ed",
        "elizabeth": "beth",
        "francis": "frank",
        "james": "jim",
        "jennifer": "jen",
        "john": "johnny",
        "joseph": "joey",
        "katherine": "kate",
        "margaret": "meg",
        "maria": "ria",
        "matthew": "matt",
        "michael": "mike",
        "nicholas": "nick",
        "patricia": "patty",
        "rebecca": "becky",
        "richard": "rich",
        "robert": "bobby",
        "sarah": "sadie",
        "steven": "steve",
        "thomas": "tom",
        "victoria": "tori",
        "william": "will",
    }

    FALLBACK_MIDDLE_NAMES = [
        "Lee",
        "Ray",
        "Jean",
        "Marie",
        "Ann",
        "Rose",
        "James",
        "Jane",
        "Lou",
        "Kai",
        "June",
        "Gail",
    ]

    RANDOM_MIDDLE_INITIALS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    REQUIRED_COLUMNS = {
        "id",
        "disease_id",
        "first_name",
        "last_name",
        "date_of_birth",
        "middle_name",
        "sex_at_birth",
        "city_at_birth",
        "clinical_classification",
    }

    def add_arguments(self, parser):
        parser.formatter_class = RawTextHelpFormatter
        parser.description = (
            "Generate duplicate records from a CSV produced by preprocess_data.\n"
            "\n"
            "Usage:\n"
            "  ./manage.py generate_duplicate_records --csv INPUT.csv --out OUTPUT.csv [--seed 42]\n"
            "\n"
            "Expected input columns:\n"
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
            "For each input record, the command writes 4 output rows:\n"
            "  1) Original row unchanged\n"
            "  2) First-name variant\n"
            "     - Replaces first_name with a common nickname when available\n"
            "     - Appends '-first' to id\n"
            "  3) Middle-name nickname variant\n"
            "     - Replaces middle_name with a common nickname when middle_name exists\n"
            "     - If middle_name is blank, inserts a generated middle name\n"
            "       that differs from first_name and last_name\n"
            "     - Appends '-middle' to id\n"
            "  4) Middle-name initial variant\n"
            "     - Replaces middle_name with its first letter when middle_name exists\n"
            "     - If middle_name is blank, uses either a random single letter or blank\n"
            "     - Appends '-middle2' to id\n"
        )
        parser.add_argument("--csv", type=str, required=True, help="Path to input CSV file")
        parser.add_argument("--out", type=str, required=True, help="Path to output CSV file")
        parser.add_argument(
            "--seed",
            type=int,
            default=None,
            help="Optional random seed for reproducible middle-name generation",
        )

    def handle(self, *args, **options):
        input_path = options["csv"]
        output_path = options["out"]
        seed = options["seed"]

        if seed is not None:
            random.seed(seed)

        if not os.path.exists(input_path):
            self.stderr.write(self.style.ERROR(f"Input file not found: {input_path}"))
            return

        with open(input_path, mode="r", newline="", encoding="utf-8-sig") as in_f:
            reader = csv.DictReader(in_f)
            fieldnames = reader.fieldnames or []

            missing = sorted(self.REQUIRED_COLUMNS.difference(set(fieldnames)))
            if missing:
                self.stderr.write(
                    self.style.ERROR(
                        "Input CSV is missing required columns: " + ", ".join(missing)
                    )
                )
                return

            rows = [dict(row) for row in reader]

        output_rows = []
        for row in rows:
            output_rows.append(row)
            output_rows.append(self.make_first_name_variant(row))
            output_rows.append(self.make_middle_name_nickname_variant(row))
            output_rows.append(self.make_middle_name_initial_variant(row))

        with open(output_path, mode="w", newline="", encoding="utf-8") as out_f:
            writer = csv.DictWriter(out_f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        self.stdout.write(
            self.style.SUCCESS(
                "Duplicate record generation complete. "
                f"Input rows: {len(rows)}, Output rows: {len(output_rows)}"
            )
        )

    def make_first_name_variant(self, row):
        variant = dict(row)
        variant["id"] = f"{row.get('id', '')}-first"
        first_name = (row.get("first_name") or "").strip()
        if first_name:
            variant["first_name"] = self.nickname_for_name(
                first_name,
                self.FIRST_NAME_NICKNAMES,
                fallback_short=True,
            )
        return variant

    def make_middle_name_nickname_variant(self, row):
        variant = dict(row)
        variant["id"] = f"{row.get('id', '')}-middle"

        middle_name = (row.get("middle_name") or "").strip()
        first_name = (row.get("first_name") or "").strip()
        last_name = (row.get("last_name") or "").strip()

        if middle_name:
            variant["middle_name"] = self.nickname_for_name(
                middle_name,
                self.MIDDLE_NAME_NICKNAMES,
                fallback_short=True,
            )
        else:
            variant["middle_name"] = self.generate_distinct_middle_name(first_name, last_name)

        return variant

    def make_middle_name_initial_variant(self, row):
        variant = dict(row)
        variant["id"] = f"{row.get('id', '')}-middle2"

        middle_name = (row.get("middle_name") or "").strip()
        if middle_name:
            variant["middle_name"] = middle_name[0]
        else:
            # Choose a single-letter middle initial or blank when middle name is absent.
            variant["middle_name"] = random.choice(["", random.choice(self.RANDOM_MIDDLE_INITIALS)])

        return variant

    def nickname_for_name(self, original_name, lookup, fallback_short=False):
        key = original_name.lower()
        nickname = lookup.get(key)
        if nickname:
            return self.match_case(original_name, nickname)

        if fallback_short and len(original_name) > 3:
            return original_name[:3]

        return original_name

    def generate_distinct_middle_name(self, first_name, last_name):
        first_lower = first_name.lower()
        last_lower = last_name.lower()

        options = [
            name for name in self.FALLBACK_MIDDLE_NAMES
            if name.lower() not in {first_lower, last_lower}
        ]

        if not options:
            options = ["Lee"]

        return random.choice(options)

    def match_case(self, source_name, replacement):
        if source_name.isupper():
            return replacement.upper()
        if source_name[:1].isupper():
            return replacement.capitalize()
        return replacement.lower()