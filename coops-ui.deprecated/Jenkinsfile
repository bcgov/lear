// Edit your app's name below
def APP_NAME = 'coops-ui'

// Edit your environment TAG names below
def TAG_NAMES = ['dev', 'test', 'prod']

// You shouldn't have to edit these if you're following the conventions
def BUILD_CONFIG = "${APP_NAME}-inter"

//EDIT LINE BELOW (Change `IMAGESTREAM_NAME` so it matches the name of your *output*/deployable image stream.)
def IMAGESTREAM_NAME = 'coops-ui'

// you'll need to change this to point to your application component's folder within your repository
def CONTEXT_DIRECTORY = 'coops-ui'

// EDIT LINE BELOW (Add a reference to the CHAINED_BUILD_CONFIG)
def CHAINED_BUILD_CONFIG = 'coops-ui'

// The name of your deployment configuration; used to verify the deployment
def DEPLOYMENT_CONFIG_NAME= 'coops-ui'

// The namespace of you dev deployment environment.
def DEV_NAME_SPACE = 'gl2uos-dev'

@NonCPS
boolean triggerBuild(String contextDirectory) {
  // Determine if code has changed within the source context directory.
  def changeLogSets = currentBuild.changeSets
  def filesChangeCnt = 0
  for (int i = 0; i < changeLogSets.size(); i++) {
    def entries = changeLogSets[i].items
    for (int j = 0; j < entries.length; j++) {
      def entry = entries[j]
      def files = new ArrayList(entry.affectedFiles)
      for (int k = 0; k < files.size(); k++) {
        def file = files[k]
        def filePath = file.path
        if (filePath.contains(contextDirectory)) {
          filesChangeCnt = 1
          k = files.size()
          j = entries.length
        }
      }
    }
  }

  if ( filesChangeCnt < 1 ) {
    echo('The changes do not require a build.')
    return false
  }
  else {
    echo('The changes require a build.')
    return true
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

def run_pipeline = true

// build wasn't triggered by changes so check with user
if( !triggerBuild(CONTEXT_DIRECTORY) ) {
    stage('No changes. Run pipeline?') {
        try {
            timeout(time: 1, unit: 'DAYS') {
                input message: "Run pipeline?", id: "1234"//, submitter: 'admin,ljtrent-admin,thorwolpert-admin,rarmitag-admin,kialj876-admin,katiemcgoff-admin,waltermoar-admin'
            }
        } catch (Exception e) {
            run_pipeline = false;
        }
    }
}

if( run_pipeline ) {


    // create NodeJS pod to run verification steps
    def nodejs_label = "jenkins-nodejs-${UUID.randomUUID().toString()}"
    podTemplate(label: nodejs_label, name: nodejs_label, serviceAccount: 'jenkins', cloud: 'openshift', containers: [
        containerTemplate(
            name: 'jnlp',
            image: '172.50.0.2:5000/openshift/jenkins-slave-nodejs:8',
            resourceRequestCpu: '500m',
            resourceLimitCpu: '1000m',
            resourceRequestMemory: '1Gi',
            resourceLimitMemory: '2Gi',
            workingDir: '/tmp',
            command: '',
            args: '${computer.jnlpmac} ${computer.name}'
        )
    ])
    {
        node (nodejs_label) {
            checkout scm
            dir('coops-ui') {
                try {
                    sh '''
                        node -v
                        npm install
                    '''
                    /* TODO - these do not run correctly in pipeline
                    stage("Run Jest tests") {
                        def testResults = sh(script: "npm run test:unit-silent", returnStatus: true)

                        echo "Unit tests ran, returned ${testResults}"
                        if (testResults != 0) {
                            try {
                                timeout(time: 1, unit: 'DAYS') {
                                    input message: "Unit tests failed. Continue?", id: "1"
                                }
                            } catch (Exception e) {
                                error('Abort')
                            }
                        }
                    }
                    */
                    stage("Check code quality (lint)") {
                        def lintResults = sh(script: "npm run lint:nofix", returnStatus: true)

                        echo "Linter ran, returned ${lintResults}"
                        if (lintResults > 0) {
                            try {
                                timeout(time: 1, unit: 'DAYS') {
                                    input message: "Linter failed. Continue?", id: "2"
                                }
                            } catch (Exception e) {
                                error('Abort')
                            }
                        }
                    }

                } catch (Exception e) {
                    error('Failure')
                }

            }
        }
    }


  node {

    stage("Build ${BUILD_CONFIG}") {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Building the application artifacts ..."
            def build = openshift.selector("bc", "${BUILD_CONFIG}")
            build.startBuild("--wait=true").logs("-f")
          }
        }
      }
    }

    stage("Build ${IMAGESTREAM_NAME}") {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Building the ${IMAGESTREAM_NAME} image ..."
            def build = openshift.selector("bc", "${CHAINED_BUILD_CONFIG}")
            build.startBuild("--wait=true").logs("-f")

            def IMAGE_HASH_DEBUG = getImageTagHash("${IMAGESTREAM_NAME}")
            echo "Completed build, image is: ${IMAGE_HASH_DEBUG}"
          }
        }
      }
    }


    stage("Deploy ${TAG_NAMES[0]}") {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Tagging ${IMAGESTREAM_NAME} for deployment to ${TAG_NAMES[0]} ..."

            // Don't tag with BUILD_ID so the pruner can do it's job; it won't delete tagged images.
            // Tag the images for deployment based on the image's hash
            def IMAGE_HASH = getImageTagHash("${IMAGESTREAM_NAME}")
            echo "IMAGE_HASH: ${IMAGE_HASH}"
            openshift.tag("${IMAGESTREAM_NAME}@${IMAGE_HASH}", "${IMAGESTREAM_NAME}:${TAG_NAMES[0]}")
          }

          echo "Deployment Complete."
        }
      }
    }

    /* ZAP scan - commented out for now until can be implemented correctly
    stage('Trigger ZAP Scan') {
      script {
        openshift.withCluster() {
          openshift.withProject() {

            echo "Triggering an asynchronous ZAP Scan ..."
            def zapScan = openshift.selector("bc", "zap-pipeline")
            zapScan.startBuild()
          }
        }
      }
    }
    */

  }
}
else {
    stage('No Changes') {
      echo "No changes ..."
      currentBuild.result = 'SUCCESS'
    }
}
