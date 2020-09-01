#!/usr/bin/env groovy
//
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
NAMESPACE = namespace
TAG_NAME = tag
COMPONENT_NAME = component
COMPONENT_TAG = component_tag

def OLD_POD
def USERNAME
def PASSWORD

def execute_pod_command(pod, command, is_sql) {
    if (is_sql) {
        def run_sql = "echo \\\"${command}\\\"|\\\"\\\$ORACLE_HOME/bin/sqlplus\\\" / as sysdba"
        command = run_sql
    }
    echo "${pod} executing ${command}..."
    def command_output = openshift.exec(
        pod,
        '--',
        "bash -c \"${command}\""
    ).actions[0].out
    echo command_output
    return command_output
}

node {
    def id_num
    stage('reset oracle') {
        script {
            echo """
            Pipeline called with constants:
                - NAMESPACE: ${NAMESPACE}
                - TAG_NAME: ${TAG_NAME}
                - COMPONENT_NAME: ${COMPONENT_NAME}
                - COMPONENT_TAG: ${COMPONENT_TAG}
            """
            openshift.withCluster() {
                openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                    def podSelector = openshift.selector('pod', [ app:"${COMPONENT_NAME}-${COMPONENT_TAG}" ])
                    OLD_POD = podSelector.objects()[0].metadata.name
                    echo "OLD_POD: ${OLD_POD}"
                    try {
                        sql = "select id_num from C##CDEV.system_id where id_typ_cd in ('BC');"
                        id_num_output = execute_pod_command(OLD_POD, sql, true)
                        id_num_regex = /\d{7}(?:\d{2})?/
                        id_num = (id_num_output =~ id_num_regex)[0]
                    } catch (Exception e) {
                        echo e.getMessage()
                    }
                    sql = 'shutdown abort;'
                    execute_pod_command(OLD_POD, sql, true)

                    try {
                        execute_pod_command(OLD_POD, 'rm -Rf /ORCL/*', false)    
                    } catch (Exception e) {
                        // try twice -- usually fails once
                        echo e.getMessage()
                        execute_pod_command(OLD_POD, 'rm -Rf /ORCL/*', false)
                    }
                    try {
                        execute_pod_command(OLD_POD, 'cp -a /ORCL_base/. /ORCL/', false)
                    } catch (Exception e) {
                        echo e.getMessage()
                    }
                }
            }
        }
    } // end stage
    stage('deploy oracle') {
        script {
            openshift.withCluster() {
                openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                    def deploy = openshift.selector("dc", "${COMPONENT_NAME}-${COMPONENT_TAG}")
                    def podSelector = openshift.selector('pod', [ app:"${COMPONENT_NAME}-${COMPONENT_TAG}" ])

                    deploy.rollout().latest()
                    podSelector.untilEach {
                        def pod_object = it.objects()[0]
                        def pod = pod_object.metadata.name
                        echo "pod: ${pod}"
                        if (pod != OLD_POD && pod_object.status.phase == 'Running' && pod_object.status.containerStatuses[0].ready) {
                            echo "New pod: ${pod}"
                            def count = 1
                            while (count < 30) {
                                sleep 10
                                echo "waited ${count*10} seconds"
                                try {
                                    echo "${pod}"
                                    sql = "select 'database ready' from dual;"
                                    ready = execute_pod_command(pod, sql, true)
                                    if (ready.contains('ERROR')) {
                                        echo 'database not ready yet.'
                                        throw new Exception('database not ready yet.')
                                    }

                                    sequences = ['noncorp_event_seq', 'noncorp_address_seq', 'noncorp_party_seq']
                                    for (seq in sequences) {
                                        sql = "alter sequence C##CDEV.${seq} increment by 50;"
                                        execute_pod_command(pod, sql, true)

                                        sql = "select C##CDEV.${seq}.NEXTVAL from dual;"
                                        execute_pod_command(pod, sql, true)

                                        sql = "alter sequence C##CDEV.${seq} increment by 1;"
                                        execute_pod_command(pod, sql, true)
                                    }
                                    if (id_num==null) {
                                        id_num = '123000'
                                        echo "Error getting id_num. Setting to default: ${id_num}"
                                    }
                                    sql = "UPDATE C##CDEV.system_id SET id_num=${id_num} WHERE id_typ_cd = 'BC';"
                                    execute_pod_command(pod, sql, true)

                                    sql = "INSERT INTO C##CDEV.FILING_TYPE_CLASS VALUES('BENCOM','Benefit Company');"
                                    execute_pod_command(pod, sql, true)

                                    sql = "INSERT INTO C##CDEV.FILING_TYPE VALUES('BEINC','BENCOM','Incorporate a BC Benefit Company','Incorporation Application for a BC Benefit Company');"
                                    execute_pod_command(pod, sql, true)

                                    sql = "INSERT INTO C##CDEV.FILING_TYPE VALUES('NOALE','BENCOM','Alteration from a BC Company to a Benefit Company','Alteration Application from a BC Company to a Benefit Company');"
                                    execute_pod_command(pod, sql, true)

                                    sql = "INSERT INTO C##CDEV.CORP_TYPE VALUES('BEN','Y','BC','BENEFIT COMPANY','Benefit Company');"
                                    execute_pod_command(pod, sql, true)

                                    sql = "DROP TRIGGER C##CDEV.NAMEX_CORP_NAME_QMSG;"
                                    execute_pod_command(pod, sql, true)

                                    sql = "@/sql/update-dev-oracle.sql"
                                    execute_pod_command(pod, sql, true)

                                } catch (Exception e) {
                                    echo "${e}"
                                    count++
                                    continue
                                }
                                break
                            }
                            if (count > 29) {
                                echo "Pipeline failed to complete final commands."
                                currentBuild.result = "FAILURE"
                            }
                            return true
                        } else {
                            return false;
                        }
                    }

                }
            }
        }

    } // end stage
} // end node
