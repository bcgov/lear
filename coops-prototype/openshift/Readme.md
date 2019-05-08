# OpenShift configuration files

In this folder OR
See https://github.com/BCDevOps/openshift-templates

# OpenShift Configuration/Setup

### in gl2uos-tools namespace:
- create the image stream "coops-ui"
  - oc create imagestream coops-ui-inter
  - oc create imagestream coops-ui
- create the two build configs from the template
  - oc process -f coops-ui-bc.tools.json | oc create -f -

### in gl2uos-dev, gl2uos-test, and gl2uos-prod namespaces each:
- create the service from the template
  - oc process -f coops-ui-service.devtestprod.json | oc create -f -
- create the deployment config from the template
  - oc process -f coops-ui-dc.prod.json | oc create -f -
- create the config maps in the Openshift console (see Namex for examples):
  - web-caddy-config
  - web-keycloak
  - web-ui-configuration
- create the route in the Openshift console for the "coops-ui" service

Note 1: Route needs to be created after service or the port (2015 in this case) won't be available.
Note 2: Apps and selectors are important for connecting deployment, service, and route.
