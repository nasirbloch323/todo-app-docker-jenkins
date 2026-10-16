from flask import Flask, render_template, request, redirect, url_for, flash

SERVICES = [
    {"slug": "web", "title": "Web applications",
     "text": "Dashboards, portals and internal tools built on Flask and modern front ends, ready for real users.",
     "points": ["Flask and REST APIs", "Responsive interfaces", "Authentication and roles"]},
    {"slug": "devops", "title": "CI/CD and automation",
     "text": "Jenkins pipelines that build, test and ship your code the same way every time.",
     "points": ["Jenkins pipelines", "Docker images", "Automated deployments"]},
    {"slug": "qa", "title": "Testing and quality",
     "text": "Unit, API and UI tests that run on every commit, so problems show up before your customers see them.",
     "points": ["pytest suites", "Selenium UI checks", "Load and security testing"]},
    {"slug": "support", "title": "Maintenance and support",
     "text": "Monitoring, updates and fixes after launch, with clear response times.",
     "points": ["Uptime monitoring", "Dependency updates", "Priority bug fixes"]},
]

STEPS = [
    ("Discover", "We agree on goals, users and scope in a short call."),
    ("Build", "Weekly releases you can open and click through."),
    ("Test", "Every change passes automated checks before it merges."),
    ("Launch", "One-click deploys, with a rollback ready."),
]


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-in-production"

    @app.route("/")
    def home():
        return render_template("index.html", services=SERVICES, steps=STEPS)

    @app.route("/services")
    def services():
        return render_template("services.html", services=SERVICES)

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            message = request.form.get("message", "").strip()
            if not name or "@" not in email or len(message) < 10:
                flash("Please enter your name, a valid email and a message of at least 10 characters.", "error")
                return render_template("contact.html", form=request.form), 400
            flash(f"Thanks {name}, we received your message and will reply by email.", "success")
            return redirect(url_for("contact"))
        return render_template("contact.html", form={})

    @app.route("/health")
    def health():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
