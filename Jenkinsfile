pipeline {
    agent none
    options {
        disableResume()
    }
    stages {
        stage('Hello!') {
            agent { label 'master' }
            steps {
                echo "Hello world ..."
            }
        }
    }
}