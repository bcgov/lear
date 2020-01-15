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
// set from call
def COMPONENT_NAME = "legal-api"
def COMPONENT_TAG = 'dev'

// constant
def TESTS_PATH = '/tests/postman'

// define groovy functions
import groovy.json.JsonOutput

def py3nodejs_label = "jenkins-py3nodejs-${UUID.randomUUID().toString()}"
podTemplate(label: py3nodejs_label, name: py3nodejs_label, serviceAccount: 'jenkins', cloud: 'openshift', containers: [
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
        echo: "check envVar",
        envVars:([
            secretEnvVar(key: 'AUTH_URL', secretName: "postman-dev-secret", secretKey: 'auth_url')



        ])
    )
])
{
    node(py3nodejs_label) {
        script {
            echo """
            AUTH_URL:${AUTH_URL} \
            """
            checkout scm

            dir("${COMPONENT_NAME}${TESTS_PATH}") {
                all_passed = true

                sh 'npm install newman'
                stage("Running ${COMPONENT_NAME} pm tests") {
                    try {
                        echo "Running ${COMPONENT_NAME} pm collection"
                        url = "https://${COMPONENT_NAME}-${COMPONENT_TAG}.pathfinder.gov.bc.ca"

                        sh """./node_modules/newman/bin/newman.js run ./${name}.postman_collection.json \
                        --global-var auth_url=${AUTH_URL} 

                        """
                    } catch (Exception e) {
                        echo "One or more tests failed."
                        echo "${e.getMessage()}"
                        all_passed = false
                    }
                }
                stage("Result") {
                    if (!all_passed) {
                        currentBuild.result = "FAILURE"
                    }
                }
            } // end dir
        } // end script
    } //end node
} //end podTemplate