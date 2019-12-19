# Deploying to Environments

This section contains the deployment configurations for each of the application components along with the scripts used to trigger the deployments.  Its intended to be abstracted from the source. This document also outlines the requirements for parameterization of the deployment configuration templates, and usage of the deployment scripts.

## Overview

The intention here is to be able to create isolated environments with all the required application components to facailitate pull request based pipelines, integration/end-to-end testing, and feature-based environments suitable for quality assurance and business validation.

| Filename(s) | Description |
| ----------- | ----------- |
| `deploy.sh` | A bash wrapper for the groovy-based deployment process. |
| `_*.dc.json` | Deployment config templates for each of the application components. |
| `config.groovy` | The configuration script that defines all the parameters required to issue a deployment. |

The `deploy.sh` script can be called locally, or from a Jenkinsfile, etc. It requires that you pass it the `--pr=` and `--env=` parameters at calltime.  The `env` paramter should represent environment specifications (ie, dev, test, e2e, prod) - and the `pr` parameter - which can be passed as a null parameter when not in a PR based process - references the Pull Request number that it should use to establish its environment.

Note: When using a PR based process, the `env` property should be set to 'dev'.

This deployment process assumes that application-component images are already built, tagged and pushed to the container registry. It expects images to be pushed up with the following guidelines:

- Images are named from the application component, ie `coops-ui` or `legal-api`.
- Images are tagged with their applicable version, ie `pr123` or `dev`.

## Deployment Config Templates

The deployment configuration templates here should contain everything needed to deploy the application components into environments - This should include any services, routes, configration maps, auto-scallers, etc.

## Parameterization Details

All application components require that they have `identification` and `resource` parameters defined for them. Otherwise any other parameters could be unique to each application component.

Parameters defined here should include a reference to where it is used, `Build Configurations (bc)`, `Deployment Configurations (dc)`, `Runtime Environment Variables (env)`, and/or `Secrets`

### Identification Parameters

All application components assume that there are three properties assigned to them for identification of the different stages of development. This should be consistant across all application components, and used in both the build, image-tagging, and deployment configurations.

| Name | Description | BC | DC | ENV | Secret |
| ---- | ----------- | -- | -- | --- | ------ |
| APP_NAME | The (shared) application name - typically bcros |n|y|n|n|
| COMP_NAME | The application component name (repo) |y|y|n|n|
| SUFFIX | The build-suffix used for tagging/promoting images, defined based on the stage of the pipeline  |y|y|n|n|


With this combination of parameters, we can create the following:

| Parameter | Value |
| ---- | ----- |
| APP_NAME | `bcros` |
| COMP_NAME | `coops-ui`, `legal-api`, `postgres`, `entity-filer` |
| SUFFIX | `pr123`, `dev`, `e2e`, `test`, `prod` |


This allows for us to create an application-group of `bcros-SUFFIX`, and within that group a deployment/pod for each of the application components - also tagged with the suffix.

```
bcros-pr123
-> coops-ui:pr123
-> legal-api:pr123
-> entity-filer:pr123
-> postgres:pr123
```

```
bcros-dev
-> coops-ui:dev
-> legal-api:dev
-> entity-filer:dev
-> postgres:dev
```


### Resource Parameters

All application components require that we specify the resources that they expect to have allocated to them in their deployment configurations.  These can be changed for each of the environments in which they are to be deployed.

| Name | Description | BC | DC | ENV | Secret |
| ---- | ----------- | -- | -- | --- | ------ |
| CPU_LIMIT | The max CPU credits to be allocated to the component. (`250m`) |n|y|n|n|
| MEMORY_LIMIT | The max Memory to be allocated to the component.(`1Gi`) |n|y|n|n|
| CPU_REQUEST | The expected CPU required for a container, allocated before being bound to a node. (`100m`) |n|y|n|n|
| MEMORY_REQUEST | The expected Memory required for a container, allocated before being bound to a node. (`750Mi`) |n|y|n|n|
| REPLICA_MIN | The min amount of pods to be running in the deployment |n|y|n|n|
| REPLICA_MAX | The max amount of pods to be running in the deployment |n|y|n|n|

### Build Configration Parameters

