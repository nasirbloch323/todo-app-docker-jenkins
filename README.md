# Sehat Connect

A three-tier health department web portal with an automated CI/CD pipeline. Patients can read health notices, browse departments and OPD hours, book appointments and check their status. The whole system runs in containers, is tested and built by **Jenkins**, stored in **Amazon ECR** and deployed with **Docker Compose** on an **AWS EC2 (Ubuntu)** server.

![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Jenkins](https://img.shields.io/badge/CI%2FCD-Jenkins-D24939?logo=jenkins&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-ECR%20%7C%20EC2-FF9900?logo=amazonaws&logoColor=white)
![Flask](https://img.shields.io/badge/Backend-Flask-000000?logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Nginx](https://img.shields.io/badge/Frontend-Nginx-009639?logo=nginx&logoColor=white)

---

## Table of contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Tech stack](#tech-stack)
4. [Project structure](#project-structure)
5. [API reference](#api-reference)
6. [Setup guide: 11 steps](#setup-guide-11-steps)
7. [Pipeline stages](#pipeline-stages)
8. [Ports](#ports)
9. [Viewing and managing stored data](#viewing-and-managing-stored-data)
10. [Troubleshooting](#troubleshooting)
11. [Security notes](#security-notes)
12. [Customising](#customising)

---

## Features

- **Health notices:** alerts, advisories, vaccination reminders and camps, newest first
- **Departments:** every department with its OPD hours, and a one-click "Book here" button
- **Appointment booking:** name, phone, department, preferred date and reason, with a reference number such as `SH-000012`
- **Status check:** look up an appointment with the reference and the phone number used to book
- **Live system status:** the top bar shows the health of the Web, API and Database tiers
- **Validation on both sides:** in the browser and again in the API
- **Responsive design:** works on phones, tablets and desktops
- **Automated delivery:** every push is tested, built, pushed to ECR and deployed

## Architecture

```
                       Docker Compose on AWS EC2
 ┌───────────────────────────────────────────────────────────────┐
 │                                                               │
 │  Browser ──► frontend (Nginx) ──► backend (Flask) ──► db      │
 │              port 80              port 5000         (Postgres)│
 │              serves the site,     validates and     stores    │
 │              proxies /api         talks to the DB   the data  │
 │                                                               │
 └───────────────────────────────────────────────────────────────┘

 Git push ──► Jenkins ──► test ──► build ──► Amazon ECR ──► deploy
```

| Tier | Technology | Network |
|---|---|---|
| Presentation | Nginx, HTML, CSS, JavaScript | `frontend-net` (publishes the site port) |
| Application | Flask, SQLAlchemy, Gunicorn | `frontend-net` and `backend-net` |
| Data | PostgreSQL 16 with a persistent volume | `backend-net` only (internal, no outside access) |

The database sits on a private network. Only the backend can reach it, and its port is never published to the host.

## Tech stack

| Area | Tools |
|---|---|
| Frontend | HTML5, CSS3, vanilla JavaScript, Nginx |
| Backend | Python 3.12, Flask, SQLAlchemy, Gunicorn |
| Database | PostgreSQL 16 |
| Testing | pytest (18 tests) |
| Containers | Docker, Docker Compose |
| CI/CD | Jenkins (declarative pipeline) |
| Registry | Amazon ECR |
| Hosting | AWS EC2, Ubuntu |

## Project structure

```
.
├── backend/
│   ├── app.py              Flask app, models and routes
│   ├── init_db.py          Waits for the DB, creates tables, seeds data
│   ├── wsgi.py             Gunicorn entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/test_api.py   pytest tests
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf          Static files and /api reverse proxy
│   └── public/             index.html, css/style.css, js/app.js
├── docker-compose.yml      Three services, two networks, one volume
├── Jenkinsfile             Declarative CI/CD pipeline
├── .env.example            Settings template
└── README.md
```

## API reference

| Method and path | Description |
|---|---|
| `GET /api/health` | Health of the API and the database (`503` if the database is down) |
| `GET /api/departments` | Departments and OPD hours |
| `GET /api/notices` | Health notices, newest first |
| `GET /api/stats` | Number of departments and appointments |
| `POST /api/appointments` | Book an appointment. Returns `201` and a reference, or `400` with field errors |
| `GET /api/appointments/<ref>?phone=...` | Appointment status. Returns `404` for a wrong reference or phone number |

Example booking request:

```bash
curl -X POST http://localhost:8081/api/appointments \
  -H "Content-Type: application/json" \
  -d '{"name":"Ayesha Khan","phone":"0300 1234567","department":"general","date":"2026-11-05","note":"Fever"}'
```

---

## Setup guide: 11 steps

These steps take a fresh AWS EC2 Ubuntu server to a fully automated pipeline. Do them in order.

### Step 1: Prepare the server

Use an EC2 Ubuntu instance with **at least 2 GB of RAM**. Check it:

```bash
free -h
```

If total memory is under 2 GB, add swap so builds do not stall:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

In the EC2 **Security Group**, add these inbound rules:

| Port | Purpose | Source |
|---|---|---|
| 22 | SSH | My IP |
| 8080 | Jenkins | My IP |
| 80 | Website | Anywhere (`0.0.0.0/0`) |
| 8081 | Local testing (Step 4) | My IP |

### Step 2: Install Docker and tools

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 curl git rsync
sudo systemctl enable --now docker
docker --version && docker compose version
```

### Step 3: Get the code and configure it

```bash
git clone https://github.com/<your-username>/sehat-connect.git
cd sehat-connect
```

Create the settings file. `.env.example` is a hidden file and is easy to miss when copying, so you can also create `.env` directly:

```bash
cat > .env <<'EOF'
POSTGRES_USER=sehat
POSTGRES_DB=sehat
POSTGRES_PASSWORD=choose-a-strong-password
FRONTEND_PORT=8081
EOF
```

`POSTGRES_PASSWORD` must not be empty, otherwise Compose stops with `required variable POSTGRES_PASSWORD is missing a value`. The `.env` file is git-ignored and is never committed.

### Step 4: Run the stack once by hand

```bash
sudo docker compose up --build -d
sudo docker compose ps
curl http://localhost:8081/api/health
```

All three containers (`db`, `backend`, `frontend`) should show `healthy`, and the health call should return `{"database":"up","status":"ok",...}`. Open `http://<EC2-public-IP>:8081` in a browser. When you are done, stop it so it does not clash with the pipeline:

```bash
sudo docker compose down
```

### Step 5: Push the project to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/sehat-connect.git
git push -u origin main
```

`Jenkinsfile` must sit in the repository **root**, next to `docker-compose.yml`.

### Step 6: Install Jenkins

```bash
sudo apt install -y fontconfig openjdk-17-jre

sudo wget -O /usr/share/keyrings/jenkins-keyring.asc \
  https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" | \
  sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null

sudo apt update
sudo apt install -y jenkins
sudo systemctl enable --now jenkins
```

Open `http://<EC2-public-IP>:8080`. Get the first-run password with:

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

Choose **Install suggested plugins** and create your admin user. If the repository key link changes, use the Debian/Ubuntu instructions on `pkg.jenkins.io`.

### Step 7: Give Jenkins access to Docker

```bash
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins

sudo -u jenkins docker ps
sudo -u jenkins docker compose version
```

Both checks must run without errors. Members of the `docker` group have root-level control of the machine, so use a dedicated server for Jenkins.

### Step 8: Create the AWS access for ECR

1. In **IAM**, choose **Users, Create user** and name it `jenkins-ecr`.
2. Add this inline policy (JSON):

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

3. Open **Security credentials, Create access key** and save the **Access key ID** and **Secret access key**. The secret is shown only once.
4. Note your **12-digit AWS Account ID** and your **region** (the same region as your EC2 server).

The ECR repositories `sehat-backend` and `sehat-frontend` are created automatically by the pipeline.

### Step 9: Add the Jenkins credentials

Go to **Manage Jenkins, Credentials, System, Global credentials, Add Credentials**. The **Kind** must be exactly as shown, and it cannot be changed later (delete and recreate if it is wrong).

| ID (exact) | Kind | Fields |
|---|---|---|
| `aws-ecr-creds` | **Username with password** | Username = Access key ID, Password = Secret access key |
| `sehat-db-password` | **Secret text** | Secret = the database password |

### Step 10: Configure the Jenkinsfile and create the job

Edit the top of `Jenkinsfile`:

```groovy
AWS_ACCOUNT_ID     = '123456789012'   // your 12-digit account ID
AWS_DEFAULT_REGION = 'us-east-1'      // your region
```

Commit and push:

```bash
git add Jenkinsfile && git commit -m "Set AWS account and region" && git push
```

In Jenkins, create the job:

1. **New Item**, name `sehat-connect`, type **Pipeline**.
2. **Definition:** `Pipeline script from SCM`.
3. **SCM:** `Git`, **Repository URL:** your repository. For a private repository, add a GitHub username and Personal Access Token as credentials.
4. **Branch Specifier:** `*/main`. **Script Path:** `Jenkinsfile`.
5. Save.

Optional: in **Build Triggers** enable **Poll SCM** with `H/2 * * * *` to build automatically after every push.

### Step 11: Run the pipeline and verify

Press **Build Now**. The first build takes a few minutes because images are downloaded. Every stage in **Stage View** must turn green:

`Checkout → Backend tests → Build images → Integration test → Push to ECR → Deploy`

Then verify:

```bash
sudo docker ps                              # db, backend, frontend running
curl http://localhost/api/health            # {"database":"up",...}
```

- Open `http://<EC2-public-IP>` in a browser (port 80, no port number).
- In the AWS Console, open **ECR, Repositories**: `sehat-backend` and `sehat-frontend` hold images tagged with the build number and `latest`.
- Make a booking on the site and confirm it is stored (see the next section).

---

## Pipeline stages

| Stage | What it does |
|---|---|
| Checkout | Gets the code from Git |
| Backend tests | Runs pytest inside a `python:3.12-slim` container and publishes the JUnit report |
| Build images | `docker compose build`, tagging images with the ECR address and build number |
| Integration test | Starts the full stack on port 18080, checks the site, API, a real booking and a status lookup, then removes it |
| Push to ECR | Creates the repositories if missing, pushes `:<build number>` and `:latest` |
| Deploy | Pulls the images from ECR and starts the stack with Compose on port 80 |

Jenkins needs only Docker. No Python and no AWS CLI are installed on the server; the AWS CLI runs from the `amazon/aws-cli` image.

## Ports

| Port | Used by |
|---|---|
| 80 | Deployed website (change `APP_PORT` in the `Jenkinsfile` if it is taken) |
| 8080 | Jenkins |
| 8081 | Manual `docker compose up` (Step 4) |
| 18080 | Temporary stack during the integration test |

## Viewing and managing stored data

Run these from the project folder while the stack is running. Replace `sehat` if you changed `POSTGRES_USER` or `POSTGRES_DB`.

**List appointments with department names:**

```bash
sudo docker compose exec db psql -U sehat -d sehat -c "
SELECT a.reference, a.name, a.phone, d.name AS department,
       a.preferred_date, a.status, a.created_at
FROM appointments a JOIN departments d ON d.id = a.department_id
ORDER BY a.id DESC;"
```

**Open an interactive SQL shell:**

```bash
sudo docker compose exec db psql -U sehat -d sehat
```

Handy commands inside it: `\dt` (tables), `SELECT * FROM notices;`, `\q` (quit).

**View in a browser with Adminer (through an SSH tunnel):**

```bash
cat > docker-compose.admin.yml <<'EOF'
services:
  adminer:
    image: adminer:4
    restart: unless-stopped
    ports:
      - "127.0.0.1:8082:8080"
    networks: [backend-net, frontend-net]
    depends_on: [db]
EOF

sudo docker compose -f docker-compose.yml -f docker-compose.admin.yml up -d
```

On your own computer, open the tunnel and then browse to `http://localhost:8082`:

```bash
ssh -i your-key.pem -L 8082:127.0.0.1:8082 ubuntu@<EC2-public-IP>
```

Login: System `PostgreSQL`, Server `db`, plus the user, password and database from your `.env`. Do **not** open port 8082 in the Security Group.

**Data is kept in the `pgdata` volume.** `docker compose down` keeps it; `docker compose down -v` deletes the database.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `required variable POSTGRES_PASSWORD is missing a value` | Create `.env` with a non-empty `POSTGRES_PASSWORD` (Step 3) |
| Site does not open from the browser | Open the port in the EC2 Security Group and use `http://<public-IP>:<port>`, not the private `172.31.x.x` address |
| `permission denied ... docker.sock` in Jenkins | Repeat Step 7 |
| `docker: 'compose' is not a docker command` | `sudo apt install -y docker-compose-v2` |
| `Credentials 'sehat-db-password' is of type 'Username with password' where ... StringCredentials was expected` | Delete the credential and recreate it with Kind **Secret text** (Step 9) |
| `Could not find credentials entry with ID ...` | The ID must match exactly: `aws-ecr-creds` and `sehat-db-password` |
| `no basic auth credentials` or `AccessDenied` on push | Check the IAM policy, the account ID and the region in the `Jenkinsfile` |
| `port is already allocated` on Deploy | Another service uses port 80. Stop it or change `APP_PORT` in the `Jenkinsfile` |
| Integration test fails | Open the archived `compose.log` in the build artifacts |
| Status dots show a red API or Database | `sudo docker compose -p sehat logs backend db` |
| Build hangs or the server freezes | Not enough memory. Add swap (Step 1) or use a larger instance |

## Security notes

- The database is on an internal network and its port is never published.
- Secrets live in Jenkins credentials and the git-ignored `.env`; none are committed.
- The database password is injected at deploy time, and the CI stack uses a throw-away password.
- The IAM policy is limited to the `sehat-*` ECR repositories.
- The appointment lookup returns the same answer for "not found" and "wrong phone", so references cannot be probed.
- Before wider production use: serve the site over HTTPS, add rate limiting to the booking and status endpoints, back up the `pgdata` volume, and prefer an IAM role over long-lived access keys.

## Customising

- **Name, helpline number and wording:** `frontend/public/index.html`
- **Colours and fonts:** the variables at the top of `frontend/public/css/style.css`
- **Departments and notices:** `SEED_DEPARTMENTS` and `SEED_NOTICES` in `backend/app.py`. They are inserted when the database is first created. Replace the sample text with the real content before going live, and edit rows in PostgreSQL to change them on a running system.

## Run the tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

## Author

Built and delivered by **NASIR MEHMOOD**, junior freelance DevOps and web developer.
Open to work and happy to connect: [nasirbloch323@gmail.com]
