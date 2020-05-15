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

// define constants placeholder values
// set from call
NAMESPACE = 'gl2uos'
TAG_NAME = 'dev'
JOB = 'colin-updater'
K8S_PATH = 'jobs/update-colin-filings/k8s/'

stage("NI: Run ${JOB}") {
    // call/wait for job pipeline with colin-updater vals
    script {
        echo """
        Pipeline called with constants:
            - NAMESPACE: ${NAMESPACE}
            - TAG_NAME: ${TAG_NAME}
            - JOB: ${JOB}
            - K8S_PATH: ${K8S_PATH}
        """
        openshift.withCluster() {
            openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                checkout scm
                // use json + param files in k8s folder to build/replace job
                dir("${K8S_PATH}") {
                    replace_job = sh (
                        script: """ls""",
                            returnStdout: true
                    ).trim()
                    echo replace_job
                    // below is commented out code for data loader: use this and newer docs in business-create k8s folder for building the job
                    // try {
                    //     replace_job = sh (
                    //         script: """oc replace jobs/data-loader""",
                    //             returnStdout: true).trim()
                    //     echo replace_job
                    // } catch (Exception e) {
                           // job doesn't exist yet (hopefully)
                    //     echo "${e.getMessage()}"
                    //     data_load_output = sh (
                    //     script: """oc process -f data-loader.yml -p ENV_TAG=test | oc create -f -""",
                    //         returnStdout: true).trim()
                    // }
                }
                sleep 10
            }
        }
    }
}
stage("NI: Run ${JOB}") {
    // Verify job ran and succeeded
    script {
        openshift.withCluster() {
            openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                    // below is code for verifying dataloader ran -> repurpose for colin-updater
                // def data_loader = openshift.selector('pod', [ "job-name":"data-loader" ])
                // data_loader.untilEach {
                //     def pod = it.objects()[0].metadata.name
                //     echo "pod: ${pod}"
                //     if (it.objects()[0].status.phase == 'Succeeded') {
                //         echo "${pod} successfully loaded data."
                //         return true
                //     } else {
                //         return false;
                //         sleep 5
                //     }
                // }
            }
        }
    }
}
