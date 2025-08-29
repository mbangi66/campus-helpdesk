# seed_bootstrap.py — idempotent seeding for first-run
import os

# --- robust imports: try app.py first, else models.py ---
try:
    from app import app, db, Organization, User  # models exposed from app.py
except Exception:
    from app import app, db                      # app + db always in app.py
    from models import Organization, User        # models are in models.py

with app.app_context():
    # Ensure tables exist
    db.create_all()

    # Ensure default org
    org = Organization.query.filter_by(slug="default").first()
    if not org:
        org = Organization(name="Default Campus", slug="default", primary_color="#111827")
        db.session.add(org)
        db.session.commit()

    # Helper to create users if missing
    def ensure(email, name, role, pw):
        u = User.query.filter_by(email=email).first()
        if not u:
            u = User(name=name, email=email, role=role, organization_id=org.id)
            if hasattr(u, "set_password"):
                u.set_password(pw)       # preferred if your model hashes passwords
            else:
                setattr(u, "password", pw)  # fallback for simple schemas
            db.session.add(u)
            db.session.commit()

    ensure(os.environ.get("SEED_ADMIN_EMAIL", "admin@campus.local"),
           "Admin", "admin", os.environ.get("SEED_ADMIN_PASSWORD", "admin123"))
    ensure(os.environ.get("SEED_AGENT_EMAIL", "agent@campus.local"),
           "Agent", "agent", os.environ.get("SEED_AGENT_PASSWORD", "agent123"))
    ensure(os.environ.get("SEED_STUDENT_EMAIL", "student@campus.local"),
           "Student", "student", os.environ.get("SEED_STUDENT_PASSWORD", "student123"))

    print("seed ok")
