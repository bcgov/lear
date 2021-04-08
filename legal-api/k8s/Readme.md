
# buildconfig
oc process -f openshift/templates/bc.yaml -o yaml | oc apply -f - -n cc892f-tools
# deploymentconfig, service and route
oc process -f openshift/templates/dc.yaml -o yaml | oc apply -f - -n cc892f-dev
oc process -f openshift/templates/dc.yaml -p TAG=test -p APPLICATION_DOMAIN=legal-api-test.apps.silver.devops.gov.bc.ca -o yaml | oc apply -f - -n cc892f-test
oc process -f openshift/templates/dc.yaml -p TAG=prod -p APPLICATION_DOMAIN=legal-api.apps.silver.devops.gov.bc.ca -o yaml | oc apply -f - -n cc892f-prod

