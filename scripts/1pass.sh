#!/bin/bash


# =================================================================================================================
# Usage:
# -----------------------------------------------------------------------------------------------------------------
usage() {
  cat <<-EOF
  A helper script to get the secrcts from 1password' vault.
  Usage: ./1pass.sh [-h -d <subdomainName> -u <accountName>]
                      -k <secretKey>
                      -p <masterPassword>
                      -m <method>
                      -e <environment(s)>
                      -v <vaultDetails>
                      -a <appName>
                      -n <namespace>

  OPTIONS:
  ========
    -h prints the usage for the script.
    -d The subdomain name of the 1password account, default is registries.1password.ca.
    -u The account name of the 1password account, default is bcregistries.devops@gmail.com.
    -k The secret key of the 1password account.
    -p The master password of the 1password account.
    -m The methodof using the vaults.
        secret - set vault values to Openshift secrets
        env - set vault values to github action environment
        compare - compare two environments vault values
    -e The environment(s) of the vault, for example pytest/dev/test/prod or "dev test".
    -a Openshift application name, for example: auth-api-dev
    -n Openshift namespace name, for example: 1rdehl-dev
    -v A list of vault and application name of the 1password account, for example:
       [
          {
              "vault": "shared",
              "application": [
                  "keycloak",
                  "email"
              ]
          },
          {
              "vault": "relationship",
              "application": [
                  "auth-api",
                  "notify-api",
                  "status-api"
              ]
          }
      ]

EOF
exit
}

# -----------------------------------------------------------------------------------------------------------------
# Initialization:
# -----------------------------------------------------------------------------------------------------------------
while getopts h:a:d:u:k:p:v:m:e:n: FLAG; do
  case $FLAG in
    h ) usage ;;
    a ) APP_NAME=$OPTARG ;;
    d ) DOMAIN_NAME=$OPTARG ;;
    u ) USERNAME=$OPTARG ;;
    k ) SECRET_KEY=$OPTARG ;;
    p ) MASTER_PASSWORD=$OPTARG ;;
    v ) VAULT=$OPTARG ;;
    m ) METHOD=$OPTARG ;;
    e ) ENVIRONMENT=$OPTARG ;;
    n ) NAMESPACE=$OPTARG ;;
    \? ) #unrecognized option - show help
      echo -e \\n"Invalid script option: -${OPTARG}"\\n
      usage
      ;;
  esac
done

# Shift the parameters in case there any more to be used
shift $((OPTIND-1))
# echo Remaining arguments: $@

if [ -z "${DOMAIN_NAME}" ]; then
  DOMAIN_NAME=registries.1password.ca
fi

if [ -z "${USERNAME}" ]; then
  USERNAME=bcregistries.devops@gmail.com
fi

if [ -z "${SECRET_KEY}" ] || [ -z "${MASTER_PASSWORD}" ]; then
  echo -e \\n"Missing parameters - secret key or master password"\\n
  usage
fi

if [ -z "${ENVIRONMENT}" ]; then
  echo -e \\n"Missing parameters - environment"\\n
  usage
fi

if [ -z "${VAULT}" ]; then
  echo -e \\n"Missing parameters - vault"\\n
  usage
fi

methods=(secret env compare)
if [[ ! " ${methods[@]} " =~ " ${METHOD} " ]]; then
  echo -e \\n"Method must be contain one of the following method: secret, env or compare."\\n
  usage
fi

