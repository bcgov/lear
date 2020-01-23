#!/usr/bin/env bash
set -e

# Cleans the tmp dir and forces a reload of the java/groovy/pipeline libs
clean_tmp() {
  echo "Cleaning /tmp"
  rm -Rf /tmp/~jdk-*
  rm -Rf /tmp/.groovy
  rm -Rf /tmp/ocp-pipeline
}

# General Usage Output
print_usage() {
  printf "\n[Environment Builder Cleanup.]\n"
  printf "\n Usage: "
  printf "\n -h Show this message and exit "
  printf "\n -t Remove the java/groovy/pipeline scripts from the /tmp directory to force a reload then exit"
  printf "\n -e [ENVIRONMENT] Set the environment suffix. "
  printf "\n -e [NAMESPACE] Set the openshift namespace/project. \n\n"
}

# Default Options
CLEAN_ENV='dev'
CLEAN_NS='zcd4ou-dev'

while getopts 'hte:n:' flag; do
  case "${flag}" in
    e) echo "Using Environment: ${OPTARG}"
       CLEAN_ENV="${OPTARG}" ;;
    n) echo "Using Namespace: ${OPTARG}"
       CLEAN_NS="${OPTARG}" ;;
    t) clean_tmp
       exit 1 ;;
    h) print_usage
       exit 1 ;;
  esac
done

COMPLIST=(
    'legal-api'
    'coops-ui'
    'entity-filer'
    'entity-pay'
    'nats-streaming'
    )

echo "-=-=- Removing OS Objects ... "

for i in "${COMPLIST[@]}"; do
  echo "Removing ${i}..."
  oc delete deploymentconfigs/${i}-${CLEAN_ENV}  -n ${CLEAN_NS} --ignore-not-found ;
  oc delete services/${i}-${CLEAN_ENV} -n ${CLEAN_NS} --ignore-not-found ;
  oc delete route/${i}-${CLEAN_ENV} -n ${CLEAN_NS} --ignore-not-found ;
  oc delete configmaps/${i}-${CLEAN_ENV} -n ${CLEAN_NS} --ignore-not-found ;
  oc delete secrets/${i}-${CLEAN_ENV} -n ${CLEAN_NS} --ignore-not-found ;
  oc delete jobs/${i}-${CLEAN_ENV} -n ${CLEAN_NS} --ignore-not-found ;
  oc delete horizontalpodautoscaler/${i}-${CLEAN_ENV} -n ${CLEAN_NS} --ignore-not-found ;
done

echo "Done!"
