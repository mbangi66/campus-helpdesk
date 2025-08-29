# seed_bootstrap.py — idempotent seeding that auto-detects models
import os
from app import app, db

# Find model classes by inspecting SQLAlchemy models loaded into the app
def find_model(predicate):
    seen = set()
    stack = list(db.Model.__subclasses__())
    while stack:
        cls = stack.pop()
        if cls in seen:
            continue
        seen.add(cls)
        try:
            if predicate(cls):
                return cls
        except Exception:
            pass
        # include subclasses recursively
        stack.extend(cls.__subclasses__())
    return None

# Heuristics: User has email+role; Organization has slug+name
User = find_model(lambda c: hasattr(c, "email") and hasattr(c, "role"))
Org  = find_model(lambda c: hasattr(c, "slug") and hasattr(c, "name"))

with app.app_context():
    # Ensure tables
    db.create_all()

    # Ensure default organization (if Org model exists)
    org = None
    if Org:
        org = db.session.query(Org).filter_by(slug="default").first()
        if not org:
            kwargs = {"name": "Default Campus", "slug": "default"}
            if hasattr(Org, "primary_color"):
                kwargs["primary_color"] = "#111827"
            org = Org(**kwargs)
            db.session.add(org)
            db.session.commit()

    # Create a user if missing (works with/without org link)
    def ensure(email, name, role, pw):
        if not User:
            return
        u = db.session.query(User).filter_by(email=email).first()
        if u:
            return
        u = User()
        # Basic fields
        for k, v in (("name", name), ("email", email), ("role", role)):
            if hasattr(u, k):
                setattr(u, k, v)
        # Optional org relationship
        if org:
            if hasattr(u, "organization_id"):
                setattr(u, "organization_id", getattr(org, "id", None))
            elif hasattr(u, "org_id"):
                setattr(u, "org_id", getattr(org, "id", None))
        # Password handling
        if hasattr(u, "set_password"):
            u.set_password(pw)           # preferred (hashing)
        elif hasattr(u, "password_hash"):
            setattr(u, "password_hash", pw)
        elif hasattr(u, "password"):
            setattr(u, "password", pw)   # plain field fallback
        db.session.add(u)
        db.session.commit()

    ensure(os.environ.get("SEED_ADMIN_EMAIL", "admin@campus.local"),
           "Admin", "admin", os.environ.get("SEED_ADMIN_PASSWORD", "admin123"))
    ensure(os.environ.get("SEED_AGENT_EMAIL", "agent@campus.local"),
           "Agent", "agent", os.environ.get("SEED_AGENT_PASSWORD", "agent123"))
    ensure(os.environ.get("SEED_STUDENT_EMAIL", "student@campus.local"),
           "Student", "student", os.environ.get("SEED_STUDENT_PASSWORD", "student123"))

    print("seed ok — User model =", getattr(User, "__name__", None),
          "Org model =", getattr(Org, "__name__", None))
