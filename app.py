import sqlite3
import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'hospital-super-secret-key'
DATABASE = 'hospital.db'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'Patient',
                specialization TEXT DEFAULT 'N/A'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                appointment_date TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (doctor_id) REFERENCES users (id)
            )
        ''')
       
        default_users = [
            ('Dev', generate_password_hash('dev@123'), 'Admin', 'System Administrator'),
            ('dr_smith', generate_password_hash('smith@123'), 'Doctor', 'General Physician'),
            ('dr_adams', generate_password_hash('adams@123'), 'Doctor', 'Cardiologist'),
            ('ravi', generate_password_hash('ravi@123'), 'Patient', 'N/A'),
            ('raju', generate_password_hash('raju@123'), 'Patient', 'N/A'),
            ('ramu', generate_password_hash('ramu@123'), 'Patient', 'N/A'),
            ('yash', generate_password_hash('yash@123'), 'Patient', 'N/A')
        ]
       
        for username, password, role, specialization in default_users:
            existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO users (username, password, role, specialization) VALUES (?, ?, ?, ?)",
                    (username, password, role, specialization)
                )
        conn.commit()


init_db()


# --- HTML TEMPLATES ---
BASE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Hospital Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
        <div class="container">
            <a class="navbar-brand font-weight-bold" href="/">🏥 City Care Hospital</a>
            <div>
                {% if session.get('user_id') %}
                    {% if session.get('role') == 'Admin' %}
                        <a href="/admin/users" class="btn btn-outline-light btn-sm me-2">Manage Users</a>
                    {% endif %}
                    <a href="/appointments" class="btn btn-outline-light btn-sm me-2">Appointments</a>
                    <span class="navbar-text text-white me-3">Welcome, {{ session['username'] }} ({{ session.get('role') }})</span>
                    <a href="/logout" class="btn btn-outline-light btn-sm">Logout</a>
                {% else %}
                    <a href="/login" class="btn btn-outline-light btn-sm">Login</a>
                    <a href="/register" class="btn btn-light btn-sm ms-2">Register</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""


INDEX_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
<div class="p-5 mb-4 bg-white rounded-3 shadow-sm text-center">
    <h1 class="display-5 fw-bold text-primary">Hospital Management System</h1>
    <p class="fs-4 col-md-8 mx-auto">Secure Patient, Doctor & Staff Portal</p>
    {% if not session.get('user_id') %}
        <a class="btn btn-primary btn-lg" href="/login" role="button">Login to Access Dashboard</a>
    {% else %}
        <div class="alert alert-success">You are logged in as <strong>{{ session['username'] }}</strong> ({{ session.get('role') }}).</div>
        <a href="/appointments" class="btn btn-success btn-lg mt-2">Go to Appointments Dashboard</a>
    {% endif %}
</div>
""")


LOGIN_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white"><h4>Login</h4></div>
            <div class="card-body">
                <form method="POST" action="/login">
                    <div class="mb-3">
                        <label>Username</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Password</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Login</button>
                </form>
            </div>
        </div>
    </div>
</div>
""")


REGISTER_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card shadow-sm">
            <div class="card-header bg-success text-white"><h4>Register Patient Account</h4></div>
            <div class="card-body">
                <form method="POST" action="/register">
                    <div class="mb-3">
                        <label>Username</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Password</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-success w-100">Register</button>
                </form>
            </div>
        </div>
    </div>
</div>
""")


APPOINTMENTS_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
<div class="row">
    {% if session.get('role') == 'Patient' %}
    <div class="col-md-4">
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-primary text-white"><h5>Book Doctor Appointment</h5></div>
            <div class="card-body">
                <form method="POST" action="/appointments">
                    <div class="mb-3">
                        <label>Select Doctor</label>
                        <select name="doctor_id" class="form-select" required>
                            {% for doc in doctors %}
                                <option value="{{ doc.id }}">Dr. {{ doc.username }} ({{ doc.specialization }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label>Appointment Date (Next 30 Days)</label>
                        <input type="date" name="appointment_date" class="form-control" min="{{ min_date }}" max="{{ max_date }}" required>
                        <div class="form-text text-muted">Past dates and fully booked slots (max 3/day) are restricted.</div>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Request Booking</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-8">
    {% else %}
    <div class="col-md-12">
    {% endif %}
        <div class="card shadow-sm">
            <div class="card-header bg-secondary text-white">
                <h5>{{ 'Appointments Management Panel' if session.get('role') in ['Admin', 'Doctor'] else 'Your Scheduled Appointments' }}</h5>
            </div>
            <div class="card-body">
                <table class="table table-hover align-middle">
                    <thead>
                        <tr>
                            <th>#</th>
                            {% if session.get('role') in ['Admin', 'Doctor'] %}<th>Patient</th>{% endif %}
                            <th>Doctor</th>
                            <th>Date</th>
                            <th>Status</th>
                            {% if session.get('role') in ['Admin', 'Doctor'] %}<th>Action</th>{% endif %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for appt in appointments %}
                        <tr>
                            <td>{{ appt.id }}</td>
                            {% if session.get('role') in ['Admin', 'Doctor'] %}<td><strong>{{ appt.patient_name }}</strong></td>{% endif %}
                            <td>Dr. {{ appt.doctor_name }} ({{ appt.specialization }})</td>
                            <td>{{ appt.appointment_date }}</td>
                            <td>
                                <span class="badge bg-{{ 'success' if appt.status == 'Approved' else ('danger' if appt.status == 'Rejected' else 'warning text-dark') }}">
                                    {{ appt.status }}
                                </span>
                            </td>
                            {% if session.get('role') in ['Admin', 'Doctor'] %}
                            <td>
                                {% if appt.status == 'Pending' %}
                                    <a href="/appointment/{{ appt.id }}/approve" class="btn btn-sm btn-success">Approve</a>
                                    <a href="/appointment/{{ appt.id }}/reject" class="btn btn-sm btn-danger">Reject</a>
                                {% else %}
                                    <span class="text-muted">Processed</span>
                                {% endif %}
                            </td>
                            {% endif %}
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="{{ 6 if session.get('role') in ['Admin', 'Doctor'] else 4 }}" class="text-center text-muted">No appointments found.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
""")


ADMIN_USERS_HTML = BASE_HTML.replace("{% block content %}{% endblock %}", """
<div class="row">
    <div class="col-md-4">
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-dark text-white"><h5>Add New User / Doctor</h5></div>
            <div class="card-body">
                <form method="POST" action="/admin/users/add">
                    <div class="mb-3">
                        <label>Username</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Password</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label>Role</label>
                        <select name="role" class="form-select">
                            <option value="Patient">Patient</option>
                            <option value="Doctor">Doctor</option>
                            <option value="Admin">Admin</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label>Specialization (for Doctors)</label>
                        <input type="text" name="specialization" class="form-control" value="General Physician">
                    </div>
                    <button type="submit" class="btn btn-dark w-100">Create User</button>
                </form>
            </div>
        </div>
    </div>
    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-header bg-secondary text-white"><h5>System Users Management & Role Updater</h5></div>
            <div class="card-body">
                <table class="table table-hover align-middle">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Username</th>
                            <th>Role & Spec</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in users %}
                        <tr>
                            <td>{{ user.id }}</td>
                            <td><strong>{{ user.username }}</strong></td>
                            <td>
                                <form method="POST" action="/admin/users/update/{{ user.id }}" class="d-flex align-items-center">
                                    <select name="role" class="form-select form-select-sm me-2" style="width: 110px;">
                                        <option value="Patient" {% if user.role == 'Patient' %}selected{% endif %}>Patient</option>
                                        <option value="Doctor" {% if user.role == 'Doctor' %}selected{% endif %}>Doctor</option>
                                        <option value="Admin" {% if user.role == 'Admin' %}selected{% endif %}>Admin</option>
                                    </select>
                                    <input type="text" name="specialization" value="{{ user.specialization }}" class="form-control form-control-sm me-2" style="width: 130px;" placeholder="Spec">
                                    <button type="submit" class="btn btn-sm btn-outline-primary">Save</button>
                                </form>
                            </td>
                            <td>
                                {% if user.username != session['username'] %}
                                    <a href="/admin/users/delete/{{ user.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('Delete this user?')">Delete</a>
                                {% else %}
                                    <span class="text-muted small">Current</span>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
""")


# --- ROUTES ---
@app.route('/')
def index():
    return render_template_string(INDEX_HTML)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (username, password, role, specialization) VALUES (?, ?, ?, ?)", (username, password, 'Patient', 'N/A'))
                conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'danger')
    return render_template_string(REGISTER_HTML)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash('Logged in successfully!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid credentials.', 'danger')
    return render_template_string(LOGIN_HTML)


@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
   
    today_str = datetime.date.today().isoformat()
    max_date_str = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()


    if request.method == 'POST' and session.get('role') == 'Patient':
        doctor_id = request.form['doctor_id']
        appointment_date = request.form['appointment_date']
       
        if appointment_date < today_str:
            flash('Cannot book appointments for past dates.', 'danger')
            return redirect(url_for('appointments'))


        with get_db() as conn:
            existing_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM appointments WHERE doctor_id = ? AND appointment_date = ? AND status != 'Rejected'",
                (doctor_id, appointment_date)
            ).fetchone()['cnt']


            if existing_count >= 3:
                flash('Selected doctor is fully booked on this date (max 3 slots). Please choose another date.', 'danger')
            else:
                conn.execute(
                    "INSERT INTO appointments (user_id, doctor_id, appointment_date, status) VALUES (?, ?, ?, 'Pending')",
                    (session['user_id'], doctor_id, appointment_date)
                )
                conn.commit()
                flash('Appointment requested successfully! Status is Pending approval.', 'success')
        return redirect(url_for('appointments'))


    with get_db() as conn:
        doctors = conn.execute("SELECT * FROM users WHERE role = 'Doctor'").fetchall()
       
        if session.get('role') == 'Admin':
            user_appointments = conn.execute("""
                SELECT appointments.*, p.username as patient_name, d.username as doctor_name, d.specialization
                FROM appointments
                JOIN users p ON appointments.user_id = p.id
                JOIN users d ON appointments.doctor_id = d.id
            """).fetchall()
        elif session.get('role') == 'Doctor':
            user_appointments = conn.execute("""
                SELECT appointments.*, p.username as patient_name, d.username as doctor_name, d.specialization
                FROM appointments
                JOIN users p ON appointments.user_id = p.id
                JOIN users d ON appointments.doctor_id = d.id
                WHERE appointments.doctor_id = ?
            """, (session['user_id'],)).fetchall()
        else:
            user_appointments = conn.execute("""
                SELECT appointments.*, d.username as doctor_name, d.specialization
                FROM appointments
                JOIN users d ON appointments.doctor_id = d.id
                WHERE appointments.user_id = ?
            """, (session['user_id'],)).fetchall()
       
    return render_template_string(APPOINTMENTS_HTML, appointments=user_appointments, doctors=doctors, min_date=today_str, max_date=max_date_str)


@app.route('/appointment/<int:appt_id>/approve')
def approve_appointment(appt_id):
    if session.get('role') not in ['Admin', 'Doctor']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    with get_db() as conn:
        conn.execute("UPDATE appointments SET status = 'Approved' WHERE id = ?", (appt_id,))
        conn.commit()
    flash('Appointment approved successfully.', 'success')
    return redirect(url_for('appointments'))


@app.route('/appointment/<int:appt_id>/reject')
def reject_appointment(appt_id):
    if session.get('role') not in ['Admin', 'Doctor']:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    with get_db() as conn:
        conn.execute("UPDATE appointments SET status = 'Rejected' WHERE id = ?", (appt_id,))
        conn.commit()
    flash('Appointment rejected.', 'info')
    return redirect(url_for('appointments'))


@app.route('/admin/users')
def admin_users():
    if session.get('role') != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    with get_db() as conn:
        users = conn.execute("SELECT * FROM users").fetchall()
    return render_template_string(ADMIN_USERS_HTML, users=users)


@app.route('/admin/users/add', methods=['POST'])
def admin_add_user():
    if session.get('role') != 'Admin':
        return redirect(url_for('index'))
    username = request.form['username']
    password = generate_password_hash(request.form['password'])
    role = request.form['role']
    specialization = request.form['specialization'] if role == 'Doctor' else 'N/A'
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO users (username, password, role, specialization) VALUES (?, ?, ?, ?)", (username, password, role, specialization))
            conn.commit()
        flash(f'User {username} created successfully.', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists.', 'danger')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/update/<int:user_id>', methods=['POST'])
def admin_update_user(user_id):
    if session.get('role') != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    new_role = request.form['role']
    new_spec = request.form['specialization'] if new_role == 'Doctor' else 'N/A'
    with get_db() as conn:
        conn.execute("UPDATE users SET role = ?, specialization = ? WHERE id = ?", (new_role, new_spec, user_id))
        conn.commit()
    flash('User role and details updated successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/delete/<int:user_id>')
def admin_delete_user(user_id):
    if session.get('role') != 'Admin':
        return redirect(url_for('index'))
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    flash('User deleted successfully.', 'info')
    return redirect(url_for('admin_users'))


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=3000)

