# BCROS - DevOps

## Jenkins

This directory contains the Jenkins build and deployment configurations, as with the Jenkins plugin and job settings required to run continuous integration and delivery.

## Openshift

This directory contains the application component templates, along with the parameter configuration scripts used to produce environments.

## Development Process

There will be a few iterations of development/improvements required here to have this project updated into the new 'ops-model'. This section is intented to outline the progress, and future development required to get there.

### Phase 1: Initial Environment Setup Scripts

__Status: Completed (Dec 2019)__

- Assuming that application-component images are properly built, tagged and pushed to the container registry - establish deployment configuration templates, their parameters, and a script suitable for deploying said components into issolated environments suitable for integration testing, and quality assurance.
- Can use `deploy.sh` and `config.groovy` to create an environment loaded with the application components.
- Noting that there will be some changes required the auth service to enable fully isolated environments, but this is released as a MVP for progression into the next steps.

### Phase 2: Ensuring Environments are Testable

- Hook into Enterprise DB:  Removed the postgres containers from the deployment process, and enable the EDB connection. This enables the `legal-api` to build new database-schemas on a persitant host at the time of deployment.

__Status: To Do__

- After plugging phase 1 into the container registry and environments are being created, there will be a need to ensure that its properly setting up the database, and that it can be accessed via postman/nightwatch to hook up the e2e/integration testing scripts.

### Phase 3: Plugging into the CI Orchestrator (Jenkins)

__Status: To Do__

- Once the ability to create environments manually is done, and its possible to tested/seeded from our external tools, it should be hooked into the CI Orchestrator

