# Tarteeb

A small, professional marketing website for a software studio, built with Flask and delivered through a Jenkins CI/CD pipeline.

The project has two goals: a clean, responsive website, and a complete pipeline that installs, tests, smoke-tests and deploys it on every build.

## Features

- Three pages: Home, Services and Contact, plus a custom 404 page
- Contact form with client-side and server-side validation
- `/health` endpoint that returns `{"status": "ok"}`, used by the pipeline to check the app is running
- Responsive layout, visible keyboard focus and reduced-motion support
- Automated tests with pytest
- Declarative Jenkins pipeline with automatic deployment as a systemd service

## Project structure

```
tarteeb/
├── app.py               Flask app and routes (create_app factory)
├── requirements.txt     Flask, pytest, gunicorn
├── pytest.ini           Lets pytest import app.py
├── Jenkinsfile          Declarative Jenkins pipeline
├── templates/
│   ├── base.html        Shared layout (navbar and footer)
│   ├── index.html       Home page
│   ├── services.html    Services page
│   ├── contact.html     Contact form
│   └── 404.html         Not found page
├── static/
│   ├── css/style.css    All styling
│   └── js/main.js       Mobile menu, pipeline animation, form check
└── tests/
    └── test_app.py      pytest tests
```

## Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Home page |
| `/services` | GET | Services page |
| `/contact` | GET, POST | Contact form. Invalid input returns status 400 |
| `/health` | GET | Health check, returns `{"status": "ok"}` |

The contact form currently shows a confirmation message only. It does not send email or store messages.

## Run locally

Requirements: Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

## Run the tests

```bash
pytest
```

The suite checks that every page loads, that unknown URLs return 404, and that the contact form accepts valid input and rejects invalid input.

## CI/CD with Jenkins

The `Jenkinsfile` defines these stages:

1. **Checkout**: pulls the code from Git
2. **Install**: creates a virtual environment and installs dependencies
3. **Unit tests**: runs pytest and publishes the JUnit report
4. **Smoke test**: starts the app with gunicorn on port 5001 and checks `/health` and `/`
5. **Deploy**: copies the project to `/opt/tarteeb`, installs dependencies and restarts the `tarteeb` systemd service

After a successful build the site runs at http://localhost:5000.

### One-time server setup (Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl git rsync

sudo mkdir -p /opt/tarteeb
sudo chown -R jenkins:jenkins /opt/tarteeb

sudo tee /etc/systemd/system/tarteeb.service > /dev/null <<'EOF'
[Unit]
Description=Tarteeb Flask site
After=network.target

[Service]
User=jenkins
WorkingDirectory=/opt/tarteeb
ExecStart=/opt/tarteeb/.venv/bin/gunicorn -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/sudoers.d/jenkins-tarteeb > /dev/null <<'EOF'
jenkins ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart tarteeb, /bin/systemctl restart tarteeb
EOF
sudo chmod 440 /etc/sudoers.d/jenkins-tarteeb
sudo visudo -c

sudo systemctl daemon-reload
sudo systemctl enable tarteeb
```

The sudoers rule lets the `jenkins` user restart this one service and nothing else.

### Create the Jenkins job

1. Choose **New Item**, enter a name and select **Pipeline**.
2. Under **Pipeline**, set **Definition** to `Pipeline script from SCM`.
3. Set **SCM** to `Git` and enter the repository URL.
4. Set **Branch Specifier** to `*/main` and **Script Path** to `Jenkinsfile`.
5. Save, then choose **Build Now**.

To build automatically on new commits, enable **Poll SCM** in the job's build triggers with the schedule `H/2 * * * *`.

## Ports

| Port | Used by |
|---|---|
| 5000 | The deployed website (systemd service), and `python app.py` locally |
| 5001 | Temporary app started by the smoke test stage |
| 8080 | Jenkins |

## Troubleshooting

| Problem | Fix |
|---|---|
| `rsync: mkdir "/opt/tarteeb" failed: Permission denied` | `sudo chown -R jenkins:jenkins /opt/tarteeb` |
| `sudo: ... can't do that` or password required | Recreate `/etc/sudoers.d/jenkins-tarteeb` and run `sudo visudo -c` |
| `Unit tarteeb.service not found` | Create the service file, then `sudo systemctl daemon-reload` |
| Smoke test cannot connect | Make sure `gunicorn` is in `requirements.txt`, and read `app.log` in the build artifacts |
| Site does not open after deploy | `sudo systemctl status tarteeb` and `sudo journalctl -u tarteeb -n 30 --no-pager` |

## Before going to production

- Replace the placeholder `SECRET_KEY` in `app.py` with a secret value from an environment variable.
- Connect the contact form to email or a database.
- Put the app behind a reverse proxy such as Nginx and serve it over HTTPS.
