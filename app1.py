import streamlit as st
import sqlite3
import pandas as pd
import random

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Smart Doctor Appointment", layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("smart_doctor.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT,
    password TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS appointments (
    username TEXT,
    name TEXT,
    symptom TEXT,
    specialist TEXT,
    doctor TEXT,
    location TEXT,
    date TEXT,
    time TEXT,
    payment TEXT,
    appointment_id TEXT
)''')

conn.commit()

# ---------------- LOAD DATA ----------------
df = pd.read_csv("Dataset.csv")
df.columns = df.columns.str.strip().str.lower()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- CSS ----------------
st.markdown("""
<style>
header {visibility: hidden;}

.title {
    text-align: center;
    font-size: 40px;
    color: #1f77b4;
    font-weight: bold;
}

.stButton > button {
    background-color: red;
    color: white;
    border-radius: 8px;
}

.stButton > button:hover {
    background-color: darkred;
}
</style>
""", unsafe_allow_html=True)

# ---------------- FUNCTIONS ----------------
def recommend(symptom, location):
    data = df[(df["symptom"] == symptom) & (df["location"] == location)]
    if len(data) == 0:
        data = df[df["symptom"] == symptom]
    if len(data) == 0:
        return None
    return data.sample(1).iloc[0]


def is_time_booked(date, time_slot):
    c.execute("SELECT * FROM appointments WHERE date=? AND time=?",
              (str(date), str(time_slot)))
    return c.fetchone() is not None

# ---------------- LOGIN / SIGNUP ----------------
if not st.session_state.logged_in:

    col1, col2, col3 = st.columns([8,1,1])

    with col2:
        login_btn = st.button("Login")

    with col3:
        signup_btn = st.button("Signup")

    st.markdown('<div class="title">🏥 Smart Doctor Appointment</div>', unsafe_allow_html=True)

    if "page" not in st.session_state:
        st.session_state.page = "home"

    if login_btn:
        st.session_state.page = "login"

    if signup_btn:
        st.session_state.page = "signup"

    # ---------------- SIGNUP ----------------
    if st.session_state.page == "signup":
        st.subheader("Signup")

        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")

        if st.button("Create Account"):
            c.execute("INSERT INTO users VALUES (?,?)", (user, pwd))
            conn.commit()
            st.success("Account created!")

    # ---------------- LOGIN ----------------
    elif st.session_state.page == "login":
        st.subheader("Login")

        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")

        if st.button("Login Submit"):
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
            if c.fetchone():
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid credentials")

    else:
        st.info("Please login or signup")

# ---------------- DASHBOARD ----------------
else:

    st.markdown('<div class="title">🩺 Dashboard</div>', unsafe_allow_html=True)

    st.write(f"👤 User: {st.session_state.user}")

    name = st.text_input("Patient Name")

    symptom = st.selectbox("Symptom", df["symptom"].unique())
    location = st.selectbox("Location", df["location"].unique())

    # -------- RECOMMEND DOCTOR --------
    if st.button("Find Doctor"):

        result = recommend(symptom, location)

        if result is not None:
            st.success("Doctor Found!")

            st.write("### 🧑‍⚕️ Recommendation")
            st.write("Specialist:", result["specialist"])
            st.write("Doctor:", result["doctor"])
            st.write("Location:", result["location"])

            st.session_state.specialist = result["specialist"]
            st.session_state.doctor = result["doctor"]

        else:
            st.error("No doctor found")

    date = st.date_input("Date")
    time_slot = st.time_input("Time")

    payment = st.selectbox("Payment", ["Cash", "Card", "UPI"])

    doctor = st.session_state.get("doctor", "Not Selected")
    specialist = st.session_state.get("specialist", "Not Selected")

    # -------- BOOK APPOINTMENT --------
    if st.button("Book Appointment"):

        if doctor == "Not Selected":
            st.error("Please find doctor first")

        elif is_time_booked(date, time_slot):
            st.error("⛔ Time slot already booked. Choose another time.")

        else:
            appointment_id = "APT" + str(random.randint(1000, 9999))

            c.execute("INSERT INTO appointments VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (st.session_state.user,
                       name,
                       symptom,
                       specialist,
                       doctor,
                       location,
                       str(date),
                       str(time_slot),
                       payment,
                       appointment_id))

            conn.commit()

            st.success("🎉 Appointment Confirmed!")
            st.info(f"🆔 Appointment ID: {appointment_id}")

            # -------- SHOW DETAILS (RECEIPT) --------
            st.markdown("### 📋 Appointment Details")

            st.write(f"👤 Name: {name}")
            st.write(f"🧠 Symptom: {symptom}")
            st.write(f"🧑‍⚕️ Specialist: {specialist}")
            st.write(f"👨‍⚕️ Doctor: {doctor}")
            st.write(f"📍 Location: {location}")
            st.write(f"📅 Date: {date}")
            st.write(f"⏰ Time: {time_slot}")
            st.write(f"💳 Payment: {payment}")
            st.write(f"🆔 ID: {appointment_id}")

    # -------- VIEW APPOINTMENTS --------
    st.subheader("📋 My Appointments")

    c.execute("SELECT rowid, * FROM appointments WHERE username=?",
              (st.session_state.user,))
    data = c.fetchall()

    if data:
        df_view = pd.DataFrame(data, columns=[
            "ID","User","Name","Symptom","Specialist","Doctor",
            "Location","Date","Time","Payment","Appointment_ID"
        ])

        st.dataframe(df_view)

        # -------- DELETE --------
        del_id = st.number_input("Delete ID", step=1)
        if st.button("Delete"):
            c.execute("DELETE FROM appointments WHERE rowid=?", (del_id,))
            conn.commit()
            st.warning("Deleted")

        # -------- EDIT --------
        edit_id = st.number_input("Edit ID", step=1)
        new_name = st.text_input("New Name")

        if st.button("Update"):
            c.execute("UPDATE appointments SET name=? WHERE rowid=?",
                      (new_name, edit_id))
            conn.commit()
            st.success("Updated")

    else:
        st.info("No appointments yet")