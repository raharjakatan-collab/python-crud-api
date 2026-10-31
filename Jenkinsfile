pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                echo 'Mengambil source code dari GitHub'
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Membangun Docker Image'
                sh 'docker build -t python-crud-api:latest .'
            }
        }

        stage('Deploy') {
            steps {
                echo 'Menjalankan aplikasi'
                sh '''
                    docker stop python-crud-container || true
                    docker rm python-crud-container || true
                    docker run -d --name python-crud-container -p 5000:5000 python-crud-api:latest
                '''
            }
        }
    }
}