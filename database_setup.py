from werkzeug.security import generate_password_hash
from app import create_app
from models import db, User


ADMIN_EMAIL = "admin@trek.com"
ADMIN_PASSWORD = "admin123"


def create_admin_user():
    existing_admin = User.query.filter_by(email=ADMIN_EMAIL).first()

    if existing_admin:
        print("Admin user already exists.")
        return

    admin = User(
        name="Admin",
        email=ADMIN_EMAIL,
        password_hash=generate_password_hash(ADMIN_PASSWORD),
        role="admin",
        contact="0000000000",
        is_approved=True,
        is_blacklisted=False
    )

    db.session.add(admin)
    db.session.commit()

    print("Admin user created successfully.")
    print(f"Admin Email: {ADMIN_EMAIL}")
    print(f"Admin Password: {ADMIN_PASSWORD}")


def initialize_database():
    app = create_app()

    with app.app_context():
        db.create_all()
        create_admin_user()
        print("Database tables created successfully.")


if __name__ == "__main__":
    initialize_database()