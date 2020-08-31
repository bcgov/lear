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
        def run_sql = "echo \"${command}\"|\"\$ORACLE_HOME/bin/sqlplus\" / as sysdba"
        command = run_sql
    }
    echo "${pod} executing ${command}..."
    def command_output = openshift.exec(
        pod,
        '--',
        "bash -c '${command}'"
    ).actions[0].out
    echo command_output
}

node {
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

                    sql = 'select id_num from system_id where id_typ_cd in (\\\"BC\\\");'
                    execute_pod_command(OLD_POD, sql, true)

                    // sql = 'shutdown abort;'
                    // execute_pod_command(OLD_POD, run_sql)
                    // execute_pod_command(OLD_POD, 'rm -Rf /ORCL/*')
                    // try {
                    //     execute_pod_command(OLD_POD, 'cp -a /ORCL_base/. /ORCL/')
                    // } catch (Exception e) {
                    //     echo e.getMessage()
                    // }
                }
            }
        }
    } // end stage
    stage('deploy oracle') {
        // script {
        //     openshift.withCluster() {
        //         openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
        //             def deploy = openshift.selector("dc", "${COMPONENT_NAME}-${COMPONENT_TAG}")
        //             def podSelector = openshift.selector('pod', [ app:"${COMPONENT_NAME}-${COMPONENT_TAG}" ])

        //             deploy.rollout().latest()
        //             def count = 1
        //             podSelector.untilEach {
        //                 def pod = it.objects()[0].metadata.name
        //                 echo "pod: ${pod}"
        //                 if (pod != OLD_POD && it.objects()[0].status.phase == 'Running' && it.objects()[0].status.containerStatuses[0].ready) {
        //                     echo "New pod: ${pod}"
        //                     sleep 80
        //                     echo "waited ${count*80} seconds"
        //                     try {
        //                         echo "${pod}"
        //                         sequences = ['noncorp_event_seq', 'noncorp_address_seq', 'noncorp_party_seq']
        //                         for (seq in sequences) {
        //                             sql = 'alter sequence C##CDEV.${seq} increment by 50;'
        //                             execute_pod_command(pod, run_sql)

        //                             sql = 'select C##CDEV.${seq}.NEXTVAL from dual;'
        //                             execute_pod_command(pod, run_sql)

        //                             sql = 'alter sequence C##CDEV.${seq} increment by 1;'
        //                             execute_pod_command(pod, run_sql)
        //                         }
        //                         return true
        //                     } catch (Exception e) {
        //                         echo "${e}"
        //                         count++
        //                         return false
        //                     }
        //                 } else {
        //                     return false;
        //                 }
        //             }

        //         }
        //     }
        // }

    } // end stage
} // end node
