import csv
import sys

from django.core.management.base import BaseCommand
from django.db.models.functions import Length

import numpy as np
from faker import Faker


from prevalence.models import Disease


class Command(BaseCommand):
    help = "Create a randomized dataset for prevalence counting"

    def handle(self, *args, **options):
        
        self.stderr.write(self.style.SUCCESS(f"Starting random file generation"))
        
        diseases = (
            Disease.objects.exclude(OMIM__exact="")
            .annotate(name_len=Length("name"))
            .exclude(name__regex=r"\d")
            .filter(name_len__lt=15)
            .order_by("?")
        )
        
        self.stderr.write(self.style.ERROR(f"diseases: {len(diseases)}"))

        faker = Faker()

        HEADER = [
            "id",
            "disease_id",
            "first_name",
            "last_name",
            "date_of_birth",
            "middle_name",
            "sex_at_birth",
            "city_at_birth",
            "zip_code_at_birth",
            "address_at_birth",
            "state_at_birth",
            "country_at_birth",
        ]

        rows = []
        
        for disease in diseases:
            # Pick a random number of patients
            num_patients = 1 + 10 * np.random.poisson(1)
            
            self.stderr.write(self.style.SUCCESS(f"number of patients: {num_patients}"))

            for _ in range(num_patients):
                
                self.stderr.write(self.style.SUCCESS(f"in loop."))
                rows.append(
                    (
                        faker.uuid4(),
                        disease.do_id,
                        faker.first_name(),
                        faker.last_name(),
                        faker.date_of_birth(),
                        faker.first_name(),
                        np.random.choice(["M", "F"]),
                        faker.city(),
                     #   faker.zipcode(),
                        faker.zipcode()[:5],
                        faker.street_address(),
                        faker.state_abbr(),
                        faker.country_code(representation="alpha-3"),
                    )
                )

            if len(rows) > 100:
                break

        self.stderr.write(self.style.SUCCESS(f"Starting write operation"))


        # Write first 20 rows to one file
        writer = csv.writer(open("patients1.csv", "w"))
        writer.writerow(HEADER)
        writer.writerows(rows[:20])

        # Write next 20 rows to another file
        writer = csv.writer(open("patients2.csv", "w"))
        writer.writerow(HEADER)
        writer.writerows(rows[20:40])
