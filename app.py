import streamlit as st
import pandas as pd
from datetime import time, datetime, date, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Page Config
st.set_page_config(page_title="Tutoring Daily Sheet", page_icon="📝")

# Styles
st.markdown("""
    <style>
    .main {
        max-width: 800px;
        margin: 0 auto;
    }
    h1 {
        text-align: center;
        color: #2E86C1;
        font-size: 1.75rem !important;
        font-weight: 600 !important;
    }
    .stTextArea textarea {
        height: 150px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 EP Tutoring Daily Sheet")

st.markdown("---")

# Shared Options
subject_options = [
    "Select Subject",
    "Manual Entry",
    "Algebra 1",
    "Algebra 2",
    "Geometry",
    "Pre-Calculus / AP Pre-Cal",
    "AP Calculus AB / BC",
    "AP Statistics",
    "Biology (Reg./Honors/AP)",
    "Chemistry (Reg./Honors/AP)",
    "Physics (General/Honors/AP Physics 1, 2, C)",
    "AP Environmental Science",
    "English 9 - 12",
    "AP English Lang / AP English Lit",
    "ESOL / ESL/ELL",
    "Standardized Tests: SAT / ACT",
    "AP Exam Prep",
    "GPA Management",
    "College Essay"
]

# Generate time options for selectbox
time_options = []
start_time_dt = datetime.strptime("12:00 AM", "%I:%M %p")
end_time_dt = datetime.strptime("11:30 PM", "%I:%M %p")
current_time_dt = start_time_dt
while current_time_dt <= end_time_dt:
    time_options.append(current_time_dt.strftime("%I:%M %p"))
    current_time_dt += timedelta(minutes=30)

st.subheader("📘 Student Tutoring Summary")
col1, col2 = st.columns(2)
with col1:
    student_name = st.text_input("Student Name", placeholder="Please enter student first name")
    teacher_name = st.text_input("Teacher", placeholder="Please type your name")
    
    # Start Time
    start_time_str = st.selectbox("Start Time", time_options, index=time_options.index("03:30 PM") if "03:30 PM" in time_options else 0)
with col2:
    class_date = st.date_input("Date", value=date.today())

    subject_selection = st.selectbox("Subject", subject_options)
    
    if subject_selection == "Manual Entry":
        subject = st.text_input("Enter Subject Manually", placeholder="Ex: Calculus & Physics")
    else:
        subject = subject_selection

    # End Time
    end_time_str = st.selectbox("End Time", time_options, index=time_options.index("05:30 PM") if "05:30 PM" in time_options else 4)

    # Convert strings back to datetime objects for calculation
    start_time = datetime.strptime(start_time_str, "%I:%M %p").time()
    end_time = datetime.strptime(end_time_str, "%I:%M %p").time()

st.markdown("---")
st.subheader("📝 Elite Homework Check")
elite_homework_options = [
    "Select Elite Homework Status",
    "Absolutely perfect.",
    "Great work.",
    "Needs more review.",
    "More focus needed.",
    "Assignment missing."
]
elite_homework_status = st.selectbox("Elite Homework Status", elite_homework_options, label_visibility="collapsed")
elite_homework_comment = st.text_input("Comment (optional)")

st.markdown("---")
st.subheader("📝 School Homework & Exam Check")

col5, col6 = st.columns(2)
with col5:
    st.markdown("**School Homework**")
    has_homework = st.selectbox("Has Homework?", ["Yes", "No"], key="homework_status")
    
    if has_homework == "Yes":
        homework_subject_selection = st.selectbox("Homework Subject", subject_options, key="homework_sub_select")
        if homework_subject_selection == "Manual Entry":
            homework_subject = st.text_input("Enter Homework Subject Manually", key="homework_sub_manual")
        else:
            homework_subject = homework_subject_selection
    else:
        homework_subject = ""
        st.text_input("Homework Subject", value="N/A", disabled=True, key="homework_sub_disabled")

    homework_due = st.date_input("Due Date", disabled=(has_homework == "No"), key="homework_due")

with col6:
    st.markdown("**School Exam**")
    has_exam = st.selectbox("Has Exam?", ["Yes", "No"], key="exam_status")
    
    if has_exam == "Yes":
        exam_subject_selection = st.selectbox("Exam Subject", subject_options, key="exam_sub_select")
        if exam_subject_selection == "Manual Entry":
            exam_subject = st.text_input("Enter Exam Subject Manually", key="exam_sub_manual")
        else:
            exam_subject = exam_subject_selection
    else:
        exam_subject = ""
        st.text_input("Exam Subject", value="N/A", disabled=True, key="exam_sub_disabled")

    exam_date = st.date_input("Exam Date", disabled=(has_exam == "No"), key="exam_date")

st.markdown("---")
st.subheader("📚 Detailed Tutoring Content")
lesson_content = st.text_area("Detailed Tutoring Content", label_visibility="collapsed", placeholder="Ex: Physics: Momentum\nCalculus: Logistic Growth", height=150)

st.markdown("---")
st.subheader("👨🎓 Attitude & Participation")
attitude_options = [
    "Excellent attitude and active participation (Great!)",
    "Good attitude (Good)",
    "Needs more focus (Needs Focus)",
    "Manual Input"
]
attitude_selection = st.selectbox("Select Attitude", attitude_options)

if attitude_selection == "Manual Input":
    attitude = st.text_area("Attitude & Participation Details", height=100)
else:
    attitude = st.text_area("Attitude & Participation Details", value=attitude_selection, height=100)

st.markdown("---")
st.subheader("🧪 Quiz & Check")
quiz = st.text_area("Example: Conducted a brief oral quiz, student answered questions to check understanding.")

st.markdown("---")
st.subheader("🏠 Today's Homework (Elite Homework)")
elite_homework = st.text_area("Elite Homework", placeholder="Ex: Complete remaining Physics problems")

submitted = st.button("Submit")

def calculate_duration(start, end):
    dummy_date = date.today()
    dt1 = datetime.combine(dummy_date, start)
    dt2 = datetime.combine(dummy_date, end)
    diff = dt2 - dt1
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    if hours > 0:
        return f"{hours} hr {minutes} min" if minutes > 0 else f"{hours} hr"
    return f"{minutes} min"

def format_time_ampm(t):
    return t.strftime("%I:%M %p")

def send_email(subject, body, to_email):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    
    if not sender_email or not sender_password:
        return False, "Email configuration missing. Please check .env file."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"

if submitted:
    # 1. Calculation
    duration = calculate_duration(start_time, end_time)
    start_time_str = format_time_ampm(start_time)
    end_time_str = format_time_ampm(end_time)
    
    # 2. Generate Email Body
    email_body = f"""
Hello, here is the summary of today's tutoring session.

📘 Student Class Summary
Student Name: {student_name}
Date: {class_date.strftime('%Y-%m-%d')}
Time: {start_time_str} – {end_time_str} ({duration})
Teacher: {teacher_name}
Subject: {subject}

📝 School Homework & Exam Check
School Homework: {has_homework}
"""
    if has_homework == "Yes":
        email_body += f"\nSubject: {homework_subject}\n\nDue Date: {homework_due}\n"
    
    email_body += f"\nSchool Exam: {has_exam}\n"
    
    if has_exam == "Yes":
        email_body += f"\nSubject: {exam_subject}\n\nExam Date: {exam_date}\n"

    email_body += f"""
📚 Class Content
{lesson_content}

👨🎓 Attitude & Participation
{attitude}

🧪 Quiz & Check
{quiz}

🏠 Today's Homework (Elite Homework)
{elite_homework}


Thank you.
"""
    
    # 3. Save Data (CSV)
    data = {
        "Date": [class_date],
        "Student": [student_name],
        "Teacher": [teacher_name],
        "Subject": [subject],
        "Start Time": [start_time_str],
        "End Time": [end_time_str],
        "Content": [lesson_content],
        "Homework": [elite_homework],
        "School Homework": [has_homework],
        "School Exam": [has_exam],
        "Attitude": [attitude]
    }
    df = pd.DataFrame(data)
    
    csv_file = "tutoring_records.csv"
    if os.path.exists(csv_file):
        df.to_csv(csv_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(csv_file, mode='w', header=True, index=False, encoding='utf-8-sig')
    
    st.success("Data saved successfully!")
    
    # 4. Send Email
    receiver_email = os.getenv("RECEIVER_EMAIL")
    if receiver_email:
        email_subject = f"[Tutoring Report] {student_name} - {class_date.strftime('%Y-%m-%d')}"
        success, msg = send_email(email_subject, email_body, receiver_email)
        if success:
            st.success(msg)
            with st.expander("View Sent Email"):
                st.text(email_body)
        else:
            st.error(msg)
    else:
        st.warning("Receiver email not configured.")
        with st.expander("View Generated Report"):
             st.text(email_body)
