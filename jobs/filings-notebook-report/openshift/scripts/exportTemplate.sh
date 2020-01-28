#!/bin/bash
SCRIPT_DIR=$(dirname $0)

# =====================================================================
# Author: Wade Barnes
# =====================================================================

# ===================================================================================================
# Funtions
# ---------------------------------------------------------------------------------------------------
usage (){
  echo "========================================================================================"
  echo "Export an OpenShift resource as a template."
  echo
  echo "----------------------------------------------------------------------------------------"
  echo "Usage:"
  echo
  echo "${0} <resource_list> <resource_name> <template_name> [output_format] [output_path]"
  echo
  echo "Where:"
  echo " - <resource_list> csv list of resources to export."
  echo " - <resource_name> The name of the resource to export."
  echo " - <template_name> The name to assign to the template."
  echo " - [output_format] Optional: Output file format; json (default) or yaml."
  echo " - [output_path] Optiona: Output path."
  echo
  echo "Examples:"
  echo "${0} bc solr solr-template"
  echo "========================================================================================"
  exit 1
}

exitOnError (){
  rtnCd=$?
  if [ ${rtnCd} -ne 0 ]; then
	echo "An error has occurred.!  Please check the previous output message(s) for details."
    exit ${rtnCd}
  fi
}
# ===================================================================================================

# ===================================================================================================
# Setup
# ---------------------------------------------------------------------------------------------------
if [ -z "${1}" ]; then
  usage  
elif [ -z "${2}" ]; then
  usage  
elif [ -z "${3}" ]; then
  usage
else
  RESOURCE_LIST=$1
  RESOURCE_NAME=$2
  TEMPLATE_NAME=$3
fi

if [ ! -z "${4}" ]; then
  OUTPUT_FORMAT=$4  
fi

if [ ! -z "${5}" ]; then
  OUTPUT_PATH=$5
fi

if [ ! -z "${6}" ]; then
  usage
fi

if [ -z "$OUTPUT_FORMAT" ]; then
	OUTPUT_FORMAT=json
fi

if [ -z "$OUTPUT_PATH" ]; then
	OUTPUT_PATH="${SCRIPT_DIR}/${TEMPLATE_NAME}.${OUTPUT_FORMAT}"
fi
# ===================================================================================================

oc export ${RESOURCE_LIST} ${RESOURCE_NAME} --as-template=${TEMPLATE_NAME} -o ${OUTPUT_FORMAT} > ${OUTPUT_PATH}
