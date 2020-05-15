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
NAMESPACE = 'gl2uos'
TAG_NAME = 'prod'
JOB = 'legal-updater'
K8S_PATH = 'jobs/update-legal-filings/k8s/'
RUN_JOB_LOC = 'gl2uos-tools'
RUN_JOB_NAME = 'run-job-pipeline'

stage("details in tools run-job-pipeline") {
    script {
        openshift.withCluster() {
            openshift.withProject("${RUN_JOB_LOC}") {
                def run_job_pipeline = openshift.selector('bc', "${RUN_JOB_NAME}")
                run_job_pipeline.startBuild(
                    '--wait=true', 
                    "-e=NAMESPACE=${NAMESPACE}", 
                    "-e=TAG_NAME=${TAG_NAME}",
                    "-e=JOB=${JOB}",
                    "-e=K8S_PATH=${K8S_PATH}"
                ).logs('-f')
            }
        }
    }
}
