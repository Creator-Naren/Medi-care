from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import json
import random
from datetime import datetime, date
from functools import wraps
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = 'medicare_hospital_secret_key_2026_super_secure'

# Initialize Database
init_db()

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Context Processor for User Info & Dark Mode
@app.context_processor
def inject_user():
    return {
        'current_user': {
            'name': session.get('user_name', 'Guest'),
            'username': session.get('username', ''),
            'role': session.get('user_role', 'guest')
        }
    }

# --- AUTHENTICATION ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    role = request.form.get('role', 'patient')

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO users (username, password, role, name, email) VALUES (?, ?, ?, ?, ?)',
                       (username, password, role, name, email))
        
        # If registering as a patient, also create a patient profile automatically
        if role == 'patient':
            patient_code = f"PAT-{random.randint(1000, 9999)}"
            cursor.execute('''
                INSERT INTO patients (patient_code, name, age, gender, blood_group, phone, email, address, emergency_contact, medical_history)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (patient_code, name, 30, 'Unspecified', 'O+', '+1 555-0000', email, 'Not provided', 'N/A', 'Newly registered user.'))

        conn.commit()
        flash('Account created successfully! Please log in.', 'success')
    except sqlite3.IntegrityError:
        flash('Username already exists. Please choose a different username.', 'danger')
    finally:
        conn.close()

    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- DASHBOARD ROUTE ---
@app.route('/')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    today_str = date.today().strftime('%Y-%m-%d')

    # Aggregated Stats
    cursor.execute('SELECT COUNT(*) as count FROM patients')
    total_patients = cursor.fetchone()['count']

    cursor.execute('SELECT COUNT(*) as count FROM doctors WHERE status = "Active"')
    active_doctors = cursor.fetchone()['count']

    cursor.execute('SELECT COUNT(*) as count FROM appointments WHERE appointment_date = ?', (today_str,))
    today_appointments = cursor.fetchone()['count']

    cursor.execute('SELECT SUM(total_amount) as total FROM bills WHERE payment_status = "Paid"')
    total_revenue = cursor.fetchone()['total'] or 0.0

    # Recent Appointments list
    cursor.execute('''
        SELECT a.*, p.name as patient_name, d.name as doctor_name, d.specialization
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.id DESC LIMIT 6
    ''')
    recent_appointments = cursor.fetchall()

    # Recent Billing
    cursor.execute('''
        SELECT b.*, p.name as patient_name
        FROM bills b
        JOIN patients p ON b.patient_id = p.id
        ORDER BY b.id DESC LIMIT 4
    ''')
    recent_bills = cursor.fetchall()

    # Active Doctors preview
    cursor.execute('SELECT * FROM doctors LIMIT 4')
    doctors_list = cursor.fetchall()

    conn.close()

    return render_template('dashboard.html',
                           total_patients=total_patients,
                           active_doctors=active_doctors,
                           today_appointments=today_appointments,
                           total_revenue=total_revenue,
                           recent_appointments=recent_appointments,
                           recent_bills=recent_bills,
                           doctors_list=doctors_list)

# --- PATIENTS ROUTES ---
@app.route('/patients')
@login_required
def patients():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM patients ORDER BY id DESC')
    patients_list = cursor.fetchall()
    conn.close()
    return render_template('patients.html', patients=patients_list)

@app.route('/patients/add', methods=['POST'])
@login_required
def add_patient():
    name = request.form['name']
    age = int(request.form['age'])
    gender = request.form['gender']
    blood_group = request.form['blood_group']
    phone = request.form['phone']
    email = request.form.get('email', '')
    address = request.form.get('address', '')
    emergency_contact = request.form.get('emergency_contact', '')
    medical_history = request.form.get('medical_history', 'None')

    patient_code = f"PAT-{random.randint(1000, 9999)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO patients (patient_code, name, age, gender, blood_group, phone, email, address, emergency_contact, medical_history)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (patient_code, name, age, gender, blood_group, phone, email, address, emergency_contact, medical_history))
    conn.commit()
    conn.close()

    flash(f'Patient {name} ({patient_code}) registered successfully!', 'success')
    return redirect(url_for('patients'))

@app.route('/patients/history/<int:patient_id>')
@login_required
def patient_history(patient_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM patients WHERE id = ?', (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('patients'))

    # Appointments history
    cursor.execute('''
        SELECT a.*, d.name as doctor_name, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC
    ''', (patient_id,))
    appointments = cursor.fetchall()

    # Prescriptions history
    cursor.execute('''
        SELECT pr.*, d.name as doctor_name
        FROM prescriptions pr
        JOIN doctors d ON pr.doctor_id = d.id
        WHERE pr.patient_id = ?
        ORDER BY pr.id DESC
    ''', (patient_id,))
    prescriptions_raw = cursor.fetchall()

    prescriptions = []
    for pr in prescriptions_raw:
        pr_dict = dict(pr)
        try:
            pr_dict['medicines'] = json.loads(pr_dict['medicines_json'])
        except Exception:
            pr_dict['medicines'] = []
        prescriptions.append(pr_dict)

    # Bills history
    cursor.execute('SELECT * FROM bills WHERE patient_id = ? ORDER BY id DESC', (patient_id,))
    bills = cursor.fetchall()

    conn.close()

    return render_template('patient_history.html', patient=patient, appointments=appointments, prescriptions=prescriptions, bills=bills)

# --- DOCTORS ROUTES ---
@app.route('/doctors')
@login_required
def doctors():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM doctors ORDER BY name ASC')
    doctors_list = cursor.fetchall()
    conn.close()
    return render_template('doctors.html', doctors=doctors_list)

@app.route('/doctors/add', methods=['POST'])
@login_required
def add_doctor():
    name = request.form['name']
    specialization = request.form['specialization']
    qualification = request.form['qualification']
    phone = request.form['phone']
    email = request.form.get('email', '')
    experience_years = int(request.form['experience_years'])
    consultation_fee = float(request.form['consultation_fee'])
    availability = request.form['availability']

    doctor_code = f"DOC-{random.randint(100, 999)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO doctors (doctor_code, name, specialization, qualification, phone, email, experience_years, consultation_fee, availability, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active')
    ''', (doctor_code, name, specialization, qualification, phone, email, experience_years, consultation_fee, availability))
    conn.commit()
    conn.close()

    flash(f'Dr. {name} added successfully!', 'success')
    return redirect(url_for('doctors'))

