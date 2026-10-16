pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        DEPLOY_DIR = '/opt/tarteeb'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Unit tests') {
            steps {
                sh '''
                    . .venv/bin/activate
                    pytest --junitxml=reports/junit.xml
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                }
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    . .venv/bin/activate
                    gunicorn -b 127.0.0.1:5001 app:app > app.log 2>&1 &
                    echo $! > app.pid

                    for i in $(seq 1 15); do
                        if curl --fail -s http://127.0.0.1:5001/health > /dev/null; then
                            echo "App is up"
                            curl --fail -s http://127.0.0.1:5001/ > /dev/null
                            exit 0
                        fi
                        sleep 1
                    done

                    echo "App did not start. app.log:"
                    cat app.log
                    exit 1
                '''
            }
            post {
                always {
                    sh 'kill $(cat app.pid) 2>/dev/null || true'
                    archiveArtifacts artifacts: 'app.log', allowEmptyArchive: true
                }
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    rsync -a --delete --exclude .venv --exclude .git --exclude reports ./ $DEPLOY_DIR/
                    python3 -m venv $DEPLOY_DIR/.venv
                    $DEPLOY_DIR/.venv/bin/pip install -r $DEPLOY_DIR/requirements.txt
                    sudo systemctl restart tarteeb

                    for i in $(seq 1 15); do
                        if curl --fail -s http://127.0.0.1:5000/health; then
                            echo ""
                            echo "Deployed: http://localhost:5000"
                            exit 0
                        fi
                        sleep 1
                    done

                    echo "Service did not come up"
                    sudo systemctl status tarteeb --no-pager || true
                    exit 1
                '''
            }
        }
    }

    post {
        success { echo 'Build passed and site deployed on port 5000.' }
        failure { echo 'Build failed. Check the stage logs above.' }
        cleanup { cleanWs() }
    }
}
