import sqlite3
import os
import json
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), 'hospital.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL, -- admin, doctor, patient
            name TEXT NOT NULL,
            email TEXT
        )
    ''')

    # Create Patients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT,
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            emergency_contact TEXT,
            medical_history TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create Doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            qualification TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            experience_years INTEGER NOT NULL,
            consultation_fee REAL NOT NULL,
            availability TEXT NOT NULL,
            status TEXT DEFAULT 'Active' -- Active, On Leave
        )
    ''')

    # Create Appointments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_code TEXT UNIQUE NOT NULL,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Scheduled', -- Scheduled, In Progress, Completed, Cancelled
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (doctor_id) REFERENCES doctors (id)
        )
    ''')

    # Create Prescriptions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            diagnosis TEXT NOT NULL,
            medicines_json TEXT NOT NULL, -- JSON string of [{name, dosage, frequency, duration}]
            advice TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (doctor_id) REFERENCES doctors (id)
        )
    ''')

    # Create Bills table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            patient_id INTEGER NOT NULL,
            appointment_id INTEGER,
            bill_date TEXT NOT NULL,
            items_json TEXT NOT NULL, -- JSON list of [{description, amount}]
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            discount REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            payment_status TEXT DEFAULT 'Pending', -- Paid, Pending, Partially Paid
            payment_method TEXT DEFAULT 'Cash', -- Cash, Card, UPI, Insurance
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    ''')

    conn.commit()

    # Seed demo data if empty
    cursor.execute('SELECT COUNT(*) as count FROM users')
    if cursor.fetchone()['count'] == 0:
        seed_sample_data(conn)

    conn.close()

def seed_sample_data(conn):
    cursor = conn.cursor()

    # Seed Users
    users = [
        ('admin', 'admin123', 'admin', 'Administrator', 'admin@medicare.com'),
        ('dr_smith', 'doc123', 'doctor', 'Dr. Robert Smith', 'dr.smith@medicare.com'),
        ('dr_patel', 'doc123', 'doctor', 'Dr. Ananya Patel', 'dr.patel@medicare.com'),
        ('john_doe', 'user123', 'patient', 'John Doe', 'john.doe@gmail.com')
    ]
    cursor.executemany('INSERT INTO users (username, password, role, name, email) VALUES (?, ?, ?, ?, ?)', users)

    # Seed Doctors
    doctors = [
        ('DOC-101', 'Dr. Robert Smith', 'Cardiology', 'MD, FACC', '+1 555-0142', 'dr.smith@medicare.com', 14, 150.00, 'Mon-Fri (09:00 AM - 04:00 PM)', 'Active'),
        ('DOC-102', 'Dr. Ananya Patel', 'Neurology', 'MD, DM Neurology', '+1 555-0189', 'dr.patel@medicare.com', 10, 180.00, 'Mon-Sat (10:00 AM - 05:00 PM)', 'Active'),
        ('DOC-103', 'Dr. Marcus Vance', 'Pediatrics', 'MBBS, DCH', '+1 555-0233', 'dr.vance@medicare.com', 8, 120.00, 'Tue-Sun (08:00 AM - 02:00 PM)', 'Active'),
        ('DOC-104', 'Dr. Elena Rostova', 'Orthopedics', 'MS Orthopedics', '+1 555-0377', 'dr.rostova@medicare.com', 12, 160.00, 'Mon-Thu (11:00 AM - 06:00 PM)', 'On Leave'),
        ('DOC-105', 'Dr. Sarah Jenkins', 'Dermatology', 'MD Dermatology', '+1 555-0499', 'dr.jenkins@medicare.com', 7, 130.00, 'Mon-Fri (10:00 AM - 03:00 PM)', 'Active')
    ]
    cursor.executemany('''
        INSERT INTO doctors (doctor_code, name, specialization, qualification, phone, email, experience_years, consultation_fee, availability, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', doctors)

    # Seed Patients
    patients = [
        ('PAT-1001', 'John Doe', 42, 'Male', 'O+', '+1 555-9821', 'john.doe@gmail.com', '742 Evergreen Terrace, Springfield', 'Jane Doe (+1 555-9822)', 'Hypertension, Mild Asthma'),
        ('PAT-1002', 'Emily Clarke', 29, 'Female', 'A+', '+1 555-3411', 'emily.clarke@yahoo.com', '124 Conch Street, Bikini Bottom', 'David Clarke (+1 555-3412)', 'No chronic illness'),
        ('PAT-1003', 'Michael Brown', 65, 'Male', 'B-', '+1 555-7634', 'mbrown@outlook.com', '42 Wallaby Way, Sydney', 'Sarah Brown (+1 555-7635)', 'Type 2 Diabetes, High Cholesterol'),
        ('PAT-1004', 'Sophia Martinez', 34, 'Female', 'AB+', '+1 555-8812', 'sophia.m@gmail.com', '350 Fifth Avenue, New York', 'Carlos Martinez (+1 555-8813)', 'Migraine'),
        ('PAT-1005', 'David Wilson', 51, 'Male', 'O-', '+1 555-1190', 'dwilson@gmail.com', '221B Baker Street, London', 'Mary Wilson (+1 555-1191)', 'L4-L5 Disc herniation')
    ]
    cursor.executemany('''
        INSERT INTO patients (patient_code, name, age, gender, blood_group, phone, email, address, emergency_contact, medical_history)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', patients)

    today = date.today().strftime('%Y-%m-%d')

    # Seed Appointments
    appointments = [
        ('APT-5001', 1, 1, today, '09:30 AM', 'Routine Cardiovascular Checkup', 'Scheduled', 'Patient reported mild chest flutter.'),
        ('APT-5002', 2, 5, today, '10:30 AM', 'Skin Rash and Allergy Follow-up', 'Completed', 'Prescribed topical corticosteroid.'),
        ('APT-5003', 3, 2, today, '11:15 AM', 'Chronic Migraine Evaluation', 'In Progress', 'MRI scan recommended.'),
        ('APT-5004', 4, 3, today, '02:00 PM', 'Pediatric Wellness Exam', 'Scheduled', 'Child milestone review.'),
        ('APT-5005', 5, 4, today, '03:30 PM', 'Lower Back Pain Consultation', 'Cancelled', 'Rescheduled by patient.')
    ]
    cursor.executemany('''
        INSERT INTO appointments (appointment_code, patient_id, doctor_id, appointment_date, appointment_time, reason, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', appointments)

    # Seed Prescriptions
    meds1 = json.dumps([
        {"name": "Amoxicillin 500mg", "dosage": "1 Capsule", "frequency": "3 times daily", "duration": "5 Days"},
        {"name": "Paracetamol 650mg", "dosage": "1 Tablet", "frequency": "As needed for fever", "duration": "3 Days"}
    ])
    meds2 = json.dumps([
        {"name": "Sumatriptan 50mg", "dosage": "1 Tablet", "frequency": "At onset of headache", "duration": "10 Days"},
        {"name": "Propranolol 40mg", "dosage": "1 Tablet", "frequency": "Twice daily", "duration": "30 Days"}
    ])
    prescriptions = [
        (2, 2, 5, 'Acute Contact Dermatitis', meds1, 'Avoid harsh detergents. Keep skin moisturized.'),
        (3, 4, 2, 'Migraine with Aura', meds2, 'Maintain sleep log and reduce screen exposure.')
    ]
    cursor.executemany('''
        INSERT INTO prescriptions (appointment_id, patient_id, doctor_id, diagnosis, medicines_json, advice)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', prescriptions)

    # Seed Bills
    items1 = json.dumps([
        {"description": "Cardiology Consultation Fee", "amount": 150.00},
        {"description": "ECG (Electrocardiogram) Test", "amount": 80.00},
        {"description": "Echocardiogram", "amount": 220.00}
    ])
    items2 = json.dumps([
        {"description": "Neurology Consultation Fee", "amount": 180.00},
        {"description": "Brain MRI Scan", "amount": 450.00},
        {"description": "Pharmacy Medication", "amount": 65.00}
    ])
    bills = [
        ('INV-9001', 1, 1, today, items1, 450.00, 22.50, 20.00, 452.50, 'Paid', 'Credit Card'),
        ('INV-9002', 4, 3, today, items2, 695.00, 34.75, 50.00, 679.75, 'Pending', 'Cash')
    ]
    cursor.executemany('''
        INSERT INTO bills (invoice_number, patient_id, appointment_id, bill_date, items_json, subtotal, tax, discount, total_amount, payment_status, payment_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', bills)

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized and sample data seeded successfully.")
