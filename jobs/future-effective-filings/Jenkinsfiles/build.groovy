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
def COMPONENT_NAME = 'future-effective-filings'
def TAG_NAME = 'dev'
def NAMESPACE = 'gl2uos'

// define groovy functions
import groovy.json.JsonOutput

// Determine whether there were any changes the files within the project's context directory.
// return a string listing commit msgs occurred since last build
@NonCPS
String triggerBuild(String contextDirectory) {
    // Determine if code has changed within the source context directory.
    def changeLogSets = currentBuild.changeSets
    def filesChangeCnt = 0
    MAX_MSG_LEN = 512
    def changeString = ""
    for (int i = 0; i < changeLogSets.size(); i++) {
        def entries = changeLogSets[i
        ].items
        for (int j = 0; j < entries.length; j++) {
            def entry = entries[j
            ]
            //echo "${entry.commitId} by ${entry.author} on ${new Date(entry.timestamp)}: ${entry.msg}"
            def files = new ArrayList(entry.affectedFiles)

            for (int k = 0; k < files.size(); k++) {
                def file = files[k
                ]
                def filePath = file.path
                //echo ">> ${file.path}"
                if (filePath.contains(contextDirectory)) {

                    filesChangeCnt = 1
                    truncated_msg = entry.msg.take(MAX_MSG_LEN)
                    changeString += " - ${truncated_msg} [${entry.author}]\n"
                    k = files.size()
                    j = entries.length
                }
            }
        }
    }
    if ( filesChangeCnt < 1 ) {
        echo('The changes do not require a build.')
        return ""
    }
    else {
        echo('The changes require a build.')
        return changeString
    }
}
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

def run_pipeline = true
if( triggerBuild("jobs/${COMPONENT_NAME}") == "" ) {
    node {
        try {
            timeout(time: 1, unit: 'DAYS') {
                input message: "Run ${COMPONENT_NAME}-${TAG_NAME}-pipeline?", id: "1234", submitter: 'admin,thorwolpert-admin,rarmitag-admin,kialj876-admin,katiemcgoff-admin,WalterMoar-admin'
            }
        } catch (Exception e) {
            run_pipeline = false;
        }
    }
}
if (!run_pipeline) {
    echo('No Build Wanted - End of Build.')
    currentBuild.result = 'SUCCESS'
    return
}

node {
    stage("Build ${COMPONENT_NAME}") {
        script {
            openshift.withCluster() {
                openshift.withProject() {
                    echo "Building ${COMPONENT_NAME} ..."
                    def build = openshift.selector("bc", "${COMPONENT_NAME}")
                    build.startBuild("--wait=true").logs("-f")
                }
            }
        }
    }
    stage("Tag ${COMPONENT_NAME} to ${TAG_NAME}") {
        script {
            openshift.withCluster() {
                openshift.withProject() {

                    echo "Tagging ${COMPONENT_NAME} to ${TAG_NAME} ..."

                    // Don't tag with BUILD_ID so the pruner can do it's job; it won't delete tagged images.
                    // Tag the images for deployment based on the image's hash
                    def IMAGE_HASH = getImageTagHash("${COMPONENT_NAME}")
                    echo "IMAGE_HASH: ${IMAGE_HASH}"
                    openshift.tag("${COMPONENT_NAME}@${IMAGE_HASH}", "${COMPONENT_NAME}:${TAG_NAME}")
                }
            }
        }
    }
}
