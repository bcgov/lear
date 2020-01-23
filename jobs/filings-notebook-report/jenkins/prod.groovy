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

import groovy.json.*

// define constants - values sent in as env vars from whatever calls this pipeline
def APP_NAME = 'filings-notebook-report'
def APP_NAME_RUNTIME ='filings-notebook-report-runtime'
def SOURCE_TAG = 'test'
def DESTINATION_TAG = 'prod'
def TOOLS_TAG = 'tools'

def NAMESPACE_APP = 'gl2uos'
def NAMESPACE_BUILD = "${NAMESPACE_APP}"  + '-' + "${TOOLS_TAG}"
def NAMESPACE_DEPLOY = "${NAMESPACE_APP}" + '-' + "${DESTINATION_TAG}"

def ROCKETCHAT_DEVELOPER_CHANNEL='#registries-entities'

// post a notification to rocketchat
def rocketChatNotificaiton(token, channel, comments) {
  def payload = JsonOutput.toJson([text: comments, channel: channel])
  def rocketChatUrl = "https://chat.pathfinder.gov.bc.ca/hooks/" + "${token}"

  sh(returnStdout: true,
     script: "curl -X POST -H 'Content-Type: application/json' --data \'${payload}\' ${rocketChatUrl}")
}


// Get an image's hash tag
String getImageTagHash(String imageName, String tag = "") {
    if(!tag?.trim()) {
        tag = "latest"
    }

    def istag = openshift.raw("get istag ${imageName}:${tag} -o template --template='{{.image.dockerImageReference}}'")
    return istag.out.tokenize('@')[1].trim()
}

node {
    properties([[$class: 'BuildDiscarderProperty', strategy: [$class: 'LogRotator', artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '', numToKeepStr: '10']]])

    def build_ok = true
    def old_version

	stage("Tag ${APP_NAME_RUNTIME}:${DESTINATION_TAG}") {				
	  script {
		openshift.withCluster() {
		  openshift.withProject() {
			try{
				echo "Tagging ${APP_NAME_RUNTIME} for deployment to ${DESTINATION_TAG} ..."

				// Don't tag with BUILD_ID so the pruner can do it's job; it won't delete tagged images.
				// Tag the images for deployment based on the image's hash
				def IMAGE_HASH = getImageTagHash("${APP_NAME_RUNTIME}")
				echo "IMAGE_HASH: ${IMAGE_HASH}"
				openshift.tag("${APP_NAME_RUNTIME}@${IMAGE_HASH}", "${APP_NAME_RUNTIME}:${DESTINATION_TAG}")
			} catch (Exception e) {
				echo e.getMessage()
				build_ok = false
			}
		  }
		}
	  }
	}


    stage("Notify on RocketChat") {
        if(build_ok) {
            currentBuild.result = "SUCCESS"
        } else {
            currentBuild.result = "FAILURE"
        }

        ROCKETCHAT_TOKEN = sh (
                script: """oc get secret/apitest-secrets -n ${NAMESPACE_BUILD} -o template --template="{{.data.ROCKETCHAT_TOKEN}}" | base64 --decode""",
                    returnStdout: true).trim()

        rocketChatNotificaiton("${ROCKETCHAT_TOKEN}", "${ROCKETCHAT_DEVELOPER_CHANNEL}", "${APP_NAME} build and deploy to ${DESTINATION_TAG} ${currentBuild.result}!")
    }
}