@app.route('/doctors/status/<int:doctor_id>', methods=['POST'])
@login_required
def toggle_doctor_status(doctor_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM doctors WHERE id = ?', (doctor_id,))
    doctor = cursor.fetchone()
    if doctor:
        new_status = 'On Leave' if doctor['status'] == 'Active' else 'Active'
        cursor.execute('UPDATE doctors SET status = ? WHERE id = ?', (new_status, doctor_id))
        conn.commit()
        flash(f'Doctor status updated to {new_status}.', 'info')
    conn.close()
    return redirect(url_for('doctors'))

# --- APPOINTMENTS ROUTES ---
@app.route('/appointments')
@login_required
def appointments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT a.*, p.name as patient_name, p.patient_code, p.phone as patient_phone,
               d.name as doctor_name, d.specialization
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.appointment_date DESC, a.appointment_time ASC
    ''')
    appointments_list = cursor.fetchall()

    cursor.execute('SELECT id, name, patient_code FROM patients ORDER BY name ASC')
    patients_list = cursor.fetchall()

    cursor.execute('SELECT id, name, specialization, consultation_fee FROM doctors WHERE status = "Active" ORDER BY name ASC')
    doctors_list = cursor.fetchall()

    conn.close()
    return render_template('appointments.html', appointments=appointments_list, patients=patients_list, doctors=doctors_list)

@app.route('/appointments/book', methods=['POST'])
@login_required
def book_appointment():
    patient_id = int(request.form['patient_id'])
    doctor_id = int(request.form['doctor_id'])
    appointment_date = request.form['appointment_date']
    appointment_time = request.form['appointment_time']
    reason = request.form.get('reason', '')
    notes = request.form.get('notes', '')

    appointment_code = f"APT-{random.randint(5000, 9999)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO appointments (appointment_code, patient_id, doctor_id, appointment_date, appointment_time, reason, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, 'Scheduled', ?)
    ''', (appointment_code, patient_id, doctor_id, appointment_date, appointment_time, reason, notes))
    conn.commit()
    conn.close()

    flash(f'Appointment {appointment_code} booked successfully!', 'success')
    return redirect(url_for('appointments'))

@app.route('/appointments/status/<int:appointment_id>', methods=['POST'])
@login_required
def update_appointment_status(appointment_id):
    new_status = request.form['status']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE appointments SET status = ? WHERE id = ?', (new_status, appointment_id))
    conn.commit()
    conn.close()
    flash(f'Appointment status updated to {new_status}.', 'success')
    return redirect(url_for('appointments'))

