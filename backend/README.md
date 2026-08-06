# PALIND backend

Django app implementing the PALIND backend spec.

You can run the app using Docker or as a development environment.

# How to build and run demo server using Docker

    docker compose up

    

Then, open a browser and visit [http://localhost:8000/dataset/1/upload-csv](http://localhost:8000/dataset/1/upload-csv)

## Run DB Migrations

Run this command if this is the first time starting a container (OR) you have changed any data models:

python manage.py migrate

Then, visit:
- Application: http://localhost:8000
- Admin interface: http://localhost:8000/admin
- Upload CSV: http://localhost:8000/dataset/1/upload-csv

## Setup Admin username & password (One Time Setup)
Use this to setup a new username & password for Admin console

    docker compose exec web python manage.py createsuperuser

## Admin site

Visit http://localhost:8000/admin with user `admin` and password `1234`.

# Run the app for development

First, create a virtual environment:

    python3 -m venv venv             # Create virtual environment
    . ./venv/bin/activate            # Activate it for this shell
    pip install -r requirements.txt  # Install requirements

Second, create a superuser who will be able to access the admin site:

    python manage.py createsuperuser

Initialize the database by running the migrations:

    python manage.py migrate

Now, you can run the local development server with:

    python manage.py runserver


Visit [localhost:8000](http://localhost:8000) to access the site and
[localhost:8000/admin](http://localhost:8000/admin) to access the admin site.

## How to create a random dataset

Execute command to create two CSV files that you can upload 

    docker compose exec web python manage.py create_random_dataset




## Install and run Terraform on AWS CloudShell

    git clone https://github.com/tfutils/tfenv.git ~/.tfenv
    mkdir ~/bin
    ln -s ~/.tfenv/bin/* ~/bin/
    tfenv install 1.7.0
    tfenv use 1.7.0
    terraform --version

    # Copy main.tf

    terraform init

    terraform plan
    terraform apply

## How to initialize DB

1. Make RDS database publicly accessible
2. Modify the default VPC security group to allow inbound traffic from your IP address to the postgres port (5432)
3. Export the following variables:
```
export DJANGO_DB_PORT=5432
export DJANGO_DB_HOST=XXX.us-east-1.rds.amazonaws.com # The RDS endpoint
export DJANGO_DB_USER_PASSWORD='{"username": "postgres", "password": "XXX"}'  # The RDS master password from the Secrets Manager
```
4. Run `./manage.py runserver` and visit [localhost:8000](http://localhost:8000) to check that the connection is done correctly. You should not be able to log in because there is no user yet.
5. Run `./manage.py createsuperuser` and create a superuser to access the admin site.
6. Visit [localhost:8000/admin](http://localhost:8000/admin) and log in with the superuser credentials.
7. Create an organization and add the superuser to it.
8. Fill in the name and last name of the superuser.
9. Visit [app.palind.io/admin](https://app.palind.io/admin) and log in with the superuser credentials to check that you have access to the production site.
10. Download the `HumanDO.json` from [GitHub](https://github.com/DiseaseOntology/HumanDiseaseOntology/tree/main/src/ontology).
11. Run `./manage.py import_diseases HumanDO.json` to fill the database with the diseases.
12. Remove Inbound rule from the VPC > Security Group.
13. Make RDS database not publicly accessible.

## SQLite to PostgreSQL data migration

Use this workflow to migrate existing data from SQLite into a new PostgreSQL database.

1. Export data from SQLite:

    python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 4 > datadump-YYYY-MM-DD.json

2. Update Django database settings to point to PostgreSQL.
3. Create the PostgreSQL database (if needed), then run migrations:

    python manage.py migrate

4. Import the fixture into PostgreSQL:

    python manage.py loaddata -v 2 datadump-YYYY-MM-DD.json

### Verification script (copy/paste)

Run this from the `backend` directory after updating database settings:

```bash
set -euo pipefail

FIXTURE_FILE="datadump-YYYY-MM-DD.json"

echo "Checking Django configuration and DB connectivity..."
python manage.py check --database default

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Loading fixture: ${FIXTURE_FILE}"
python manage.py loaddata -v 2 "${FIXTURE_FILE}"

echo "Sanity check: users and datasets"
python manage.py shell -c "from django.contrib.auth import get_user_model; from datasets.models import Dataset; print(f'Users: {get_user_model().objects.count()} | Datasets: {Dataset.objects.count()}')"

echo "Migration verification completed successfully."
```

### Important fixture-loading caveat

If a `post_save` signal dereferences related objects during fixture loading, `loaddata` can fail because objects may be saved in an order where relations are not yet resolvable. In this project, the `CustomUser` default dataset signal must:

- Return immediately when `raw=True`.
- Check `instance.default_dataset_id is None` rather than `instance.default_dataset is None`.

This prevents `Dataset.DoesNotExist` errors during fixture import.

### Troubleshooting

1. `connection to server ... failed: Operation not permitted`

- Cause: network path to PostgreSQL is blocked.
- Check: DB host/port are correct in Django settings or env vars.
- Check: for RDS, inbound rule allows your current IP on port `5432`.
- Check: local firewall/VPN is not blocking outbound access.

2. `password authentication failed for user ...`

- Cause: wrong username/password.
- Check: `DJANGO_DB_USER_PASSWORD` secret JSON has the expected username and password.
- Re-test with the same credentials using `psql`.

3. `database "..." does not exist`

- Cause: target DB not created yet.
- Fix: create the database, then run `python manage.py migrate` before `loaddata`.

4. `Dataset.DoesNotExist` (or similar relation errors) during `loaddata`

- Cause: signal logic dereferences relations while fixtures are loading.
- Fix: guard `post_save` handlers with `if kwargs.get("raw", False): return`.
- Fix: prefer checking `*_id` fields (for example `default_dataset_id`) over relation objects during signal checks.

5. Fixtures partially imported on a failed run

- Cause: interrupted or failing import attempt.
- Fix: reset target database state (drop/recreate DB, or truncate tables), rerun `migrate`, then rerun `loaddata` once.
