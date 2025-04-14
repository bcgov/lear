# buildconfig
oc process -f openshift/templates/bc.yaml -o yaml | oc apply -f - -n cc892f-tools
# deploymentconfig, service
oc process -f openshift/templates/dc.yaml -o yaml | oc apply -f - -n cc892f-dev
oc process -f openshift/templates/dc.yaml -p TAG=test -o yaml | oc apply -f - -n cc892f-test
oc process -f openshift/templates/dc.yaml -p TAG=prod -o yaml | oc apply -f - -n cc892f-prod

