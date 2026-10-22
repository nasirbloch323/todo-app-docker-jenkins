# Sehat Connect: district health department portal

A three-tier public health portal, packaged as containers, tested and shipped by a Jenkins pipeline using Docker Compose and Amazon ECR.

- Read **health notices** (alerts, advisories, vaccination reminders, camps)
- See **departments** and their OPD hours
- **Book an appointment** and get a reference number
- **Check appointment status** with the reference and phone number

```
Browser ──► frontend (Nginx) ──► backend (Flask + Gunicorn) ──► db (PostgreSQL)
            serves the site,     validates requests,             departments, notices,
            proxies /api         only tier that can              appointments
                                 reach the database
```

| Tier | Tech | Network |
|---|---|---|
| Presentation | Nginx, HTML, CSS, JS | `frontend-net` (publishes the site port) |
| Application | Flask, SQLAlchemy, Gunicorn | `frontend-net` and `backend-net` |
| Data | PostgreSQL 16, persistent volume | `backend-net` only (internal, no outside access) |

The status dots in the top bar show the live health of the three tiers.

This is a demonstration project. Departments and notices are sample content, and it is not a medical record system. Do not enter real patient data.

## Project structure

```
.
├── backend/             Flask API, tests, Dockerfile
├── frontend/            Nginx config, static site, Dockerfile
├── docker-compose.yml   The three services and two networks
├── Jenkinsfile          CI/CD pipeline
└── .env.example         Settings template
```

API:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Health of the API and database |
| `GET /api/departments` | Departments and OPD hours |
| `GET /api/notices` | Health notices, newest first |
| `GET /api/stats` | Department and appointment counts |
| `POST /api/appointments` | Book an appointment, returns a reference like `SH-000012` |
| `GET /api/appointments/<ref>?phone=...` | Check status (needs the matching phone number) |

## Run locally

Requires Docker with the Compose plugin.

```bash
cp .env.example .env        # then set POSTGRES_PASSWORD
docker compose up --build
```

Open http://localhost:8081. `docker compose down -v` also deletes the database volume.

Backend tests only (no Docker needed):

```bash
cd backend && pip install -r requirements.txt && pytest
```

## Customising

- **Emergency number, name, wording:** `frontend/public/index.html` (the helpline is `1122`).
- **Departments and notices:** the `SEED_DEPARTMENTS` and `SEED_NOTICES` lists in `backend/app.py`. They are added when the database is first created. To change them on a running system, edit the rows in PostgreSQL.
- **Colours and fonts:** the variables at the top of `frontend/public/css/style.css`.

## Pipeline

| Stage | What it does |
|---|---|
| Checkout | Gets the code |
| Backend tests | Runs pytest inside a `python:3.12-slim` container and publishes the JUnit report |
| Build images | `docker compose build`, tagging images with the ECR address and build number |
| Integration test | Starts the whole stack on port 18080, then checks the site, API, a real booking and a status lookup, and tears it down |
| Push to ECR | Creates the repositories if missing, pushes `:<build number>` and `:latest` |
| Deploy | Pulls the images from ECR and starts the stack with Compose on port 80 |

Jenkins needs only Docker. No Python and no AWS CLI are required on the server; the AWS CLI runs from the `amazon/aws-cli` image.

## Jenkins setup (Ubuntu), one time

### 1. Install Docker and let Jenkins use it

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 curl git
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

Check as the Jenkins user (both must work without errors):

```bash
sudo -u jenkins docker ps
sudo -u jenkins docker compose version
```

Membership of the `docker` group gives Jenkins root-level control of the machine, so use a dedicated server.

### 2. Create the ECR access key

In AWS IAM, create a user with this policy, then create an access key:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*" },
    { "Effect": "Allow",
      "Action": [
        "ecr:DescribeRepositories", "ecr:CreateRepository",
        "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage",
        "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "arn:aws:ecr:*:*:repository/sehat-*" }
  ]
}
```

### 3. Add two Jenkins credentials

Manage Jenkins, Credentials, Global, Add Credentials:

| ID (exact) | Kind | Value |
|---|---|---|
| `aws-ecr-creds` | Username with password | Username = AWS access key ID, Password = secret access key |
| `sehat-db-password` | Secret text | A strong database password of your choice |

### 4. Edit the Jenkinsfile

```groovy
AWS_ACCOUNT_ID     = '123456789012'
AWS_DEFAULT_REGION = 'us-east-1'
```

### 5. Create the job

1. New Item, name it, choose **Pipeline**.
2. Pipeline, Definition: `Pipeline script from SCM`, SCM: `Git`.
3. Repository URL: your repo. Branch: `*/main`. Script Path: `Jenkinsfile`.
4. Save, then **Build Now**.

When it finishes, the site is at `http://<server>:80` and the images are in ECR as `sehat-backend` and `sehat-frontend`.

## Ports

| Port | Used by |
|---|---|
| 80 | Deployed website (change `APP_PORT` in the Jenkinsfile) |
| 18080 | Temporary stack during the integration test |
| 8081 | Local `docker compose up` |
| 8080 | Jenkins |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `permission denied ... docker.sock` | `sudo usermod -aG docker jenkins && sudo systemctl restart jenkins` |
| `docker: 'compose' is not a docker command` | `sudo apt install -y docker-compose-v2` |
| `Could not find credentials entry with ID ...` | Create the credential with the exact ID from step 3 |
| `no basic auth credentials` or `AccessDenied` on push | Check the IAM policy, and the Account ID and region in the Jenkinsfile |
| `port is already allocated` on Deploy | Something else uses port 80. Change `APP_PORT` in the Jenkinsfile |
| Integration test fails | Open the archived `compose.log` in the build artifacts |
| Status dots show a red API or database | `docker compose -p sehat logs backend db` |

## Before real production use

- Serve the site over HTTPS (a load balancer or TLS-terminating proxy in front of port 80).
- Add rate limiting on the booking and status endpoints.
- Back up the `pgdata` volume.
- Use an IAM role instead of long-lived access keys where possible, and a dedicated Jenkins and Docker host.
