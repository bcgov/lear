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
def NAMESPACE = 'gl2uos'
def COMPONENT_NAME = 'entity-filer'
def TAG_NAME = 'test'
def SOURCE_TAG = 'dev'
def E2E_TAG = 'e2e'
def E2E_NAMESPACE = 'd7eovc'
def E2E_PROJ = 'tools'

// define groovy functions
import groovy.json.JsonOutput

// Get an image's hash tag
String getImageTagHash(String imageName, String tag = "") {

  if(!tag?.trim()) {
    tag = "latest"
  }

  def istag = openshift.raw("get istag ${imageName}:${tag} -o template --template='{{.image.dockerImageReference}}'")
  return istag.out.tokenize('@')[1].trim()
}

// pipeline
// define job properties - keep 10 builds only
properties([
    [$class: 'BuildDiscarderProperty', strategy: [$class: 'LogRotator', artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '', numToKeepStr: '10'
        ]
    ]
])

node {
    stage("Tag image for E2E") {
        script {
            openshift.withCluster() {
                openshift.withProject() {
                    echo "Tagging ${COMPONENT_NAME}:${E2E_TAG}-prev with ${E2E_TAG}..."

                    def IMAGE_HASH = getImageTagHash("${COMPONENT_NAME}", "${E2E_TAG}")
                    echo "IMAGE_HASH: ${IMAGE_HASH}"
                    openshift.tag("${COMPONENT_NAME}@${IMAGE_HASH}", "${COMPONENT_NAME}:${E2E_TAG}-prev")

                    echo "Tagging ${COMPONENT_NAME} to ${E2E_TAG} ..."

                    IMAGE_HASH = getImageTagHash("${COMPONENT_NAME}", "${SOURCE_TAG}")
                    echo "IMAGE_HASH: ${IMAGE_HASH}"
                    openshift.tag("${COMPONENT_NAME}@${IMAGE_HASH}", "${COMPONENT_NAME}:${E2E_TAG}")
                }
            }
        }
    }
    def passed = true
    stage("Run E2E Tests") {
        script {
            try {
                timeout(time: 1, unit: 'DAYS') {
                    input message: "Run E2E pipeline?", id: "1234", submitter: 'admin,thorwolpert-admin,rarmitag-admin,kialj876-admin,katiemcgoff-edit,WalterMoar-admin,JohnamLane-edit'
                }
                openshift.withCluster() {
                    openshift.withProject("${E2E_NAMESPACE}-${E2E_PROJ}") {
                        def e2e_pipeline = openshift.selector('bc', 'e2e-pipeline')
                        try {
                            echo "Running e2e pipeline (check ${E2E_NAMESPACE}-${E2E_PROJ} to view progress)..."
                            e2e_pipeline.startBuild('--wait=true').logs('-f')
                            echo "E2E tests passed!"
                        } catch (Exception e) {
                            echo "E2E tests failed: ${e.getMessage()}"
                            passed = false
                        }
                    }
                }
            } catch (Exception e0) {
                echo "Did not run E2E pipeline."
                passed = false
            }
        }
    }
    def end_pipeline = false
    stage("Verify E2E Tests") {
        script {
            if (!passed) {
                try {
                    timeout(time: 1, unit: 'DAYS') {
                        input message: "E2E failed or were not run. Proceed to test?", id: "1234", submitter: 'admin,thorwolpert-admin,rarmitag-admin,kialj876-admin,katiemcgoff-edit,WalterMoar-admin,JohnamLane-edit'
                    }
                } catch (Exception e1) {
                    try {
                        timeout(time: 1, unit: 'DAYS') {
                            input message: "Keep E2E image?", id: "1234", submitter: 'admin,thorwolpert-admin,rarmitag-admin,kialj876-admin,katiemcgoff-edit,WalterMoar-admin,JohnamLane-edit'
                        }
                    } catch (Exception e2) {
                        echo "Reverting E2E image back to previous image..."
                        openshift.withCluster() {
                            openshift.withProject() {
                                echo "Tagging ${COMPONENT_NAME}:${E2E_TAG} with ${E2E_TAG}-prev ..."

                                def IMAGE_HASH = getImageTagHash("${COMPONENT_NAME}", "${E2E_TAG}-prev")
                                echo "IMAGE_HASH: ${IMAGE_HASH}"
                                openshift.tag("${COMPONENT_NAME}@${IMAGE_HASH}", "${COMPONENT_NAME}:${E2E_TAG}")
                            }
                        }
                    } finally {
                        currentBuild.result = 'FAILURE'
                        end_pipeline = true
                        return
                    }
                }
            }
        }
    }
    if (!end_pipeline) {
        def old_version
        stage("Deploy ${COMPONENT_NAME}:${TAG_NAME}") {
            script {
                openshift.withCluster() {
                    openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                        old_version = openshift.selector('dc', "${COMPONENT_NAME}-${TAG_NAME}").object().status.latestVersion
                    }
                }
                openshift.withCluster() {
                    openshift.withProject() {

                        echo "Tagging ${COMPONENT_NAME} for deployment to ${TAG_NAME} ..."

                        // Don't tag with BUILD_ID so the pruner can do it's job; it won't delete tagged images.
                        // Tag the images for deployment based on the image's hash
                        def IMAGE_HASH = getImageTagHash("${COMPONENT_NAME}", "${SOURCE_TAG}")
                        echo "IMAGE_HASH: ${IMAGE_HASH}"
                        openshift.tag("${COMPONENT_NAME}@${IMAGE_HASH}", "${COMPONENT_NAME}:${TAG_NAME}")
                    }
                }
            }
        }
        stage("Verify deployment") {
            sleep 10
            script {
                openshift.withCluster() {
                    openshift.withProject("${NAMESPACE}-${TAG_NAME}") {
                        def new_version = openshift.selector('dc', "${COMPONENT_NAME}-${TAG_NAME}").object().status.latestVersion
                        if (new_version == old_version) {
                            echo "New deployment was not triggered."
                            currentBuild.result = "FAILURE"
                            return
                        }
                        def pod_selector = openshift.selector('pod', [ app:"${COMPONENT_NAME}-${TAG_NAME}" ])
                        pod_selector.untilEach {
                            deployment = it.objects()[0].metadata.labels.deployment
                            echo deployment
                            if (deployment ==  "${COMPONENT_NAME}-${TAG_NAME}-${new_version}" && it.objects()[0].status.phase == 'Running' && it.objects()[0].status.containerStatuses[0].ready) {
                                return true
                            } else {
                                echo "Pod for new deployment not ready"
                                sleep 5
                                return false
                            }
                        }
                    }
                }
            }
        }
        stage("Run pytests for ${COMPONENT_NAME}:${TAG_NAME}") {
            script {
                openshift.withCluster() {
                    openshift.withProject() {
                        def test_pipeline = openshift.selector('bc', 'pytest-pipeline')
                        try {
                            test_pipeline.startBuild('--wait=true', "-e=component=${COMPONENT_NAME}", "-e=component_tag=${TAG_NAME}", "-e=tag=${TAG_NAME}", "-e=namespace=${NAMESPACE}", "-e=db_type=PG").logs('-f')
                            echo "All tests passed"
                        } catch (Exception e) {
                            echo e.getMessage()
                            echo "Not all tests passed."
                            currentBuild.result = 'FAILURE'
                        }
                    }
                }
            }
        }
    }
}//end node