envs=(${ENVIRONMENT})
if [[ " compare " =~ " ${METHOD} " ]]; then
  if [[ ${#envs[@]} != 2 ]]; then
    echo -e \\n"Environments must be contain two values ('dev test' or 'test prod')."\\n
    exit
  fi
fi

if [[ " secret " =~ " ${METHOD} " ]]; then
  if [[ -z "${APP_NAME}" ]]; then
    echo -e \\n"Missing parameters - application name"\\n
    usage
  else
    if [[ -z "${NAMESPACE}" ]]; then
      echo -e \\n"Missing parameters - namespace"\\n
      usage
    fi
  fi
fi


# Login to 1Password../s
# Assumes you have installed the OP CLI and performed the initial configuration
# For more details see https://support.1password.com/command-line-getting-started/
eval $(echo "${MASTER_PASSWORD}" | op signin ${DOMAIN_NAME} ${USERNAME} ${SECRET_KEY})

if [[ " secret " =~ " ${METHOD} " ]]; then
  # create application secrets
  oc create secret generic ${APP_NAME}-secret -n ${NAMESPACE} > /dev/null 2>&1 &
fi

num=0
for env_name in "${envs[@]}"; do

  num=$((num+1))
  for vault_name in $(echo "${VAULT}" | jq -r '.[] | @base64' ); do
    _jq() {
      echo ${vault_name} | base64 --decode | jq -r ${1}
    }
    for application_name in $(echo "$(_jq '.application')" | jq -r '.[]| @base64' ); do
      _jq_app() {
        echo ${application_name} | base64 --decode
      }
      app_name=$(echo ${application_name} | base64 --decode)
      # My setup uses a 1Password type of 'Password' and stores all records within a
      # single section. The label is the key, and the value is the value.
      ev=`op get item --vault=$(_jq .vault) ${env_name}`

      # Convert to base64 for multi-line secrets.
      # The schema for the 1Password type uses t as the label, and v as the value.
      # Set secrets to secret in Openshift
      for row in $(echo ${ev} | jq -r -c '.details.sections[] | select(.title=='\"$(_jq_app)\"') | .fields[] | @base64'); do
          _envvars() {
              echo ${row} | base64 --decode | jq -r ${1}
          }

          case  ${METHOD}  in
            secret)
              secret_json=$(oc create secret generic ${APP_NAME}-secret --from-literal="$(_envvars '.t')=$(_envvars '.v')" --dry-run=client -o json)

              # Set secret key and value from 1password
              oc get secret ${APP_NAME}-secret -n ${NAMESPACE} -o json \
                | jq ". * $secret_json" \
                | oc apply -f -
              ;;
            env)
              echo "Setting environment variable $(_envvars '.t')"
              echo ::add-mask::$(_envvars '.v')
              echo ::echo "$(_envvars '.t')=$(_envvars '.v')" >> $GITHUB_ENV
              ;;
            compare)
              #read the vault's key to a txt file

              echo "${app_name}: $(_envvars '.t')" >> t$num.txt
              ;;
          esac
      done
    done
  done
done

case  ${METHOD}  in
  secret)
    # Set environment variable of deployment config
    oc set env dc/${APP_NAME} -n ${NAMESPACE} --overwrite --from=secret/${APP_NAME}-secret --containers=${APP_NAME} ENV-  > /dev/null 2>&1 &
    ;;
  compare)
    # Compare txt file and write the result into github actions environment
    result=$(comm -23 <(sort t1.txt) <(sort t2.txt))
    result2=$(comm -23 <(sort t2.txt) <(sort t1.txt))
    if [[ -z ${result} ]]; then
      if [[ -z ${result2} ]]; then
        echo ::echo "approval=true" >> $GITHUB_ENV
        echo ::echo "message=The vault items between ${envs[0]} and ${envs[1]}  are matched." >> $GITHUB_ENV
      else
        echo ::echo "approval=false" >> $GITHUB_ENV
        echo ::echo "message=The following vault items between ${envs[1]} and ${envs[0]} does not match. ${result2}" >> $GITHUB_ENV
      fi
    else
      echo ::echo "approval=false" >> $GITHUB_ENV
      echo ::echo "message=The following vault items between ${envs[0]} and ${envs[1]} does not match. ${result}"  >> $GITHUB_ENV
    fi

    rm t*.txt
    ;;
esac




