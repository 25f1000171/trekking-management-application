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

        booking_query = Booking.query.join(Booking.user).join(Booking.trek)

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
        staff_id = session.get("user_id")

        assigned_treks = Trek.query.filter_by(
            assigned_staff_id=staff_id
        ).all()

        total_assigned = len(assigned_treks)

        active_treks = Trek.query.filter(
            Trek.assigned_staff_id == staff_id,
            Trek.status.in_(["Open", "Ongoing"])
        ).count()

        completed_treks = Trek.query.filter_by(
            assigned_staff_id=staff_id,
            status="Completed"
        ).count()

        total_participants = Booking.query.join(Trek).filter(
            Trek.assigned_staff_id == staff_id,
            Booking.status.in_(["Booked", "Completed"])
        ).count()

        return render_template(
            "staff/dashboard.html",
            total_assigned=total_assigned,
            active_treks=active_treks,
            completed_treks=completed_treks,
            total_participants=total_participants,
            assigned_treks=assigned_treks
        )

    @app.route("/staff/treks")
    @role_required("staff")
    def staff_treks():
        staff_id = session.get("user_id")
        search = request.args.get("search", "").strip()

        trek_query = Trek.query.filter_by(assigned_staff_id=staff_id)

        if search:
            trek_query = trek_query.filter(
                or_(
                    Trek.name.ilike(f"%{search}%"),
                    Trek.location.ilike(f"%{search}%"),
                    Trek.difficulty.ilike(f"%{search}%"),
                    Trek.status.ilike(f"%{search}%")
                )
            )

        treks = trek_query.order_by(Trek.start_date.asc()).all()

        return render_template(
            "staff/assigned_treks.html",
            treks=treks,
            search=search
        )


    @app.route("/staff/treks/<int:trek_id>/update", methods=["GET", "POST"])
    @role_required("staff")
    def staff_update_trek(trek_id):
        staff_id = session.get("user_id")

        trek = Trek.query.get_or_404(trek_id)

        if trek.assigned_staff_id != staff_id:
            flash("You can manage only your assigned treks.", "danger")
            return redirect(url_for("staff_treks"))

        if request.method == "POST":
            available_slots = int(request.form.get("available_slots"))
            status = request.form.get("status")

            if available_slots < 0:
                flash("Available slots cannot be negative.", "danger")
                return redirect(url_for("staff_update_trek", trek_id=trek.id))

            if available_slots > trek.total_slots:
                flash("Available slots cannot be greater than total slots.", "danger")
                return redirect(url_for("staff_update_trek", trek_id=trek.id))

            trek.available_slots = available_slots
            trek.status = status

            if status == "Completed":
                related_bookings = Booking.query.filter_by(
                    trek_id=trek.id,
                    status="Booked"
                ).all()

                for booking in related_bookings:
                    booking.status = "Completed"

            db.session.commit()

            flash("Trek updated successfully.", "success")
            return redirect(url_for("staff_treks"))

        return render_template("staff/update_trek.html", trek=trek)


    @app.route("/staff/treks/<int:trek_id>/participants")
    @role_required("staff")
    def staff_participants(trek_id):
        staff_id = session.get("user_id")

        trek = Trek.query.get_or_404(trek_id)

        if trek.assigned_staff_id != staff_id:
            flash("You can view participants only for your assigned treks.", "danger")
            return redirect(url_for("staff_treks"))

        bookings = Booking.query.filter_by(
            trek_id=trek.id
        ).order_by(Booking.booking_date.desc()).all()

        return render_template(
            "staff/participants.html",
            trek=trek,
            bookings=bookings
        )


    @app.route("/staff/profile", methods=["GET", "POST"])
    @role_required("staff")
    def staff_profile():
        staff = User.query.get_or_404(session.get("user_id"))

        if request.method == "POST":
            staff.name = request.form.get("name")
            staff.contact = request.form.get("contact")

            if staff.staff_profile:
                experience = request.form.get("experience")
                staff.staff_profile.experience = int(experience) if experience else 0
                staff.staff_profile.specialization = request.form.get("specialization")
                staff.staff_profile.address = request.form.get("address")

            db.session.commit()

            session["name"] = staff.name

            flash("Profile updated successfully.", "success")
            return redirect(url_for("staff_profile"))

        return render_template("staff/profile.html", staff=staff)

    @app.route("/user/dashboard")
    @role_required("user")
    def user_dashboard():
        user_id = session.get("user_id")

        available_treks = Trek.query.filter_by(status="Open").count()
        booked_treks = Booking.query.filter_by(
            user_id=user_id,
            status="Booked"
        ).count()
        completed_treks = Booking.query.filter_by(
            user_id=user_id,
            status="Completed"
        ).count()

        recent_bookings = Booking.query.filter_by(
            user_id=user_id
        ).order_by(Booking.booking_date.desc()).limit(5).all()

        return render_template(
            "user/dashboard.html",
            available_treks=available_treks,
            booked_treks=booked_treks,
            completed_treks=completed_treks,
            recent_bookings=recent_bookings
        )
    
    @app.route("/user/treks")
    @role_required("user")
    def user_treks():
        search = request.args.get("search", "").strip()
        difficulty = request.args.get("difficulty", "").strip()
        location = request.args.get("location", "").strip()

        trek_query = Trek.query.filter_by(status="Open")

        if search:
            trek_query = trek_query.filter(
                or_(
                    Trek.name.ilike(f"%{search}%"),
                    Trek.location.ilike(f"%{search}%"),
                    Trek.difficulty.ilike(f"%{search}%")
                )
            )

        if difficulty:
            trek_query = trek_query.filter(Trek.difficulty == difficulty)

        if location:
            trek_query = trek_query.filter(Trek.location.ilike(f"%{location}%"))

        treks = trek_query.order_by(Trek.start_date.asc()).all()

        user_bookings = Booking.query.filter_by(
            user_id=session.get("user_id"),
            status="Booked"
        ).all()

        booked_trek_ids = [booking.trek_id for booking in user_bookings]

        return render_template(
            "user/treks.html",
            treks=treks,
            search=search,
            difficulty=difficulty,
            location=location,
            booked_trek_ids=booked_trek_ids
        )


    @app.route("/user/treks/<int:trek_id>/book", methods=["POST"])
    @role_required("user")
    def book_trek(trek_id):
        user_id = session.get("user_id")
        trek = Trek.query.get_or_404(trek_id)

        current_user = User.query.get_or_404(user_id)

        if current_user.is_blacklisted:
            flash("Your account is blacklisted. You cannot book treks.", "danger")
            return redirect(url_for("user_treks"))

        if trek.status != "Open":
            flash("This trek is not open for booking.", "danger")
            return redirect(url_for("user_treks"))

        if trek.available_slots <= 0:
            flash("No slots available for this trek.", "danger")
            return redirect(url_for("user_treks"))

        existing_booking = Booking.query.filter(
            Booking.user_id == user_id,
            Booking.trek_id == trek.id,
            Booking.status.in_(["Booked", "Completed"])
        ).first()

        if existing_booking:
            flash("You have already booked this trek.", "warning")
            return redirect(url_for("user_treks"))

        booking = Booking(
            user_id=user_id,
            trek_id=trek.id,
            status="Booked",
            payment_status="Not Required"
        )

        trek.available_slots -= 1

        db.session.add(booking)
        db.session.commit()

        flash("Trek booked successfully.", "success")
        return redirect(url_for("my_bookings"))


    @app.route("/user/bookings")
    @role_required("user")
    def my_bookings():
        search = request.args.get("search", "").strip()

        booking_query = Booking.query.join(Trek).filter(
            Booking.user_id == session.get("user_id")
        )

        if search:
            booking_query = booking_query.filter(
                or_(
                    Trek.name.ilike(f"%{search}%"),
                    Trek.location.ilike(f"%{search}%"),
                    Trek.status.ilike(f"%{search}%"),
                    Booking.status.ilike(f"%{search}%")
                )
            )

        bookings = booking_query.order_by(Booking.booking_date.desc()).all()

        return render_template(
            "user/my_bookings.html",
            bookings=bookings,
            search=search
        )

    @app.route("/user/bookings/<int:booking_id>/cancel", methods=["POST"])
    @role_required("user")
    def cancel_booking(booking_id):
        user_id = session.get("user_id")

        booking = Booking.query.get_or_404(booking_id)

        if booking.user_id != user_id:
            flash("You can cancel only your own booking.", "danger")
            return redirect(url_for("my_bookings"))

        if booking.status != "Booked":
            flash("Only booked treks can be cancelled.", "warning")
            return redirect(url_for("my_bookings"))

        if booking.trek.status in ["Ongoing", "Completed"]:
            flash("You cannot cancel an ongoing or completed trek.", "danger")
            return redirect(url_for("my_bookings"))

        booking.status = "Cancelled"

        if booking.trek.available_slots < booking.trek.total_slots:
            booking.trek.available_slots += 1

        db.session.commit()

        flash("Booking cancelled successfully.", "success")
        return redirect(url_for("my_bookings"))
    
    @app.route("/user/profile", methods=["GET", "POST"])
    @role_required("user")
    def user_profile():
        user = User.query.get_or_404(session.get("user_id"))

        if request.method == "POST":
            user.name = request.form.get("name")
            user.contact = request.form.get("contact")

            db.session.commit()

            session["name"] = user.name

            flash("Profile updated successfully.", "success")
            return redirect(url_for("user_profile"))

        return render_template("user/profile.html", user=user)


    return app


app = create_app()

with app.app_context():
    from database_setup import create_admin_user
    db.create_all()
    create_admin_user()

if __name__ == "__main__":
    app.run(debug=True)