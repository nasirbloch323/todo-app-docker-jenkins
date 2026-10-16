pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Unit tests') {
            steps {
                sh '. .venv/bin/activate && pytest --junitxml=reports/junit.xml'
            }
            post {
                always { junit allowEmptyResults: true, testResults: 'reports/junit.xml' }
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python app.py > app.log 2>&1 &
                    echo $! > app.pid
                    sleep 5
                    curl --fail http://127.0.0.1:5000/health
                '''
            }
            post {
                always { sh 'kill $(cat app.pid) 2>/dev/null || true' }
            }
        }
    }
}
