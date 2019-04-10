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
def COMPONENT_NAME = 'legal-api'
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
// pipeline
// define job properties - keep 10 builds only
properties([
    [$class: 'BuildDiscarderProperty', strategy: [$class: 'LogRotator', artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '', numToKeepStr: '10'
        ]
    ]
])

def run_pipeline = true
if( triggerBuild(COMPONENT_NAME) == "" ) {
    node {
        try {
            timeout(time: 1, unit: 'DAYS') {
                input message: "Run ${COMPONENT_NAME}-${TAG_NAME}-pipeline?", id: "1234", submitter: 'admin,thorwolpert-admin,rarmitag-admin,kialj876-edit,katiemcgoff-edit,WalterMoar-admin'
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

def py3njs_label = "jenkins-py3nodejs-${UUID.randomUUID().toString()}"
    podTemplate(label: py3njs_label, name: py3njs_label, serviceAccount: 'jenkins', cloud: 'openshift', containers: [
        containerTemplate(
            name: 'jnlp',
            image: '172.50.0.2:5000/openshift/jenkins-slave-py3nodejs',
            resourceRequestCpu: '500m',
            resourceLimitCpu: '1000m',
            resourceRequestMemory: '1Gi',
            resourceLimitMemory: '2Gi',
            workingDir: '/tmp',
            command: '',
            args: '${computer.jnlpmac} ${computer.name}',
            envVars: [
                envVar(key:'DATABASE_TEST_HOST', value: "postgresql-test"),
                envVar(key:'DATABASE_TEST_PORT', value: "5432"),
                secretEnvVar(key: 'DATABASE_TEST_USERNAME', secretName: 'postgresql-test', secretKey: 'database-user'),
                secretEnvVar(key: 'DATABASE_TEST_PASSWORD', secretName: 'postgresql-test', secretKey: 'database-password'),
                secretEnvVar(key: 'DATABASE_TEST_NAME', secretName: 'postgresql-test', secretKey: 'database-name'),
                secretEnvVar(key: 'JWT_OIDC_WELL_KNOWN_CONFIG', secretName: 'namex-keycloak-secrets', secretKey: 'JWT_OIDC_WELL_KNOWN_CONFIG'),
                secretEnvVar(key: 'JWT_OIDC_ALGORITHMS', secretName: 'namex-keycloak-secrets', secretKey: 'JWT_OIDC_ALGORITHMS'),
                secretEnvVar(key: 'JWT_OIDC_AUDIENCE', secretName: 'namex-keycloak-secrets', secretKey: 'JWT_OIDC_AUDIENCE'),
                secretEnvVar(key: 'JWT_OIDC_CLIENT_SECRET', secretName: 'namex-keycloak-secrets', secretKey: 'JWT_OIDC_CLIENT_SECRET')
           ]
        )
    ]
)


node (py3njs_label){
    // Part 1 - CI - Source code scanning, build, dev deploy
    stage("Build ${COMPONENT_NAME}") {
        try {
            echo "Building..."
            openshiftBuild bldCfg: COMPONENT_NAME, verbose: 'false', showBuildLogs: 'true'

            sleep 5

            // openshiftVerifyBuild bldCfg: BUILDCFG_NAME
            echo ">>> Get Image Hash"
            IMAGE_HASH = sh (
                script: """oc get istag ${COMPONENT_NAME}:latest -o template --template=\"{{.image.dockerImageReference}}\"|awk -F \":\" \'{print \$3}\'""",
                    returnStdout: true).trim()
            echo ">> IMAGE_HASH: ${IMAGE_HASH}"
            echo ">>>> Build Complete"

        } catch (Exception e) {
            echo "error during build: ${e}"
            error('Aborted')
        }
    }//end stage
}