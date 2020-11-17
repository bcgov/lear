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
2. Run notebook with `(python notebookreport.py)`

## Running Unit Tests

1. Run `python -m pytest` or `pytest` command.

### Build API - can be done in VS Code

1. Login to openshift

   ```sh
   oc login xxxxxxx
   ```

2. switch to tools namespace

   ```sh
   oc project gl2uos-tools
   ```

3. Create build image

   ```sh
   cd */lear/jobs/filings-notebook-report/openshift/templates
   oc create imagestream filings-notebook-report
   oc process -f filings-notebook-report-bc-template.json \
        -p GIT_REPO_URL=https://github.com/bcgov/lear.git \
    | oc apply -f -
   ```

4. Create runtime image

   ```sh
   oc create imagestream filings-notebook-report-runtime
   oc process -f filings-notebook-report-runtime-bc-template.json \
    | oc apply -f -
   ```
  
5. Create pipeline and need to start pipeline manually

   ```sh
   oc process -f filings-notebook-report-pipeline.json \
        -p TAG_NAME=dev \
        -p GIT_REPO_URL=https://github.com/bcgov/lear.git \
        -p WEBHOOK=github-filings-notebook-report-dev \
        -p JENKINS_FILE=./jenkins/dev.groovy \
    | oc apply -f -
   ```

### Create cron

1. Login to openshift

   ```sh
   oc login xxxxxxx
   ```

2. switch to dev namespace

   ```sh
   oc project gl2uos-dev
   ```

3. Create cron

   ```sh
   oc process -f cron-notebook-report.yml \
        -p ENV_TAG=dev \
    | oc apply -f -
   ```
