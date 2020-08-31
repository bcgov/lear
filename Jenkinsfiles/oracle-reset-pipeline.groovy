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
def NAMESPACE = namespace
def TAG_NAME = tag
def COMPONENT_NAME = component
def COMPONENT_TAG = component_tag
def OLD_POD
def USERNAME
def PASSWORD

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
                    def shutdownDb = openshift.exec(
                        OLD_POD,
                        '--',
                        "bash -c ' \
                        echo \"shutdown abort;\"|\"\$ORACLE_HOME/bin/sqlplus\" / as sysdba \
                        '"
                    ).actions[0].out
                    echo shutdownDb
                    def deleteORCL = openshift.exec(
                        OLD_POD,
                        '--',
                        "bash -c '\
                        rm -Rf /ORCL/*'"
                    ).actions[0].out
                    echo deleteORCL
                    try {
                        def resetORCL = openshift.exec(
                            OLD_POD,
                            '--',
                            "bash -c '\
                            cp -a /ORCL_base/. /ORCL/'"
                        ).actions[0].out
                        echo resetORCL
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
                    def count = 1
                    podSelector.untilEach {
                        def pod = it.objects()[0].metadata.name
                        echo "pod: ${pod}"
                        if (pod != OLD_POD && it.objects()[0].status.phase == 'Running' && it.objects()[0].status.containerStatuses[0].ready) {
                            echo "New pod: ${pod}"
                            sleep 80
                            echo "waited ${count*80} seconds"
                            try {
                                echo "${pod}"
                                sequences = ['noncorp_event_seq', 'noncorp_address_seq', 'noncorp_party_seq']
                                for (seq in sequences) {
                                    def inc_seq_50 = openshift.exec(
                                        pod,
                                        '--',
                                        "bash -c ' \
                                        echo \"alter sequence C##CDEV.${seq} increment by 50;\"|\"\$ORACLE_HOME/bin/sqlplus\" / as sysdba \
                                        '"
                                    ).actions[0].out
                                    echo inc_seq_50
                                    def set_seq_val = openshift.exec(
                                        pod,
                                        '--',
                                        "bash -c ' \
                                        echo \"select C##CDEV.${seq}.NEXTVAL from dual;\"|\"\$ORACLE_HOME/bin/sqlplus\" / as sysdba \
                                        '"
                                    ).actions[0].out
                                    echo set_seq_val
                                    def reset_seq_inc = openshift.exec(
                                        pod,
                                        '--',
                                        "bash -c ' \
                                        echo \"alter sequence C##CDEV.${seq} increment by 1;\"|\"\$ORACLE_HOME/bin/sqlplus\" / as sysdba \
                                        '"
                                    ).actions[0].out
                                    echo reset_seq_inc
                                }
                                return true
                            } catch (Exception e) {
                                echo "${e}"
                                count++
                                return false
                            }
                        } else {
                            return false;
                        }
                    }

                }
            }
        }

    } // end stage
} // end node
