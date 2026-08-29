import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import pytz

import config
from src import drafts
from src import report as report_lib
from src import store
from src.mailer import send_email
from src.students import find_student

# Page Config
st.set_page_config(page_title="Tutoring Daily Sheet", page_icon="📝")


@st.cache_data(ttl=300, show_spinner=False)
def roster() -> list:
    """The student list, for addressing the parent draft. Never raises: a draft
    with no address still beats no draft at all."""
    if not config.STUDENTS_SPREADSHEET_ID:
        return []
    try:
        from src.auth import default_credentials
        from src.students import load_students
        return load_students(default_credentials(),
                             config.STUDENTS_SPREADSHEET_ID, config.STUDENTS_RANGE)
    except Exception:
        return []

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

# Get current date in US Eastern time to prevent timezone issues in the evening
eastern = pytz.timezone('America/New_York')
current_date_est = datetime.now(eastern).date()

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
# Row 1: Student Name and Date
row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    student_name = st.text_input("Student Name", placeholder="Please enter student first name")
with row1_col2:
    class_date = st.date_input("Date", value=current_date_est, format="MM/DD/YYYY")

# Row 2: Teacher and Subject
row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    teacher_name = st.text_input("Teacher", placeholder="Please type your name")
with row2_col2:
    subject_selection = st.selectbox("Subject", subject_options)
    
    if subject_selection == "Manual Entry":
        subject = st.text_input("Enter Subject Manually")
    else:
        subject = subject_selection

# Row 3: Start Time
start_time_str = st.selectbox("Start Time", time_options, index=time_options.index("03:30 PM") if "03:30 PM" in time_options else 0)

# Convert string back to datetime object
start_time = datetime.strptime(start_time_str, "%I:%M %p").time()

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

    homework_due = st.date_input("Due Date", value=current_date_est, disabled=(has_homework == "No"), key="homework_due", format="MM/DD/YYYY")

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

    exam_date = st.date_input("Exam Date", value=current_date_est, disabled=(has_exam == "No"), key="exam_date", format="MM/DD/YYYY")

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
    attitude = st.text_input("Attitude & Participation Details")
else:
    attitude = attitude_selection

st.markdown("---")
st.subheader("🧪 Quiz & Check")
quiz_options = [
    "Select Quiz Status",
    "No quiz conducted this session; focused on introducing new material.",
    "Conducted a brief oral quiz; student answered all questions correctly.",
    "Reviewed key concepts through Q&A; student demonstrated solid understanding.",
    "Administered a short written quiz; student showed good comprehension.",
    "Tested understanding through practice problems; student needs more review on some topics.",
    "Checked understanding via oral questions; student struggled and requires additional practice.",
    "Manual Input"
]
quiz_selection = st.selectbox("Quiz Status", quiz_options, label_visibility="collapsed")

if quiz_selection == "Manual Input":
    quiz = st.text_input("Quiz & Check Details")
else:
    quiz = quiz_selection

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

if submitted:
    # 1. Collect everything the teacher entered into one report
    entry = report_lib.new_report(
        student_name=student_name,
        class_date=class_date,
        start_time=format_time_ampm(start_time),
        teacher_name=teacher_name,
        subject=subject,
        has_homework=has_homework,
        homework_subject=homework_subject,
        homework_due=homework_due if has_homework == "Yes" else "",
        has_exam=has_exam,
        exam_subject=exam_subject,
        exam_date=exam_date if has_exam == "Yes" else "",
        lesson_content=lesson_content,
        attitude=attitude,
        quiz=quiz,
        elite_homework=elite_homework,
        elite_homework_status=elite_homework_status,
        elite_homework_comment=elite_homework_comment,
    )

    text_body = report_lib.render_text(entry)
    html_body = report_lib.render_html(entry)

    # 2. Save Data (CSV)
    data = {
        "Date": [class_date],
        "Student": [student_name],
        "Teacher": [teacher_name],
        "Subject": [subject],
        "Start Time": [entry["start_time"]],
        "Content": [lesson_content],
        "Homework": [elite_homework],
        "School Homework": [has_homework],
        "School Exam": [has_exam],
        "Attitude": [attitude]
    }
    df = pd.DataFrame(data)

    csv_file = str(config.RECORDS_CSV)
    if os.path.exists(csv_file):
        df.to_csv(csv_file, mode='a', header=False, index=False, encoding='utf-8-sig')
    else:
        df.to_csv(csv_file, mode='w', header=True, index=False, encoding='utf-8-sig')

    st.success("Data saved successfully!")

    # 3. Queue it for the director's review app.
    # Never let this stop step 4: emailing the director is how the report
    # actually reaches a human, and it worked long before the review queue
    # existed. A teacher who has finished a lesson should not lose their write-up
    # because a spreadsheet is misconfigured.
    entry_id = None
    try:
        entry_id = store.add(entry, config.LOCAL_TZ)
    except Exception as e:
        st.warning(f"Saved and emailed, but not queued for review: {e}")

    # 4. Send Email to the director
    if config.RECEIVER_EMAIL:
        success, msg = send_email(
            report_lib.email_subject(entry), text_body, html_body,
            config.RECEIVER_EMAIL,
            sender=config.SENDER_EMAIL, password=config.SENDER_PASSWORD,
            host=config.SMTP_HOST, port=config.SMTP_PORT,
        )
        if success:
            st.success(msg)
            with st.expander("View Sent Email"):
                st.components.v1.html(html_body, height=600, scrolling=True)
        else:
            st.error(msg)
    else:
        st.warning("Receiver email not configured.")
        with st.expander("View Generated Report"):
            st.components.v1.html(html_body, height=600, scrolling=True)

    # 5. Leave the parent email as a draft while the lesson is still fresh, so
    # the director only has to read it and press send. Nothing goes out here.
    # A failure leaves the report pending, which the Prepare parent drafts
    # workflow can pick up later; it must never cost the teacher their write-up.
    if entry_id:
        try:
            match = find_student(roster(), entry.get("student_name", ""))
            to = match.parent_email if match else ""
            cc = match.student_email if match else ""
            ok, why = drafts.save_drafts(
                [drafts.build_report_draft(entry, to, cc, config.SENDER_EMAIL)],
                sender=config.SENDER_EMAIL, password=config.SENDER_PASSWORD)[0]
            if ok:
                store.mark_drafted(entry_id, to, cc)
                st.success(
                    f"Parent draft ready in Gmail, addressed to {to}." if to
                    else "Parent draft ready in Gmail. No roster match for this "
                         "name, so the address was left blank.")
            else:
                st.warning(f"Parent draft not prepared: {why}")
        except Exception as e:
            st.warning(f"Parent draft not prepared: {e}")