# --- PRESCRIPTIONS ROUTES ---
@app.route('/prescriptions')
@login_required
def prescriptions():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT pr.*, p.name as patient_name, p.patient_code, d.name as doctor_name, d.specialization
        FROM prescriptions pr
        JOIN patients p ON pr.patient_id = p.id
        JOIN doctors d ON pr.doctor_id = d.id
        ORDER BY pr.id DESC
    ''')
    raw_list = cursor.fetchall()

    prescriptions_list = []
    for row in raw_list:
        r_dict = dict(row)
        try:
            r_dict['medicines'] = json.loads(r_dict['medicines_json'])
        except Exception:
            r_dict['medicines'] = []
        prescriptions_list.append(r_dict)

    cursor.execute('SELECT id, name, patient_code FROM patients ORDER BY name ASC')
    patients_list = cursor.fetchall()

    cursor.execute('SELECT id, name, specialization FROM doctors WHERE status = "Active" ORDER BY name ASC')
    doctors_list = cursor.fetchall()

    cursor.execute('''
        SELECT a.id, a.appointment_code, p.name as patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        ORDER BY a.id DESC
    ''')
    appointments_list = cursor.fetchall()

    conn.close()
    return render_template('prescriptions.html', prescriptions=prescriptions_list, patients=patients_list, doctors=doctors_list, appointments=appointments_list)

@app.route('/prescriptions/add', methods=['POST'])
@login_required
def add_prescription():
    patient_id = int(request.form['patient_id'])
    doctor_id = int(request.form['doctor_id'])
    appointment_id = request.form.get('appointment_id')
    appointment_id = int(appointment_id) if appointment_id else None
    diagnosis = request.form['diagnosis']
    advice = request.form.get('advice', '')

    # Parse medication fields arrays
    med_names = request.form.getlist('med_name[]')
    med_dosages = request.form.getlist('med_dosage[]')
    med_freqs = request.form.getlist('med_freq[]')
    med_durations = request.form.getlist('med_duration[]')

    medicines = []
    for i in range(len(med_names)):
        if med_names[i].strip():
            medicines.append({
                'name': med_names[i].strip(),
                'dosage': med_dosages[i].strip() if i < len(med_dosages) else '',
                'frequency': med_freqs[i].strip() if i < len(med_freqs) else '',
                'duration': med_durations[i].strip() if i < len(med_durations) else ''
            })

    medicines_json = json.dumps(medicines)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO prescriptions (appointment_id, patient_id, doctor_id, diagnosis, medicines_json, advice)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (appointment_id, patient_id, doctor_id, diagnosis, medicines_json, advice))
    
    # Optionally update appointment status to Completed if linked
    if appointment_id:
        cursor.execute('UPDATE appointments SET status = "Completed" WHERE id = ?', (appointment_id,))

    conn.commit()
    conn.close()

    flash('Prescription created successfully!', 'success')
    return redirect(url_for('prescriptions'))

# --- BILLING & INVOICING ROUTES ---
@app.route('/billing')
@login_required
def billing():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT b.*, p.name as patient_name, p.patient_code, p.phone as patient_phone
        FROM bills b
        JOIN patients p ON b.patient_id = p.id
        ORDER BY b.id DESC
    ''')
    bills_raw = cursor.fetchall()

    bills_list = []
    for b in bills_raw:
        b_dict = dict(b)
        try:
            b_dict['items'] = json.loads(b_dict['items_json'])
        except Exception:
            b_dict['items'] = []
        bills_list.append(b_dict)

    cursor.execute('SELECT id, name, patient_code FROM patients ORDER BY name ASC')
    patients_list = cursor.fetchall()

    conn.close()
    return render_template('billing.html', bills=bills_list, patients=patients_list)

@app.route('/billing/create', methods=['POST'])
@login_required
def create_bill():
    patient_id = int(request.form['patient_id'])
    bill_date = request.form.get('bill_date', date.today().strftime('%Y-%m-%d'))
    payment_status = request.form.get('payment_status', 'Pending')
    payment_method = request.form.get('payment_method', 'Cash')
    tax_rate = float(request.form.get('tax_rate', 5.0)) # Tax %
    discount = float(request.form.get('discount', 0.0))

    item_descs = request.form.getlist('item_desc[]')
    item_amounts = request.form.getlist('item_amount[]')

    items = []
    subtotal = 0.0
    for i in range(len(item_descs)):
        if item_descs[i].strip():
            amt = float(item_amounts[i]) if item_amounts[i] else 0.0
            items.append({'description': item_descs[i].strip(), 'amount': amt})
            subtotal += amt

    tax = (subtotal * tax_rate) / 100.0
    total_amount = max(0.0, subtotal + tax - discount)
    invoice_number = f"INV-{random.randint(9000, 9999)}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bills (invoice_number, patient_id, bill_date, items_json, subtotal, tax, discount, total_amount, payment_status, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (invoice_number, patient_id, bill_date, json.dumps(items), subtotal, tax, discount, total_amount, payment_status, payment_method))
    conn.commit()
    conn.close()

    flash(f'Invoice {invoice_number} generated successfully!', 'success')
    return redirect(url_for('billing'))

