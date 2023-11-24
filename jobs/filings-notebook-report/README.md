# Notebook Report

Generate notebook report

## Development Environment

Follow the instructions of the [Development Readme](https://github.com/bcgov/entity/blob/master/docs/development.md)
to setup your local development environment.

## Development Setup

1. Follow the [instructions](https://github.com/bcgov/entity/blob/master/docs/setup-forking-workflow.md) to checkout the project from GitHub.
2. Open the notebook-report directory in VS Code to treat it as a project (or WSL projec). 
3. Follow up document to create environment: https://community.inkdrop.app/note/a27b7a79c8cdf7db0ab19be10b4fc2e8/note:gxJT0Yj7D#user-content-setting-up-postgres-container

## Running Notebook Report (refer to doc: https://community.inkdrop.app/note/a27b7a79c8cdf7db0ab19be10b4fc2e8/note:gxJT0Yj7D)

1. Open project in VS Code and Ubuntu environment.
2. Create pyproject.toml file on project 
3. poetry config virtualenvs.in-project true
4. for first time: brew install python@3.10
5. for first time: brew info python@3.10
6. Create .venv: poetry env use /home/linuxbrew/.linuxbrew/bin/python3.10
7. Change to .venv environment by:  poetry shell
8. Install required dependencies: poetry install
9. Run project: 'poetry run python notebookreport.py' or 'poetry run ./run.sh' or './run.sh' (Important: Please remember to do "git update-index --add --chmod=+x run.sh" before run.sh is commit to github on first time.)



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
