#!/usr/bin/env groovy
// Copyright © 2018 Province of British Columbia
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//JENKINS DEPLOY ENVIRONMENT VARIABLES:
// - JENKINS_JAVA_OVERRIDES  -Dhudson.model.DirectoryBrowserSupport.CSP= -Duser.timezone=America/Vancouver
//   -> user.timezone : set the local timezone so logfiles report correxct time
//   -> hudson.model.DirectoryBrowserSupport.CSP : removes restrictions on CSS file load, thus html pages of test reports are displayed pretty
//   See: https://docs.openshift.com/container-platform/3.9/using_images/other_images/jenkins.html for a complete list of JENKINS env vars

// define constants
// openshift env
def NAMESPACE = 'd7eovc'
def TAG_NAME = 'tools'

// components TODO: add in auth/pay/queue/jobs
def COMPONENT_TAG = 'e2e'
def LEGAL_API = 'legal-api'
def COLIN_API = 'colin-api'
def COOPS_UI = 'coops-ui'
def ORACLE = 'oracle'
def POSTGRESQL = 'postgresql'

// set in setup stage (will be set to current values for running pods) TODO: username/name for auth/pay dbs
def LEGAL_DB_USERNAME
def LEGAL_DB_NAME
def PG_POD
def DEPLOYMENTS

// old version of deployments
def OLD_VERSIONS

// stays true if all tests pass
def PASSED = true

// define groovy functions
import groovy.json.JsonOutput

def scale_up(NAMESPACE, TAG_NAME, COMPONENT_TAG, deployment) {
    script {
        openshift.withCluster() {
            openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                deploy = openshift.selector("dc", "${deployment}-${COMPONENT_TAG}")
                echo "Scaling up ${deployment}-${COMPONENT_TAG}"
                deploy.scale('--replicas=1')
            }
        }
    }
    return ""
}

def scale_down(NAMESPACE, TAG_NAME, COMPONENT_TAG, deployment) {
    script {
        openshift.withCluster() {
            openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                deploy = openshift.selector("dc", "${deployment}-${COMPONENT_TAG}")
                echo "Scaling down ${deployment}-${COMPONENT_TAG}"
                deploy.scale('--replicas=0')
            }
        }
    }
    return ""
}

def verify_new_deployments(NAMESPACE, TAG_NAME, COMPONENT_TAG, OLD_VERSIONS, components) {
    script {
        openshift.withCluster() {
            openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                for (component in components) {
                    echo "Verifying ${component} has a pod up and running"
                    def new_version = openshift.selector('dc', "${component}-${COMPONENT_TAG}").object().status.latestVersion
                    if ("${component}-${new_version}" in OLD_VERSIONS) {
                        echo "New deployment was not triggered."
                        echo "New: ${component}-${new_version}"
                        echo "Old versions: ${OLD_VERSIONS}"
                        currentBuild.result = "FAILURE"
                    }
                    def pod_selector = openshift.selector('pod', [ deployment:"${component}-${COMPONENT_TAG}-${new_version}" ])
                    pod_selector.untilEach {
                        def latest = it.objects().size()
                        if (!latest) {
                            return false
                        }
                        latest--
                        deployment = it.objects()[latest].metadata.labels.deployment
                        echo "Checking pod: ${deployment}"
                        if (deployment ==  "${component}-${COMPONENT_TAG}-${new_version}" && it.objects()[latest].status.phase == 'Running' && it.objects()[latest].status.containerStatuses[0].ready) {
                            return true
                        } else {
                            echo "${component}-${COMPONENT_TAG} pod not ready"
                            sleep 5
                            return false
                        }
                    }
                }
            }
        }
    }
    return ""
}

