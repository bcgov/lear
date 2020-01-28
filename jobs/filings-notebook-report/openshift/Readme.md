# OpenShift configuration files

* deployment config .  (Example: https://github.com/bcgov/angular-scaffold/blob/master/openshift/templates/angular-on-nginx/angular-on-nginx-deploy.json)
* build config (Example: https://github.com/bcgov/angular-scaffold/blob/master/openshift/templates/angular-on-nginx/angular-on-nginx-build.json)

# Using Shell cripts to setup your environment
Checkout: https://github.com/BCDevOps/openshift-project-tools.git
Add following to your PATH: 
* openshift-project-tools/bin



# How to configure a CI/CD pipeline for the <project-name> on OpenShift

- Create a project to house the Jenkins instance that will be responsible for promoting application images (via OpenShift ImageStreamTags) across environment; the exact project name used was "{project-name}-tools".
- Create the BuildConfiguration within this project using the ```oc``` command and "{project-name}-build.json" file:

```
oc process -f {project-name}-build.json | oc create -f -
```

This build config is in the openshift namespace as it uses the {base-image-name} S2I strategy.


- Deploy a Jenkins instance with persistent storage into the tools project ({project-name}-tools) using the web gui
- Create an OpenShift project for each "environment" (e.g. DEV, TEST, PROD); 
  Exact names used were {project-name}-dev, {project-name}-test, {project-name}-prod
- Configure the access controls to allow the Jenkins instance to tag imagestreams in the environment projects, and to allow the environment projects to pull images from the tools project:
 
```
oc policy add-role-to-user system:image-puller system:serviceaccount:{project-name}-dev:default -n {project-name}-tools
oc policy add-role-to-user edit system:serviceaccount:{project-name}-tools:default -n {project-name}-dev

oc policy add-role-to-user system:image-puller system:serviceaccount:{project-name}-test:default -n {project-name}-tools
oc policy add-role-to-user edit system:serviceaccount:{project-name}-tools:default -n {project-name}-test

oc policy add-role-to-user system:image-puller system:serviceaccount:{project-name}-prod:default -n {project-name}-tools
oc policy add-role-to-user edit system:serviceaccount:{project-name}-tools:default -n {project-name}-prod
```

https://console.pathfinder.gov.bc.ca:8443/console/project/<project-name>-tools/browse/builds/<build-name>?tab=configuration
displays the webhook urls. Copy the GitHub one. 
https://console.pathfinder.gov.bc.ca:8443/oapi/v1/namespaces/{project-name}-tools/buildconfigs/devxp/webhooks/github

In the GitHub repository go to Settings > Webhooks > Add webhook
Create a webhook for the push event only to Payload URL copied from URL above.
Content type: application/json

Create the deploy configuration
 - Use the JSON file in this directory  and `oc` tool to create the necessary app resources within each project (user and password can be found in the postgresql deployment environment variables in the web gui):

```
oc process -f <project-name>-environment.json -v DATABASE_USER=<user> -v DATABASE_PASSWORD=<password> -v APP_DEPLOYMENT_TAG=<tag> -v APPLICATION_DOMAIN=<appname>-<env>.pathfinder.gov.bc.ca | oc create -f -
```

Where APP_DEPLOYMENT_TAG used is dev, test, prod.
The deployment config uses the <project-name>-tools namespace since that is where the image stream resides.


# How to access Jenkins

- Login to https://jenkins-{project-name}-tools.pathfinder.gov.bc.ca.

# How to access OpenShift

## Web UI
- Login to https://console.pathfinder.gov.bc.ca:8443; you'll be prompted for GitHub authorization.

## Command-line (```oc```) tools
- Download OpenShift [command line tools](https://github.com/openshift/origin/releases/download/v1.2.1/openshift-origin-client-tools-v1.2.1-5e723f6-mac.zip), unzip, and add ```oc``` to your PATH.  
- Copy command line login string from https://console.pathfinder.gov.bc.ca:8443/console/command-line.  It will look like ```oc login https://console.pathfinder.gov.bc.ca:8443 --token=xtyz123xtyz123xtyz123xtyz123```
- Paste the login string into a terminal session.  You are now authenticated against OpenShift and will be able to execute ```oc``` commands. ```oc -h``` provides a summary of available commands.



# Background reading/Resources

[Pathfiner Site](https://www.pathfinder.gov.bc.ca/)

[Free OpenShift book](https://www.openshift.com/promotions/for-developers.html) from RedHat – good overview

[Red Hat Container Development Kit](http://developers.redhat.com/products/cdk/overview/)

# OpenShift CI/CD pieline Demos:

- https://www.youtube.com/watch?v=65BnTLcDAJI
- https://www.youtube.com/watch?v=wSFyg6Etwx8

# OpenShift Configuration/Setup

* https://docs.openshift.com/container-platform/3.6/dev_guide/application_lifecycle/new_app.html#dev-guide-new-app
* https://docs.openshift.com/container-platform/3.6/dev_guide/builds/index.html
* https://docs.openshift.com/container-platform/3.6/dev_guide/templates.html#writing-templates
* https://github.com/BCDevOps/BCDevOps-Guide


  
