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

### Phase 2: Extending Application Components

- Added 'nats-streaming' application components
- Added 'entity-filer' application components
- Added 'pay-filer' application components
- Added a (temp) postgres-db until cross-project EDB is working
- Added the future-effective-filings cron components

__Status: Completed (Jan 2020)__

- After plugging phase 1 and 2 into the container registry and environments are being created, we will need to address the auth (redirection) issues.

### Phase 3: Plugging into the CI Orchestrator (Jenkins)

__Status: To Do__