node {
    stage('Setup E2E Environment') {
        script {
            echo """
            Pipeline called with constants:
                - NAMESPACE: ${NAMESPACE}
                - TAG_NAME: ${TAG_NAME}
                - COMPONENT_TAG: ${COMPONENT_TAG}
                - LEGAL_API: ${LEGAL_API}
                - COLIN_API: ${COLIN_API}
                - COOPS_UI: ${COOPS_UI}
                - ORACLE: ${ORACLE}
                - POSTGRESQL: ${POSTGRESQL}

            """
            DEPLOYMENTS = [LEGAL_API, COLIN_API, COOPS_UI, ORACLE, POSTGRESQL]
            // scale down all deployments to reset any connections
            for (name in DEPLOYMENTS) {
                scale_down(NAMESPACE, TAG_NAME, COMPONENT_TAG, name)
            }
            sleep 10
            // scale up all deployments
            for (name in DEPLOYMENTS) {
                scale_up(NAMESPACE, TAG_NAME, COMPONENT_TAG, name)
            }
            // wait for deployments to boot up
            openshift.withCluster() {
                openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                    // confirm all deployments are up (otherwise wait till all pods are up)
                    for (name in DEPLOYMENTS) {
                        echo "Verifying ${name} has a pod up and running"
                        deploy = openshift.selector("dc", "${name}-${COMPONENT_TAG}")
                        def version = deploy.object().status.latestVersion
                        pod_selector = openshift.selector('pod', [deployment: "${name}-${COMPONENT_TAG}-${version}"])
                        def latest = pod_selector.objects().size()
                        if (latest) {
                            latest--
                        }
                        if (latest || !pod_selector.objects()[latest] || pod_selector.objects()[latest].status.phase != 'Running' || !pod_selector.objects()[latest].status.containerStatuses[0].ready) {
                            pod_selector.untilEach {
                                if (!it.objects()[latest]) {
                                    if (latest > 0) {
                                        latest--
                                    }
                                    return false
                                }
                                deployment = it.objects()[latest].metadata.labels.deployment
                                echo "checking for ${deployment}"
                                if (it.objects()[latest].status.phase == 'Running' && it.objects()[latest].status.containerStatuses[0].ready) {
                                    return true
                                } else {
                                    echo "${name}-${COMPONENT_TAG} pod not ready"
                                    echo "Note: colin-api will be unhealthy until oracle config is finished (usually takes ~3 minutes)"
                                    sleep 5
                                    return false
                                }
                            }
                        }
                    }

                    def legal_deploy = openshift.selector("dc", "${LEGAL_API}-${COMPONENT_TAG}")
                    def pg_deploy = openshift.selector('dc', "${POSTGRESQL}-${COMPONENT_TAG}")
                    def colin_deploy = openshift.selector('dc', "${COLIN_API}-${COMPONENT_TAG}")
                    def coops_ui_deploy = openshift.selector('dc', "${COOPS_UI}-${COMPONENT_TAG}")

                    // get db user + db name envs from legal pod
                    def legal_version = legal_deploy.object().status.latestVersion
                    legal_pod = openshift.selector('pod', [deployment: "${LEGAL_API}-${COMPONENT_TAG}-${legal_version}"])
                    def latest = legal_pod.objects().size()
                    if (latest) {
                        latest--
                    }
                    LEGAL_DB_USERNAME = openshift.exec(
                        legal_pod.objects()[latest].metadata.name,
                        '--',
                        "bash -c 'printenv DATABASE_USERNAME'"
                    ).actions[0].out
                    LEGAL_DB_NAME = openshift.exec(
                        legal_pod.objects()[latest].metadata.name,
                        '--',
                        "bash -c 'printenv DATABASE_NAME'"
                    ).actions[0].out
                    echo """
                    - LEGAL_DB_USERNAME: ${LEGAL_DB_USERNAME}
                    - LEGAL_DB_NAME: ${LEGAL_DB_NAME}
                    """
                    echo "Scaling down ${LEGAL_API}-${COMPONENT_TAG}"
                    legal_deploy.scale('--replicas=0')

                    // reset legal db
                    echo "Dropping ${LEGAL_DB_NAME} in ${POSTGRESQL}-${COMPONENT_TAG}"
                    def pg_version = pg_deploy.object().status.latestVersion
                    PG_POD = openshift.selector('pod', [deployment: "${POSTGRESQL}-${COMPONENT_TAG}-${pg_version}"])
                    latest = PG_POD.objects().size()-1

                    // execute as postgres user and drop db
                    def output_disconnect_db = openshift.exec(
                        PG_POD.objects()[latest].metadata.name,
                        '--',
                        "bash -c \"\
                            psql -c \\\"\
                                UPDATE pg_database SET datallowconn = 'false' WHERE datname = '${LEGAL_DB_NAME}'; \
                                SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${LEGAL_DB_NAME}'; \
                            \\\" \
                        \""
                    )
                    echo "Temporary DB disconnect results: "+ output_disconnect_db.actions[0].out

                    // execute as postgres user and drop db
                    def output_drop_db = openshift.exec(
                        PG_POD.objects()[latest].metadata.name,
                        '--',
                        "bash -c \"\
                            psql -c \\\"\
                                DROP DATABASE \\\\\\\"${LEGAL_DB_NAME}\\\\\\\"; \
                            \\\" \
                        \""
                    )
                    echo "Temporary DB drop results: "+ output_drop_db.actions[0].out

                    echo "Creating ${LEGAL_DB_NAME} in ${POSTGRESQL}-${COMPONENT_TAG}"
                    // execute as postgres user and create test db
                    def output_create_db = openshift.exec(
                        PG_POD.objects()[latest].metadata.name,
                        '--',
                        "bash -c '\
                            psql -c \"CREATE DATABASE \\\"${LEGAL_DB_NAME}\\\";\" \
                        '"
                    )
                    echo "Temporary DB create results: "+ output_create_db.actions[0].out

                    def output_alter_role = openshift.exec(
                        PG_POD.objects()[latest].metadata.name,
                        '--',
                        "bash -c '\
                            psql -c \"ALTER ROLE \\\"${LEGAL_DB_USERNAME}\\\" WITH superuser;\" \
                        '"
                    )
                    echo "Temporary DB grant results: "+ output_alter_role.actions[0].out

                    OLD_VERSIONS = ["${LEGAL_API}-${legal_version}", "${COLIN_API}-${colin_deploy.object().status.latestVersion}", "${COOPS_UI}-${coops_ui_deploy.object().status.latestVersion}"]

                    echo "Rolling out ${LEGAL_API}-${COMPONENT_TAG}"
                    legal_deploy.rollout().latest()
                    legal_deploy.scale('--replicas=1')

                    echo "Rolling out ${COOPS_UI}-${COMPONENT_TAG}"
                    coops_ui_deploy.rollout().latest()

                    echo "Scaling down ${COLIN_API}-${COMPONENT_TAG}"
                    colin_deploy.scale('--replicas=0')

                    openshift.withProject('gl2uos-tools') {
                        // start + wait for ora-pipline to finish
                        echo "Resetting ${ORACLE}-${COMPONENT_TAG}"
                        def ora = openshift.selector('bc', 'oradb-startup-pipeline')
                        ora.startBuild('--wait=true', "-e=namespace=${NAMESPACE}", "-e=component=${ORACLE}", "-e=tag=${TAG_NAME}", "-e=component_tag=${COMPONENT_TAG}").logs('-f')
                    }

                    echo "Rolling out ${COLIN_API}-${COMPONENT_TAG}"
                    colin_deploy.rollout().latest()
                    colin_deploy.scale('--replicas=1')
                }
            }
        }
    }
    stage("Verify Deployments") {
        //sleep 10
        def components = [LEGAL_API, COLIN_API, COOPS_UI]
        verify_new_deployments(NAMESPACE, TAG_NAME, COMPONENT_TAG, OLD_VERSIONS, components)
    }
    stage('Run Postman Tests') {
        script {
            openshift.withCluster() {
                openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                    // prep postgres for tests
                    echo "Prepping database"
                    def latest = PG_POD.objects().size()-1
                    def legal_name = '\'legal name CP0002098\''
                    def founding_date = '\'2019-06-10\''
                    def identifier = '\'CP0002098\''
                    def output_alter_role = openshift.exec(
                        PG_POD.objects()[latest].metadata.name,
                        '--',
                        "bash -c \"\
                            psql -d ${LEGAL_DB_NAME} -c \\\"INSERT INTO businesses (legal_name, founding_date, identifier) VALUES (${legal_name}, ${founding_date}, ${identifier});\\\" \
                        \""
                    )
                    echo "Temporary DB grant results: "+ output_alter_role.actions[0].out
                    // run postman pipeline
                    apis = ['colin-api', 'legal-api']
                    for (name in apis) {
                        echo "Running ${name} pm collection"
                        try {
                            def url = ""
                            if (name == 'colin-api') {
                                url = "http://${name}-${COMPONENT_TAG}.${NAMESPACE}-${TAG_NAME}.svc:8080"
                            } else {
                                url = "https://${name}-${COMPONENT_TAG}.pathfinder.gov.bc.ca"
                            }
                            def pm_pipeline = openshift.selector('bc', 'postman-pipeline')
                            pm_pipeline.startBuild('--wait=true', "-e=component=${name}", "-e=url=${url}").logs('-f')
                        } catch (Exception e) {
                            PASSED = false
                            def error_message = e.getMessage()
                            echo """
                            Postman details for ${name}: ${error_message}
                            """
                        }
                    }
                }
            }
        }
    }
    stage('Run E2E Tests') {
        script {
            echo "E2E tests not implemented yet."
        }
    }
    stage('Clean E2E Environment') {
        script {
            openshift.withCluster() {
                openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                    // scale down all deployments
                    for (name in DEPLOYMENTS) {
                        deploy = openshift.selector("dc", "${name}-${COMPONENT_TAG}")
                        echo "Scaling down ${name}-${COMPONENT_TAG}"
                        deploy.scale('--replicas=0')
                    }
                }
            }
        }
    }
    stage('Check test result') {
        script {
            if (!PASSED) {
                echo "One or more tests failed."
                currentBuild.result = "FAILURE"
            }
        }
    }
}
