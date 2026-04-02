import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from datetime import datetime

# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    return sqlite3.connect("database.db", timeout=10)

# Create tables
conn = get_connection()
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users(
            username TEXT, password TEXT, role TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS appointments(
            name TEXT, age INT, gender TEXT, symptom TEXT,
            doctor TEXT, hospital TEXT, specialist TEXT,
            date TEXT, time TEXT)''')
conn.commit()
conn.close()

# ---------------- PASSWORD HASH ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- DATASET ----------------
data = pd.DataFrame([
    {"age": 22, "gender": "M", "symptom": "fever", "doctor": "Dr. Rao", "hospital": "City Hospital", "specialist": "General Physician"},
    {"age": 30, "gender": "F", "symptom": "fever", "doctor": "Dr. Mehta", "hospital": "Green Clinic", "specialist": "General Physician"},
    {"age": 45, "gender": "F", "symptom": "diabetes", "doctor": "Dr. Reddy", "hospital": "Care Hospital", "specialist": "Endocrinologist"},
    {"age": 50, "gender": "M", "symptom": "chest pain", "doctor": "Dr. Kumar", "hospital": "Apollo Hospital", "specialist": "Cardiologist"},
    {"age": 40, "gender": "M", "symptom": "cough", "doctor": "Dr. Sharma", "hospital": "Sunrise Hospital", "specialist": "Pulmonologist"},
    {"age": 35, "gender": "F", "symptom": "cough", "doctor": "Dr. Singh", "hospital": "City Hospital", "specialist": "Pulmonologist"},
    {"age": 28, "gender": "M", "symptom": "headache", "doctor": "Dr. Kapoor", "hospital": "Green Clinic", "specialist": "Neurologist"},
    {"age": 32, "gender": "F", "symptom": "headache", "doctor": "Dr. Nair", "hospital": "Sunrise Hospital", "specialist": "Neurologist"},
])

# ---------------- ENCODING ----------------
le_gender = LabelEncoder()
le_symptom = LabelEncoder()
le_doctor = LabelEncoder()

data['gender_enc'] = le_gender.fit_transform(data['gender'])
data['symptom_enc'] = le_symptom.fit_transform(data['symptom'])
data['doctor_enc'] = le_doctor.fit_transform(data['doctor'])

X = data[['age', 'gender_enc', 'symptom_enc']]
y = data['doctor_enc']

# ---------------- MODEL ----------------
model = DecisionTreeClassifier()
model.fit(X, y)

# ---------------- SESSION ----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.recommended_doctor = None
    st.session_state.recommended_hospital = None
    st.session_state.recommended_specialist = None

# ---------------- FUNCTIONS ----------------
def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (username, hash_password(password)))
    res = c.fetchone()
    conn.close()
    return res

def signup_user(username, password, role):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO users VALUES (?, ?, ?)",
              (username, hash_password(password), role))
    conn.commit()
    conn.close()

def book_appointment(data_tuple):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO appointments 
    (name, age, gender, symptom, doctor, hospital, specialist, date, time)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_tuple)
    conn.commit()
    conn.close()

def get_appointments():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM appointments")
    data = c.fetchall()
    conn.close()
    return data

def is_slot_available(date, time, doctor):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM appointments WHERE date=? AND time=? AND doctor=?",
              (str(date), str(time), doctor))
    res = c.fetchone()
    conn.close()
    return res is None

# ---------------- UI ----------------
st.title("🏥 Smart Doctor Appointment System")

menu = ["Login", "Sign Up"] if not st.session_state.logged_in else ["Dashboard", "Logout"]
choice = st.sidebar.selectbox("Menu", menu)

# ---------------- SIGNUP ----------------
if choice == "Sign Up":
    st.subheader("Create Account")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type='password')
    role = st.selectbox("Role", ["Patient", "Admin"])

    if st.button("Sign Up"):
        if user and pwd:
            signup_user(user, pwd, role)
            st.success("Account created! Please login.")
        else:
            st.warning("Enter all details")

# ---------------- LOGIN ----------------
elif choice == "Login":
    st.subheader("Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type='password')

    if st.button("Login"):
        res = login_user(user, pwd)
        if res:
            st.session_state.logged_in = True
            st.session_state.user = res[0]
            st.session_state.role = res[2]
            st.success("Login successful")
        else:
            st.error("Invalid credentials")

# ---------------- DASHBOARD ----------------
elif choice == "Dashboard":

    st.header(f"Welcome {st.session_state.user}")

    if st.session_state.role == "Patient":

        st.markdown("## 🧾 Patient Details")
        name = st.text_input("Name", st.session_state.user)
        age = st.slider("Age", 1, 100, 25)
        gender = st.selectbox("Gender", ["M", "F"])
        symptom = st.selectbox("Symptom", list(le_symptom.classes_))

        g = le_gender.transform([gender])[0]
        s = le_symptom.transform([symptom])[0]

        st.markdown("## 🤖 AI Recommendation")

        if st.button("Recommend Doctor"):
            pred = model.predict([[age, g, s]])
            doc = le_doctor.inverse_transform(pred)[0]
            info = data[data['doctor'] == doc].iloc[0]

            st.session_state.recommended_doctor = doc
            st.session_state.recommended_hospital = info['hospital']
            st.session_state.recommended_specialist = info['specialist']

            st.success(f"Doctor: {doc}")
            st.info(f"{info['hospital']} | {info['specialist']}")

        st.markdown("## 📅 Booking")

        date = st.date_input("Date")
        slots = ["10:00", "11:00", "12:00", "2:00", "4:00"]
        time = st.selectbox("Time", slots)

        st.markdown("## 💳 Payment")
        st.selectbox("Payment Method", ["UPI", "Card", "Cash"])

        if st.button("Confirm Booking"):
            if st.session_state.recommended_doctor:
                if is_slot_available(date, time, st.session_state.recommended_doctor):

                    book_appointment((
                        name, age, gender, symptom,
                        st.session_state.recommended_doctor,
                        st.session_state.recommended_hospital,
                        st.session_state.recommended_specialist,
                        str(date), str(time)
                    ))

                    st.success("🎉 Appointment Confirmed!")
                else:
                    st.error("❌ Slot already booked!")
            else:
                st.warning("Get recommendation first")

        st.subheader("📜 History")
        df = pd.DataFrame(get_appointments(),
                          columns=["Name","Age","Gender","Symptom","Doctor","Hospital","Specialist","Date","Time"])
        st.dataframe(df[df["Name"] == st.session_state.user])

    else:
        st.subheader("🛠 Admin Panel")
        df = pd.DataFrame(get_appointments(),
                          columns=["Name","Age","Gender","Symptom","Doctor","Hospital","Specialist","Date","Time"])

        st.dataframe(df)

        st.write("Total Appointments:", len(df))
        st.bar_chart(df["Doctor"].value_counts())

# ---------------- LOGOUT ----------------
elif choice == "Logout":
    st.session_state.logged_in = False
    st.success("Logged out successfully!")