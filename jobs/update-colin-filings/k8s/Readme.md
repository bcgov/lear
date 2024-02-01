

# buildconfig
oc process -f openshift/templates/bc.yaml -o yaml | oc apply -f - -n cc892f-tools
# cronjob
oc process -f openshift/templates/cronjob.yaml -o yaml | oc apply -f - -n cc892f-dev
oc process -f openshift/templates/cronjob.yaml -p TAG=test -o yaml | oc apply -f - -n cc892f-test
oc process -f openshift/templates/cronjob.yaml -p TAG=prod -o yaml | oc apply -f - -n cc892f-prod
# manually run job
oc create job --from=cronjob/<cronjob-name> <job-name> -n cc892f-prod
