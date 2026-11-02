pipeline {
    agent any

    environment {
        PYTHONUNBUFFERED = '1'
        REGISTRY_NAME = 'python-crud-api'
        CONTAINER_NAME = 'production-api-container'
        PORT_MAPPING = '5000:5000'
        VOLUME_NAME = 'production-api-data'
        NETWORK_NAME = 'jenkins-net'
    }

    stages {
        stage('1. Checkout Code') {
            steps {
                echo 'Mengambil source code dari GitHub'
                checkout scm
            }
        }

        stage('2. Code Syntax Verification') {
            steps {
                sh 'python3 -m py_compile app.py'
            }
        }

        stage('3. Automated Tests') {
            steps {
                sh 'python3 -m unittest discover -s tests -v'
            }
        }

        stage('4. Build Docker Image') {
            steps {
                script {
                    env.GIT_SHORT_SHA = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }
                sh '''
                    docker build \
                        -t ${REGISTRY_NAME}:${BUILD_NUMBER} \
                        -t ${REGISTRY_NAME}:${GIT_SHORT_SHA} \
                        -t ${REGISTRY_NAME}:latest .
                '''
            }
        }

        stage('5. Automated Deployment') {
            steps {
                sh '''
                    docker stop ${CONTAINER_NAME} || true
                    docker rm ${CONTAINER_NAME} || true
                    docker volume create ${VOLUME_NAME}
                    docker run -d \
                        --name ${CONTAINER_NAME} \
                        --network ${NETWORK_NAME} \
                        --restart unless-stopped \
                        -p ${PORT_MAPPING} \
                        -v ${VOLUME_NAME}:/var/lib/backend_data \
                        ${REGISTRY_NAME}:latest
                '''
            }
        }

        // Jenkins berjalan di dalam container, sehingga localhost di sini
        // adalah container Jenkins. API dijangkau lewat nama container.
        stage('6. Health Check') {
            steps {
                sh '''
                    for attempt in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS http://${CONTAINER_NAME}:5000/health; then
                            echo
                            docker logs --tail 20 ${CONTAINER_NAME}
                            exit 0
                        fi
                        echo "Menunggu API siap (percobaan ${attempt}/10)"
                        sleep 2
                    done
                    docker logs --tail 20 ${CONTAINER_NAME}
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully.'
        }
        failure {
            echo 'Pipeline failed. Inspect Console Output.'
        }
    }
}
