**Production Note:**
In production, you must set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account JSON key file for gcloud authentication to work.
**Note:** Locally, the Jupyter notebook uses the default gcloud authentication for database access. Make sure your gcloud credentials are set up and active in your environment.
# Jupyter Notebook Environment Variables

To run the Jupyter notebook only, you must populate the following environment variables in your `.env` file:

```
DATABASE_USERNAME=
DATABASE_NAME=
LEAR_DB_CONNECTION_NAME=
```

# Notebook Report

Generate notebook report

## Development Environment

Follow the instructions of the [Development Readme](https://github.com/bcgov/entity/blob/master/docs/development.md)
to setup your local development environment.


## Running Notebook Report

1. Activate your virtual environment:
   ```sh
   source .venv/bin/activate
   ```
2. Run the notebook pipeline with:
   ```sh
   python sftpnuans.py
   ```
   This will execute `notebook/generate_files.ipynb` using papermill, connect to the database, and generate the output file in the `data/` directory.