Build configuration parameters are used at the time in which the application component is being built. Identification Parameters are always required at build time, but there could be other parameters required too. Any parameter used at build time (with the exception of `SUFFIX`) should not change as the build artifact is promoted through the various environment stages.

__Note:__ While builds are not intended to be done here at this time, they will require that they follow the same application-component naming and suffix-tagging of images as they are pushed to the container registry. If this is not done, and the applicable images cannot be found in the container registry, you will get an error similar the following when deploying:

```
Caught: java.lang.NullPointerException: Cannot get property 'image' on null object
java.lang.NullPointerException: Cannot get property 'image' on null object
```

### Deployment Configuration Parameters

Deployment Configuration Parameters are used at the time in which the application component is being deployed into any environment. Identification Parameters and Resource Parameters are always required as Deployment Configuration Parameters.

Deployment Configuration Parameters are expected to change from environment to environment, and likely are also used as Environment Variable Parameters and/or Secrets that are exported into the resulting containers as they are being deployed.

### Environment Variable Parameters

Environment variable parameters are properties that the source code generally needs to use, and often change from one deployed environment to another. Environment variable parameters are typically (but not limited to) service uri's, credentials, etc. All Environment variable parameters are exported into the containers as they are started up/deployed.

### Enterprise DB

This service uses a persistant database host, with ephemoral database schemas (for ephemoral environments). The hostname, username and password used for connecting are stored in openshift as a secret named '`lear-db--admin`. Deployment configurations should be set to pull these values from the stored secret.

The Legal API component contains a set of scripts for database-creation, migration and seeding, and is triggered through a lifecycle hook at the time of deployment.

## Secrets

Note: With Enterprise DB enabled there is no longer a need for database connection strings to be generated as openshift secrets.

Parameters that contain sensitive information that should be included in the sourcecode are stored as secrets within Openshift at this time. In the future we may offload these into a secret/key management/rotation service - but for now they are required to be manually entered into openshift, and referenced in the templates and source code.

Secrets should still have an openshift template created for them and stored in the repo though, only the actual value of the parameters should be omitted. This would allow for someone to create the secrets in a different namespace/project, or update them in the future with the risk of missing or miss-typing them.

Secret templates require that the properties have their values base64 encoded, this can be done from the command-line:

```
#> echo foobar | base64
#> Zm9vYmFydwo
#> echo Zm9vYmFydwo= | base64 --decode
#> foobar
```
Secret templates should use a format as follows:

```
{
    "kind": "Template",
    "apiVersion": "v1",
    "metadata": {
        "annotations": {
            "description": "Secrets Template.",
            "tags": "super-secret"
        },
        "name": "super-secret-template"
    },
    "objects": [{
        "kind": "Secret",
        "apiVersion": "v1",
        "type": "Opaque",
        "data": {
            "username": "Zm9vYmFyCg==",
            "password": "Zm9vYmFyCg=="
        },
        "metadata": {
            "name": "super-secret-${SUFFIX}",
            "labels": {
                "app": "${APP_NAME}-${SUFFIX}",
                "app-name": "${APP_NAME}-${SUFFIX}",
                "env-name": "${SUFFIX}"
            }
        }
    }],
    "parameters": [
        {
            "name": "APP_NAME",
            "displayName": "APP_NAME",
            "description": "The name of the application (grouped).",
            "required": true,
            "value": "bcros"
        },
        {
            "name": "SUFFIX",
            "description": "The suffix or tagname, typically represented as the environment name.",
            "displayName": "SUFFIX",
            "required": true
        }
    ]
}
```

Once this is loaded into openshift, the secrets could then be referenced by any deployment configuration template using the follow syntax:

```
...
{
    "name": "USERNAME",
    "valueFrom": {
        "secretKeyRef": {
            "name": "super-secret-${SUFFIX}",
            "key": "username"
        }
    }
},
{
    "name": "PASSWORD",
    "valueFrom": {
        "secretKeyRef": {
            "name": "super-secret-${SUFFIX}",
            "key": "password"
        }
    }
}
...
```
## Application Component Details

The following section outlines the paramaterization details and deployment specifics of the various application components used here.

