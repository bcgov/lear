# Notebook Report

Generate notebook report

## Development Environment

Follow the instructions of the [Development Readme](https://github.com/bcgov/entity/blob/master/docs/development.md)
to setup your local development environment.

## Development Setup

1. Follow the [instructions](https://github.com/bcgov/entity/blob/master/docs/setup-forking-workflow.md) to checkout the project from GitHub.
2. Open the notebook-report directory in VS Code to treat it as a project (or WSL projec). To prevent version clashes, set up a virtual environment to install the Python packages used by this project.
3. Run `make setup` to set up the virtual environment and install libraries.
4. The following command will generate a pair of private key and public key. The private key will be kept on the calling side and the public key will be kept on the called side (sftp host side) - from command line
   > ssh-keygen -t rsa -b 2048 -C 'BCRegistries'
5. The following command will print a public key which will be used on the calling side (i.e openshift) - from command line
   > ssh-keyscan server.gov.bc.ca(target server domain or IP)   such as 'C:\>ssh-keyscan bcsc01.gov.bc.ca'

   this will print the public key. Store the string after ssh-rsa to the SFTP_HOST_KEY configurations on openshift.

## Running Notebook Report

1. Open project in VS Code and Ubuntu environment.
2. Create pyproject.toml file on project 
3. poetry config virtualenvs.in-project true
4. for first time: brew install python@3.10
5. for first time: brew info python@3.10
6. Create .venv: poetry env use /home/linuxbrew/.linuxbrew/bin/python3.10
7. Change to .venv environment by:  poetry shell
8. Install required dependencies: poetry install
9. Run project: 'poetry run python sftpnuans.py' or 'poetry run ./run.sh' or './run.sh' (Important: Please remember to do "git update-index --add --chmod=+x run.sh" before run.sh is commit to github on first time.)

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
4. Checking log for building process at Console => Administrator => Builds => Builds => click image 'sftp-nuans-report' => logs

5. Tag image to dev: 'oc tag sftp-nuans-report:latest sftp-nuans-report:dev'


### Create cron

1. Login to openshift

   ```sh
   oc login xxxxxxx
   ```

2. switch to dev namespace

   ```sh
   oc project cc892f-dev
   ```

3. Create cron - to run at 0:55 * * TUE-SAT at pacific time so it will be 7:55 at UTC

   ```sh
   oc process -f openshift/templates/cronjob.yaml \
  -p TAG=dev \
  -p SCHEDULE="55 7 * * TUE-SAT" \
  -o yaml \
  | oc apply -f - -n cc892f-dev
  ```

4. Create a job to run and test it: 'oc create job sftp-nuans-report-dev-1 --from=cronjob/sftp-nuans-report-dev -n cc892f-dev'
