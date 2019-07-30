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
def COMPONENT = component
def URL = url

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
        envVars: [
            secretEnvVar(key: 'AUTHURL', secretName: "${COMPONENT}-postman-e2e", secretKey: 'authurl'),
            secretEnvVar(key: 'REALM', secretName: "${COMPONENT}-postman-e2e", secretKey: 'realm'),
            secretEnvVar(key: 'PASSWORD', secretName: "${COMPONENT}-postman-e2e", secretKey: 'password'),
            secretEnvVar(key: 'CLIENT_SECRET', secretName: "${COMPONENT}-postman-e2e", secretKey: 'client_secret'),
            secretEnvVar(key: 'USERID', secretName: "${COMPONENT}-postman-e2e", secretKey: 'userid'),
            secretEnvVar(key: 'CLIENTID', secretName: "${COMPONENT}-postman-e2e", secretKey: 'clientid'),
        ]
    )
])
{
    node(py3nodejs_label) {
        stage("Running ${COMPONENT} tests") {

            echo """
            URL:${URL}
            AUTHURL:${AUTHURL}
            REALM:${REALM}
            USERID:${USERID}
            PASSWORD:${PASSWORD}
            CLIENTID:${CLIENTID}
            CLIENT_SECRET:${CLIENT_SECRET}
            """
            checkout scm

            dir("${COMPONENT}${TESTS_PATH}") {

                sh 'npm install newman'

                try {
                    sh """./node_modules/newman/bin/newman.js run ./${COMPONENT}.postman_collection.json \
                    --global-var url=${URL} --global-var auth_url=${AUTHURL} --global-var realm=${REALM} \
                    --global-var password=${PASSWORD} --global-var client_secret=${CLIENT_SECRET} \
                    --global-var userid=${USERID} --global-var clientid=${CLIENTID}
                    """

                } catch (Exception e) {
                    echo "One or more tests failed."
                    echo "${e.getMessage()}"
                    currentBuild.result = "FAILED"
                }

            } // end dir
        } //end stage
    } //end node
} //end podTemplate
