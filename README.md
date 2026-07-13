# Trekora - Trekking Management Application

Trekora is a web-based Trekking Management Application built for the MAD-I project.  
It helps manage trekking activities involving Admin, Trek Staff, and Users/Trekkers.

## Project Overview

Many trekking groups manage treks, bookings, staff coordination, and participant history manually using spreadsheets, phone calls, or offline records. This application provides a centralized system to manage treks, staff assignments, user bookings, trek slots, booking history, and trek status tracking.

## Tech Stack Used

- Backend: Flask
- Frontend: HTML, CSS, Bootstrap, Jinja2
- Database: SQLite
- ORM: Flask-SQLAlchemy
- Version Control: Git and GitHub

### Admin

Admin is the pre-existing superuser of the application.

- Login using predefined credentials
- Add, edit, and delete treks
- Approve trek staff
- Blacklist or unblacklist users and staff
- Assign staff members to treks
- View all users, staff, treks, and bookings
- Search users, staff, and treks

### Trek Staff

Trek Staff members can register, but they can access the dashboard only after admin approval.

- Login after approval
- View assigned treks
- Update trek slots and trek status
- View participants registered for assigned treks
- Mark treks as Open, Closed, Ongoing, or Completed
- Update profile

### User

Users can register and book available treks.

- Register and login
- View open treks
- Search and filter treks
- Book available treks
- Cancel eligible bookings
- View booking history
- Track trek status
- Update profile

## Core Features

- Role-based authentication
- Admin dashboard
- User dashboard
- Trek Staff dashboard
- Trek creation and management
- Staff approval and assignment
- Trek booking system
- Duplicate booking prevention
- Overbooking prevention
- Booking cancellation
- Trek status tracking
- Booking history

## Database Tables

The application uses SQLite database created programmatically using Flask-SQLAlchemy.

Main tables:

- User
- Trek
- Booking
- StaffProfile

## Admin Login Credentials

Use the following credentials after running the database setup file:

Email: admin@trek.com
Password: admin123