@app.route('/billing/status/<int:bill_id>', methods=['POST'])
@login_required
def update_bill_status(bill_id):
    new_status = request.form['payment_status']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE bills SET payment_status = ? WHERE id = ?', (new_status, bill_id))
    conn.commit()
    conn.close()
    flash(f'Invoice payment status updated to {new_status}.', 'success')
    return redirect(url_for('billing'))

@app.route('/billing/invoice/<int:bill_id>')
@login_required
def view_invoice(bill_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT b.*, p.name as patient_name, p.patient_code, p.phone as patient_phone, p.email as patient_email, p.address as patient_address
        FROM bills b
        JOIN patients p ON b.patient_id = p.id
        WHERE b.id = ?
    ''', (bill_id,))
    bill_raw = cursor.fetchone()

    if not bill_raw:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('billing'))

    bill = dict(bill_raw)
    try:
        bill['items'] = json.loads(bill['items_json'])
    except Exception:
        bill['items'] = []

    conn.close()
    return render_template('invoice.html', bill=bill)

# --- GLOBAL SEARCH & ANALYTICS APIs ---
@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()
    results = []

    # Search Patients
    cursor.execute('SELECT id, name, patient_code as meta, "patient" as type FROM patients WHERE name LIKE ? OR patient_code LIKE ? OR phone LIKE ? LIMIT 5', (f'%{q}%', f'%{q}%', f'%{q}%'))
    for row in cursor.fetchall():
        results.append({'id': row['id'], 'title': row['name'], 'subtitle': f"Patient Code: {row['meta']}", 'type': 'Patient', 'url': url_for('patient_history', patient_id=row['id'])})

    # Search Doctors
    cursor.execute('SELECT id, name, specialization as meta, "doctor" as type FROM doctors WHERE name LIKE ? OR specialization LIKE ? LIMIT 5', (f'%{q}%', f'%{q}%'))
    for row in cursor.fetchall():
        results.append({'id': row['id'], 'title': row['name'], 'subtitle': f"Specialization: {row['meta']}", 'type': 'Doctor', 'url': url_for('doctors')})

    # Search Appointments
    cursor.execute('SELECT a.id, a.appointment_code, p.name as patient_name FROM appointments a JOIN patients p ON a.patient_id = p.id WHERE a.appointment_code LIKE ? OR p.name LIKE ? LIMIT 5', (f'%{q}%', f'%{q}%'))
    for row in cursor.fetchall():
        results.append({'id': row['id'], 'title': row['appointment_code'], 'subtitle': f"Patient: {row['patient_name']}", 'type': 'Appointment', 'url': url_for('appointments')})

    # Search Invoices
    cursor.execute('SELECT b.id, b.invoice_number, p.name as patient_name FROM bills b JOIN patients p ON b.patient_id = p.id WHERE b.invoice_number LIKE ? OR p.name LIKE ? LIMIT 5', (f'%{q}%', f'%{q}%'))
    for row in cursor.fetchall():
        results.append({'id': row['id'], 'title': row['invoice_number'], 'subtitle': f"Patient: {row['patient_name']}", 'type': 'Invoice', 'url': url_for('view_invoice', bill_id=row['id'])})

    conn.close()
    return jsonify(results)

@app.route('/api/analytics')
@login_required
def api_analytics():
    conn = get_db()
    cursor = conn.cursor()

    # Department wise doctor distribution
    cursor.execute('SELECT specialization, COUNT(*) as count FROM doctors GROUP BY specialization')
    departments = cursor.fetchall()
    dept_labels = [d['specialization'] for d in departments]
    dept_counts = [d['count'] for d in departments]

    # Appointment status distribution
    cursor.execute('SELECT status, COUNT(*) as count FROM appointments GROUP BY status')
    statuses = cursor.fetchall()
    status_labels = [s['status'] for s in statuses]
    status_counts = [s['count'] for s in statuses]

    conn.close()

    return jsonify({
        'departments': {'labels': dept_labels, 'counts': dept_counts},
        'appointments': {'labels': status_labels, 'counts': status_counts}
    })

if __name__ == '__main__':
    print("Starting Medicare Hospital Management System on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
