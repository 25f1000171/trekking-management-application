from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, StaffProfile, Trek, Booking


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
        total_treks = Trek.query.count()
        total_bookings = Booking.query.count()

        return render_template(
            "admin/dashboard.html",
            total_users=total_users,
            total_staff=total_staff,
            total_treks=total_treks,
            total_bookings=total_bookings
        )
    def parse_date(date_value):
        if not date_value:
            return None
        return datetime.strptime(date_value, "%Y-%m-%d").date()
    @app.route("/admin/treks")
    @role_required("admin")
    def admin_treks():
        search = request.args.get("search", "").strip()

        trek_query = Trek.query

        if search:
            filters = [
                Trek.name.ilike(f"%{search}%"),
                Trek.location.ilike(f"%{search}%"),
                Trek.difficulty.ilike(f"%{search}%"),
                Trek.status.ilike(f"%{search}%")
            ]

            if search.isdigit():
                filters.append(Trek.id == int(search))

            trek_query = trek_query.filter(or_(*filters))

        treks = trek_query.order_by(Trek.created_at.desc()).all()
        return render_template("admin/treks.html", treks=treks, search=search)


    @app.route("/admin/treks/add", methods=["GET", "POST"])
    @role_required("admin")
    def add_trek():
        staff_members = User.query.filter_by(
            role="staff",
            is_approved=True,
            is_blacklisted=False
        ).all()

        if request.method == "POST":
            name = request.form.get("name")
            location = request.form.get("location")
            difficulty = request.form.get("difficulty")
            duration_days = int(request.form.get("duration_days"))
            total_slots = int(request.form.get("total_slots"))
            status = request.form.get("status")
            assigned_staff_id = request.form.get("assigned_staff_id")
            start_date = parse_date(request.form.get("start_date"))
            end_date = parse_date(request.form.get("end_date"))
            description = request.form.get("description")

            trek = Trek(
                name=name,
                location=location,
                difficulty=difficulty,
                duration_days=duration_days,
                total_slots=total_slots,
                available_slots=total_slots,
                assigned_staff_id=int(assigned_staff_id) if assigned_staff_id else None,
                status=status,
                start_date=start_date,
                end_date=end_date,
                description=description
            )

            db.session.add(trek)
            db.session.commit()

            flash("Trek created successfully.", "success")
            return redirect(url_for("admin_treks"))

        return render_template(
            "admin/trek_form.html",
            trek=None,
            form_title="Add New Trek",
            staff_members=staff_members
        )


    @app.route("/admin/treks/<int:trek_id>/edit", methods=["GET", "POST"])
    @role_required("admin")
    def edit_trek(trek_id):
        trek = Trek.query.get_or_404(trek_id)

        staff_members = User.query.filter_by(
            role="staff",
            is_approved=True,
            is_blacklisted=False
        ).all()

        if request.method == "POST":
            trek.name = request.form.get("name")
            trek.location = request.form.get("location")
            trek.difficulty = request.form.get("difficulty")
            trek.duration_days = int(request.form.get("duration_days"))
            trek.total_slots = int(request.form.get("total_slots"))
            trek.available_slots = int(request.form.get("available_slots"))
            trek.status = request.form.get("status")

            assigned_staff_id = request.form.get("assigned_staff_id")
            trek.assigned_staff_id = int(assigned_staff_id) if assigned_staff_id else None

            trek.start_date = parse_date(request.form.get("start_date"))
            trek.end_date = parse_date(request.form.get("end_date"))
            trek.description = request.form.get("description")

            if trek.available_slots > trek.total_slots:
                flash("Available slots cannot be greater than total slots.", "danger")
                return redirect(url_for("edit_trek", trek_id=trek.id))

            db.session.commit()

            flash("Trek updated successfully.", "success")
            return redirect(url_for("admin_treks"))

        return render_template(
            "admin/trek_form.html",
            trek=trek,
            form_title="Edit Trek",
            staff_members=staff_members
        )


    @app.route("/admin/treks/<int:trek_id>/delete", methods=["POST"])
    @role_required("admin")
    def delete_trek(trek_id):
        trek = Trek.query.get_or_404(trek_id)

        db.session.delete(trek)
        db.session.commit()

        flash("Trek deleted successfully.", "success")
        return redirect(url_for("admin_treks"))
    
    @app.route("/admin/staff")
    @role_required("admin")
    def admin_staff():
        search = request.args.get("search", "").strip()

        staff_query = User.query.filter_by(role="staff")

        if search:
            filters = [
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            ]

            if search.isdigit():
                filters.append(User.id == int(search))

            staff_query = staff_query.filter(or_(*filters))

        staff_members = staff_query.order_by(User.created_at.desc()).all()

        return render_template(
            "admin/staff.html",
            staff_members=staff_members,
            search=search
        )


    @app.route("/admin/staff/<int:staff_id>/approve", methods=["POST"])
    @role_required("admin")
    def approve_staff(staff_id):
        staff = User.query.get_or_404(staff_id)

        if staff.role != "staff":
            flash("Invalid staff account.", "danger")
            return redirect(url_for("admin_staff"))

        staff.is_approved = True

        if staff.staff_profile:
            staff.staff_profile.status = "Approved"

        db.session.commit()

        flash("Staff approved successfully.", "success")
        return redirect(url_for("admin_staff"))


    @app.route("/admin/staff/<int:staff_id>/toggle-blacklist", methods=["POST"])
    @role_required("admin")
    def toggle_staff_blacklist(staff_id):
        staff = User.query.get_or_404(staff_id)

        if staff.role != "staff":
            flash("Invalid staff account.", "danger")
            return redirect(url_for("admin_staff"))

        staff.is_blacklisted = not staff.is_blacklisted

        if staff.staff_profile:
            if staff.is_blacklisted:
                staff.staff_profile.status = "Blacklisted"
            elif staff.is_approved:
                staff.staff_profile.status = "Approved"
            else:
                staff.staff_profile.status = "Pending"

        db.session.commit()

        flash("Staff status updated successfully.", "success")
        return redirect(url_for("admin_staff"))


    @app.route("/admin/users")
    @role_required("admin")
    def admin_users():
        search = request.args.get("search", "").strip()

        user_query = User.query.filter_by(role="user")

        if search:
            filters = [
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%")
            ]

            if search.isdigit():
                filters.append(User.id == int(search))

            user_query = user_query.filter(or_(*filters))

        users = user_query.order_by(User.created_at.desc()).all()

        return render_template(
            "admin/users.html",
            users=users,
            search=search
        )


    @app.route("/admin/users/<int:user_id>/toggle-blacklist", methods=["POST"])
    @role_required("admin")
    def toggle_user_blacklist(user_id):
        user = User.query.get_or_404(user_id)

        if user.role != "user":
            flash("Invalid user account.", "danger")
            return redirect(url_for("admin_users"))

        user.is_blacklisted = not user.is_blacklisted
        db.session.commit()

        flash("User status updated successfully.", "success")
        return redirect(url_for("admin_users"))
    @app.route("/admin/bookings")
    @role_required("admin")
    def admin_bookings():
        search = request.args.get("search", "").strip()

        booking_query = Booking.query.join(User).join(Trek)

        if search:
            filters = [
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                Trek.name.ilike(f"%{search}%"),
                Trek.location.ilike(f"%{search}%"),
                Booking.status.ilike(f"%{search}%"),
                Booking.payment_status.ilike(f"%{search}%")
            ]

            if search.isdigit():
                filters.append(Booking.id == int(search))
                filters.append(User.id == int(search))
                filters.append(Trek.id == int(search))

            booking_query = booking_query.filter(or_(*filters))

        bookings = booking_query.order_by(Booking.booking_date.desc()).all()

        return render_template(
            "admin/bookings.html",
            bookings=bookings,
            search=search
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