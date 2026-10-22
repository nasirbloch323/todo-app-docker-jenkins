"""Sehat Connect API: the application tier (Flask + SQLAlchemy + PostgreSQL)."""
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from flask import Flask, jsonify, request
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, create_engine, func, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

VERSION = os.getenv("APP_VERSION", "dev")
MAX_DAYS_AHEAD = 60

SEED_DEPARTMENTS = [
    ("general", "General Medicine", "Check-ups, fever, blood pressure, diabetes and everyday illness.", "Mon to Sat, 8:00 to 14:00"),
    ("maternal", "Maternal and Child Health", "Antenatal care, safe delivery, newborn and child check-ups.", "Mon to Sat, 8:00 to 13:00"),
    ("immunisation", "Immunisation", "Routine childhood and adult vaccines, with records kept for you.", "Mon to Sat, 8:00 to 15:00"),
    ("dental", "Dental Care", "Examinations, fillings, extractions and oral health advice.", "Mon to Fri, 9:00 to 14:00"),
    ("lab", "Laboratory and Diagnostics", "Blood tests, urine tests and X-ray, with reports within the day.", "Daily, 7:30 to 18:00"),
    ("emergency", "Emergency and Trauma", "Round-the-clock care for accidents and urgent medical problems.", "Open 24 hours"),
]

SEED_NOTICES = [
    ("alert", "Heat wave precautions",
     "Drink water often, avoid going out between noon and 4 pm, and check on elderly neighbours. Seek care for dizziness or very high temperature."),
    ("advisory", "Dengue prevention",
     "Remove standing water from coolers, tyres and pots every week. Use mosquito repellent and wear full sleeves at dusk."),
    ("vaccination", "Routine vaccination reminder",
     "Check your child's immunisation card. Missed doses can be caught up at any immunisation counter during OPD hours."),
    ("camp", "Free screening camps",
     "Blood pressure and diabetes screening is available for adults over 30. Ask at the General Medicine counter for the next camp."),
]


class Base(DeclarativeBase):
    pass


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    opd_hours: Mapped[str] = mapped_column(String(80))
    position: Mapped[int] = mapped_column(default=0)


class Notice(Base):
    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    preferred_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    department: Mapped[Department] = relationship()


def database_url():
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    return URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "sehat"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "db"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "sehat"),
    )


def make_engine(url):
    if make_url(url).get_backend_name() == "sqlite":
        return create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


def init_db(engine):
    """Create tables and seed sample content (safe to run repeatedly)."""
    Base.metadata.create_all(engine)
    with sessionmaker(engine)() as s:
        if s.scalar(select(func.count()).select_from(Department)) == 0:
            for i, (slug, name, desc, hours) in enumerate(SEED_DEPARTMENTS):
                s.add(Department(slug=slug, name=name, description=desc, opd_hours=hours, position=i))
        if s.scalar(select(func.count()).select_from(Notice)) == 0:
            now = datetime.now(timezone.utc)
            for i, (cat, title, body) in enumerate(SEED_NOTICES):
                s.add(Notice(category=cat, title=title, body=body, published_at=now - timedelta(days=i)))
        s.commit()


def _clean(value):
    return value.strip() if isinstance(value, str) else ""


def _digits(value):
    return re.sub(r"\D", "", value or "")


def create_app(db_url=None):
    app = Flask(__name__)
    engine = make_engine(db_url or database_url())
    Session = sessionmaker(engine, expire_on_commit=False)
    app.config["ENGINE"] = engine

    @app.get("/api/health")
    def health():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db = "up"
        except Exception:
            db = "down"
        ok = db == "up"
        return jsonify(status="ok" if ok else "degraded", database=db, version=VERSION), (200 if ok else 503)

    @app.get("/api/departments")
    def departments():
        with Session() as s:
            rows = s.scalars(select(Department).order_by(Department.position)).all()
        return jsonify([
            {"slug": r.slug, "name": r.name, "description": r.description, "opd_hours": r.opd_hours}
            for r in rows
        ])

    @app.get("/api/notices")
    def notices():
        with Session() as s:
            rows = s.scalars(select(Notice).order_by(Notice.published_at.desc())).all()
        return jsonify([
            {"category": r.category, "title": r.title, "body": r.body,
             "published_at": r.published_at.isoformat()} for r in rows
        ])

    @app.get("/api/stats")
    def stats():
        with Session() as s:
            return jsonify(
                departments=s.scalar(select(func.count()).select_from(Department)),
                appointments=s.scalar(select(func.count()).select_from(Appointment)),
            )

    @app.post("/api/appointments")
    def book():
        data = request.get_json(silent=True) or {}
        name = _clean(data.get("name"))
        phone = _clean(data.get("phone"))
        slug = _clean(data.get("department"))
        raw_date = _clean(data.get("date"))
        note = _clean(data.get("note"))
        errors = {}

        if not 1 <= len(name) <= 100:
            errors["name"] = "Enter the patient's name (up to 100 characters)."
        if not (re.fullmatch(r"\+?[0-9\s-]+", phone) and 7 <= len(_digits(phone)) <= 15 and len(phone) <= 30):
            errors["phone"] = "Enter a valid phone number."
        if len(note) > 500:
            errors["note"] = "Note must be 500 characters or fewer."

        when = None
        try:
            when = date.fromisoformat(raw_date)
            today = date.today()
            if not today <= when <= today + timedelta(days=MAX_DAYS_AHEAD):
                errors["date"] = f"Choose a date within the next {MAX_DAYS_AHEAD} days."
        except ValueError:
            errors["date"] = "Choose a valid date."

        with Session() as s:
            dept = s.scalar(select(Department).where(Department.slug == slug))
            if dept is None:
                errors["department"] = "Choose a department."
            if errors:
                return jsonify(errors=errors), 400
            item = Appointment(name=name, phone=phone, department_id=dept.id,
                               preferred_date=when, note=note)
            s.add(item)
            s.flush()
            item.reference = f"SH-{item.id:06d}"
            s.commit()
            return jsonify(reference=item.reference, status=item.status, id=item.id), 201

    @app.get("/api/appointments/<reference>")
    def lookup(reference):
        phone = _digits(request.args.get("phone", ""))
        with Session() as s:
            item = s.scalar(select(Appointment).where(Appointment.reference == reference.strip().upper()))
            # Same answer for "not found" and "wrong phone" so references cannot be probed.
            if item is None or not phone or _digits(item.phone) != phone:
                return jsonify(error="No matching appointment found."), 404
            return jsonify(reference=item.reference, name=item.name, department=item.department.name,
                           date=item.preferred_date.isoformat(), status=item.status)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify(error="Not found"), 404

    @app.errorhandler(405)
    def not_allowed(_):
        return jsonify(error="Method not allowed"), 405

    @app.errorhandler(500)
    def server_error(_):
        return jsonify(error="Internal server error"), 500

    return app
