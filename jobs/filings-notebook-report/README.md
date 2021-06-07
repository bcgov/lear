# Notebook Report

Generate notebook report

## Development Environment

Follow the instructions of the [Development Readme](https://github.com/bcgov/entity/blob/master/docs/development.md)
to setup your local development environment.

## Development Setup

1. Follow the [instructions](https://github.com/bcgov/entity/blob/master/docs/setup-forking-workflow.md) to checkout the project from GitHub.
2. Open the notebook-report directory in VS Code to treat it as a project (or WSL projec). To prevent version clashes, set up a virtual environment to install the Python packages used by this project.
3. Run `make setup` to set up the virtual environment and install libraries.

## Running Notebook Report

1. Run `. venv/bin/activate` to change to `venv` environment.
2. Run notebook with `python notebookreport.py`

## Running Unit Tests

1. Run `python -m pytest` or `pytest` command.

### Build API - can be done in VS Code

1. Login to openshift

   ```sh
   oc login xxxxxxx
   ```

2. switch to tools namespace

   ```sh
   oc project cc892f-tools
   ```

3. Create build image with a tag 'latest'.

   ```sh   
   oc process -f openshift/templates/bc.yaml \
   -p GIT_REPO_URL=https://github.com/bcgov/lear.git \
   -p GIT_REF=main \
   -o yaml \
   | oc apply -f - -n cc892f-tools  
   ```
4. Checking log for building process at Console => Administrator => Builds => Builds => click image 'filings-notebook-report' => logs

5. Tag image to dev: 'oc tag filings-notebook-report:latest filings-notebook-report:dev'


### Create cron

1. Login to openshift

   ```sh
   oc login xxxxxxx
   ```

2. switch to dev namespace

   ```sh
   oc project cc892f-dev
   ```

3. Create cron

   ```sh
   oc process -f openshift/templates/cronjob.yaml \
  -p TAG=dev \
  -p SCHEDULE="30 14 * * *" \
  -o yaml \
  | oc apply -f - -n cc892f-dev
  ```

4. Create a job to run and test it: 'oc create job filings-notebook-report-dev-1 --from=cronjob/filings-notebook-report-dev -n cc892f-dev'
