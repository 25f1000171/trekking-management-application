from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, StaffProfile


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = "dev-secret-key-change-later"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///trekking.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    def login_required(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please login first.", "warning")
                return redirect(url_for("login"))
            return view_function(*args, **kwargs)
        return wrapper

    def role_required(required_role):
        def decorator(view_function):
            @wraps(view_function)
            def wrapper(*args, **kwargs):
                if "user_id" not in session:
                    flash("Please login first.", "warning")
                    return redirect(url_for("login"))

                if session.get("role") != required_role:
                    flash("You are not allowed to access this page.", "danger")
                    return redirect(url_for("home"))

                return view_function(*args, **kwargs)
            return wrapper
        return decorator

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/register/user", methods=["GET", "POST"])
    def register_user():
        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            contact = request.form.get("contact")

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered.", "danger")
                return redirect(url_for("register_user"))

            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role="user",
                contact=contact,
                is_approved=True,
                is_blacklisted=False
            )

            db.session.add(user)
            db.session.commit()

            flash("User registration successful. Please login.", "success")
            return redirect(url_for("login"))

        return render_template("register_user.html")

    @app.route("/register/staff", methods=["GET", "POST"])
    def register_staff():
        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            contact = request.form.get("contact")
            experience = request.form.get("experience")
            specialization = request.form.get("specialization")
            address = request.form.get("address")

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email already registered.", "danger")
                return redirect(url_for("register_staff"))

            staff = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role="staff",
                contact=contact,
                is_approved=False,
                is_blacklisted=False
            )

            db.session.add(staff)
            db.session.commit()

            staff_profile = StaffProfile(
                user_id=staff.id,
                experience=int(experience) if experience else 0,
                specialization=specialization,
                address=address,
                status="Pending"
            )

            db.session.add(staff_profile)
            db.session.commit()

            flash("Staff registration successful. Please wait for admin approval.", "success")
            return redirect(url_for("login"))

        return render_template("register_staff.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            user = User.query.filter_by(email=email).first()

            if not user or not check_password_hash(user.password_hash, password):
                flash("Invalid email or password.", "danger")
                return redirect(url_for("login"))

            if user.is_blacklisted:
                flash("Your account has been blacklisted.", "danger")
                return redirect(url_for("login"))

            if user.role == "staff" and not user.is_approved:
                flash("Your staff account is waiting for admin approval.", "warning")
                return redirect(url_for("login"))

            session["user_id"] = user.id
            session["name"] = user.name
            session["role"] = user.role

            flash("Login successful.", "success")

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user.role == "staff":
                return redirect(url_for("staff_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        session.clear()
        flash("Logged out successfully.", "success")
        return redirect(url_for("login"))

    @app.route("/admin/dashboard")
    @role_required("admin")
    def admin_dashboard():
        total_users = User.query.filter_by(role="user").count()
        total_staff = User.query.filter_by(role="staff").count()
        return render_template(
            "admin/dashboard.html",
            total_users=total_users,
            total_staff=total_staff
        )

    @app.route("/staff/dashboard")
    @role_required("staff")
    def staff_dashboard():
        return render_template("staff/dashboard.html")

    @app.route("/user/dashboard")
    @role_required("user")
    def user_dashboard():
        return render_template("user/dashboard.html")

    return app


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        db.create_all()

    app.run(debug=True)