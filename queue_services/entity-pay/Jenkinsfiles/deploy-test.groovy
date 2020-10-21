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
def COMPONENT_NAME = 'entity-pay'
def TAG_NAME = 'test'
def SOURCE_TAG = 'dev'
def DEPLOY_PIPELINE = 'deploy-service'
def DEPLOY_PIPELINE_LOC = 'gl2uos-tools'

// define job properties - keep 10 builds only
properties([
    [$class: 'BuildDiscarderProperty', strategy: [$class: 'LogRotator', artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '', numToKeepStr: '2'
        ]
    ]
])
stage("deploy ${COMPONENT_NAME}-${TAG_NAME}") {
    script {
        openshift.withCluster() {
            openshift.withProject("${DEPLOY_PIPELINE_LOC}") {
                def deploy_pipeline = openshift.selector('bc', "${DEPLOY_PIPELINE}")
                deploy_pipeline.startBuild(
                    '--wait=true', 
                    "-e=NAMESPACE=${NAMESPACE}",
                    "-e=COMPONENT_NAME=${COMPONENT_NAME}",
                    "-e=TAG_NAME=${TAG_NAME}",
                    "-e=SOURCE_TAG=${SOURCE_TAG}"
                ).logs('-f')
            }
        }
    }
}
