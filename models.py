from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, staff, user
    contact = db.Column(db.String(20))
    is_approved = db.Column(db.Boolean, default=True)
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff_profile = db.relationship(
        "StaffProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    bookings = db.relationship(
        "Booking",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    assigned_treks = db.relationship(
        "Trek",
        back_populates="assigned_staff",
        foreign_keys="Trek.assigned_staff_id"
    )


class StaffProfile(db.Model):
    __tablename__ = "staff_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    experience = db.Column(db.Integer, default=0)
    specialization = db.Column(db.String(150))
    address = db.Column(db.Text)
    status = db.Column(db.String(30), default="Pending")  # Pending, Approved, Blacklisted

    user = db.relationship("User", back_populates="staff_profile")


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    difficulty = db.Column(db.String(30), nullable=False)  # Easy, Moderate, Hard
    duration_days = db.Column(db.Integer, nullable=False)
    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(30), default="Pending")
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assigned_staff = db.relationship(
        "User",
        back_populates="assigned_treks",
        foreign_keys=[assigned_staff_id]
    )

    bookings = db.relationship(
        "Booking",
        back_populates="trek",
        cascade="all, delete-orphan"
    )


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(30), default="Booked")  # Booked, Cancelled, Completed
    payment_status = db.Column(db.String(30), default="Pending")

    user = db.relationship("User", back_populates="bookings")
    trek = db.relationship("Trek", back_populates="bookings")