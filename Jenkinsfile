pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    environment {
        // ---- EDIT THESE TWO ----
        AWS_ACCOUNT_ID     = '123456789012'
        AWS_DEFAULT_REGION = 'us-east-1'

        ECR_REGISTRY   = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"
        BACKEND_IMAGE  = "${ECR_REGISTRY}/sehat-backend:${BUILD_NUMBER}"
        FRONTEND_IMAGE = "${ECR_REGISTRY}/sehat-frontend:${BUILD_NUMBER}"
        APP_VERSION    = "${BUILD_NUMBER}"

        // Throw-away values used only for the CI build and test stack.
        // The real password is injected from Jenkins credentials in the Deploy stage.
        POSTGRES_USER     = 'sehat'
        POSTGRES_DB       = 'sehat'
        POSTGRES_PASSWORD = 'ci_only_password'

        CI_PROJECT = "sehat-ci-${BUILD_NUMBER}"
        CI_PORT    = '18080'
        APP_PORT   = '80'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Backend tests') {
            steps {
                sh '''
                    mkdir -p reports
                    docker run --rm \
                        --user "$(id -u):$(id -g)" \
                        -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 \
                        -v "$PWD/backend":/app:ro \
                        -v "$PWD/reports":/reports \
                        -w /app python:3.12-slim \
                        sh -c "pip install --no-cache-dir --user -q -r requirements.txt && python -m pytest -q -p no:cacheprovider --junitxml=/reports/junit.xml"
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                }
            }
        }

        stage('Build images') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Integration test') {
            steps {
                sh '''
                    export FRONTEND_PORT=$CI_PORT
                    docker compose -p $CI_PROJECT up -d --no-build --wait --wait-timeout 180

                    BASE=http://127.0.0.1:$CI_PORT
                    VISIT=$(date -d '+3 days' +%F)

                    curl --fail -s $BASE/healthz
                    curl --fail -s $BASE/api/health
                    curl --fail -s $BASE/ > /dev/null
                    curl --fail -s $BASE/api/departments > /dev/null
                    curl --fail -s $BASE/api/notices > /dev/null

                    RESPONSE=$(curl --fail -s -X POST -H "Content-Type: application/json" \
                        -d '{"name":"CI Patient","phone":"03001234567","department":"general","date":"'$VISIT'","note":"CI test"}' \
                        $BASE/api/appointments)
                    echo "$RESPONSE"

                    REF=$(echo "$RESPONSE" | grep -o '"reference":"[^"]*"' | cut -d'"' -f4)
                    test -n "$REF"
                    curl --fail -s -G --data-urlencode "phone=03001234567" $BASE/api/appointments/$REF
                    echo ""
                    echo "Integration test passed"
                '''
            }
            post {
                always {
                    sh '''
                        export FRONTEND_PORT=$CI_PORT
                        docker compose -p $CI_PROJECT logs --no-color > compose.log 2>&1 || true
                        docker compose -p $CI_PROJECT down -v --remove-orphans || true
                    '''
                    archiveArtifacts artifacts: 'compose.log', allowEmptyArchive: true
                }
            }
        }

        stage('Push to ECR') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'aws-ecr-creds',
                                                  usernameVariable: 'AWS_ACCESS_KEY_ID',
                                                  passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
                    sh '''
                        aws() {
                            docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION amazon/aws-cli "$@"
                        }

                        for repo in sehat-backend sehat-frontend; do
                            aws ecr describe-repositories --repository-names $repo > /dev/null 2>&1 || \
                                aws ecr create-repository --repository-name $repo \
                                    --image-scanning-configuration scanOnPush=true > /dev/null
                        done

                        aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY

                        docker push $BACKEND_IMAGE
                        docker push $FRONTEND_IMAGE

                        docker tag $BACKEND_IMAGE  $ECR_REGISTRY/sehat-backend:latest
                        docker tag $FRONTEND_IMAGE $ECR_REGISTRY/sehat-frontend:latest
                        docker push $ECR_REGISTRY/sehat-backend:latest
                        docker push $ECR_REGISTRY/sehat-frontend:latest
                    '''
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([
                    usernamePassword(credentialsId: 'aws-ecr-creds',
                                     usernameVariable: 'AWS_ACCESS_KEY_ID',
                                     passwordVariable: 'AWS_SECRET_ACCESS_KEY'),
                    string(credentialsId: 'sehat-db-password', variable: 'POSTGRES_PASSWORD')
                ]) {
                    sh '''
                        aws() {
                            docker run --rm -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_DEFAULT_REGION amazon/aws-cli "$@"
                        }

                        aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY

                        export FRONTEND_PORT=$APP_PORT
                        docker compose -p sehat pull backend frontend
                        docker compose -p sehat up -d --no-build --wait --wait-timeout 180

                        curl --fail -s http://127.0.0.1:$APP_PORT/api/health
                        echo ""
                        echo "Deployed build $BUILD_NUMBER at http://localhost:$APP_PORT"
                        docker image prune -f > /dev/null
                    '''
                }
            }
        }
    }

    post {
        success { echo "Build ${BUILD_NUMBER} passed and was deployed." }
        failure { echo 'Build failed. Check the stage logs above.' }
        always  { sh 'docker logout $ECR_REGISTRY || true' }
        cleanup { cleanWs() }
    }
}
