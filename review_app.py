"""Director's review app: check a submitted tutoring report, edit it, then
send it to the parent (To) with the student on CC.

Run it on its own port so it never collides with the teacher form:
    streamlit run review_app.py --server.port 8502
"""

from datetime import datetime, timedelta

import streamlit as st

import config
from src import report as report_lib
from src import store
from src.mailer import send_email, invalid_addresses

st.set_page_config(page_title="Tutoring Report Review", page_icon="📬", layout="wide")

st.markdown("""
    <style>
    h1 { color: #2E86C1; font-size: 1.6rem !important; font-weight: 600 !important; }
    .stTextArea textarea { font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)


# --- Password gate -------------------------------------------------------
# This app lists every parent's address and can send mail as SENDER_EMAIL, so
# it must not be openable by anyone who happens to have the URL.
def require_password() -> bool:
    # Read it on every check, not once at import: a password gets rotated, and
    # a value frozen at process start keeps letting the old one through until
    # someone thinks to reboot the app.
    expected = config.setting("ADMIN_PASSWORD")
    if not expected:
        st.error("ADMIN_PASSWORD is not set, so this app is refusing to open.")
        st.caption("Set it in .env locally, or in the app's secrets when deployed.")
        # Say whether secrets loaded at all: a TOML error there looks exactly
        # like a missing password otherwise. Names only, never values.
        try:
            names = sorted(st.secrets.keys())
            st.caption(f"Secrets the app can see: {names or '(none)'}")
        except Exception as e:
            st.caption(f"Secrets could not be read at all: {type(e).__name__}: {e}")
        return False
    if st.session_state.get("authed"):
        return True

    st.title("📬 Tutoring Report Review")
    with st.form("login"):
        pw = st.text_input("Password (enter 4-digits)", type="password")
        if st.form_submit_button("Enter"):
            if pw == expected:
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
    return False


if not require_password():
    st.stop()


# --- Student roster (Google Sheet) ---------------------------------------
@st.cache_data(ttl=300, show_spinner="Loading student roster...")
def load_roster() -> tuple[list, str]:
    """Returns (students, error_message). Never raises: the app must stay
    usable with hand-typed addresses when the sheet is unreachable."""
    if not config.STUDENTS_SPREADSHEET_ID:
        return [], ("STUDENTS_SPREADSHEET_ID is not set in .env, so parent/student "
                    "emails cannot be looked up. Enter them by hand below.")
    try:
        from src.auth import default_credentials
        from src.students import load_students
        creds = default_credentials()
        return load_students(creds, config.STUDENTS_SPREADSHEET_ID,
                             config.STUDENTS_RANGE), ""
    except FileNotFoundError:
        return [], (f"credentials.json not found at {config.CREDENTIALS_PATH}. "
                    "Copy it from another Automation-H project folder.")
    except Exception as e:
        return [], f"Could not load the student roster: {e}"


roster, roster_error = load_roster()


# --- Sidebar -------------------------------------------------------------
TIME_OPTIONS = []
_t = datetime.strptime("12:00 AM", "%I:%M %p")
while _t <= datetime.strptime("11:30 PM", "%I:%M %p"):
    TIME_OPTIONS.append(_t.strftime("%I:%M %p"))
    _t += timedelta(minutes=30)

try:
    all_entries = store.load_all()
except Exception as e:
    st.error(f"Could not read the reports sheet: {e}")
    st.caption("The submitted reports are safe in the sheet; only this app is "
               "failing to read them.")
    st.stop()
open_ids = {e["id"] for e in all_entries if e.get("status") != store.SENT}


@st.fragment(run_every=15)
def watch_for_new_reports(known: set) -> None:
    """Poll the store on a timer and offer to pull new submissions in.

    Only this fragment reruns, so a report landing mid-edit cannot reset the
    report selector or interrupt typing: picking the moment to reload stays
    with the reviewer.
    """
    try:
        current = store.load_all()
    except Exception:
        return          # a blip while polling must not take the page down
    arrived = {e["id"] for e in current
               if e.get("status") != store.SENT} - known
    if not arrived:
        return
    st.info(f"🔔 {len(arrived)} new report(s) submitted.")
    if st.button("Load new reports", use_container_width=True):
        st.rerun(scope="app")


with st.sidebar:
    st.header("📬 Review")
    view = st.radio("Show", ["Pending", "Sent", "All"], horizontal=True)
    watch_for_new_reports(open_ids)
    if st.button("🔄 Reload roster"):
        load_roster.clear()
        st.rerun()
    st.caption(f"Roster: {len(roster)} student(s)" if roster else "Roster: not loaded")
    if roster_error:
        st.warning(roster_error)

entries = all_entries
if view == "Pending":
    entries = [e for e in entries if e.get("status") != store.SENT]
elif view == "Sent":
    entries = [e for e in entries if e.get("status") == store.SENT]

st.title("📬 Tutoring Report Review")

if not entries:
    st.info("No reports here yet. Submissions from the teacher form show up "
            "automatically.")
    st.stop()


def label_for(e: dict) -> str:
    r = e.get("report", {})
    icon = "✅" if e.get("status") == store.SENT else "🟡"
    d = report_lib.to_date(r.get("class_date"))
    return (f"{icon}  {r.get('student_name') or '(no name)'} — "
            f"{d.strftime('%m/%d/%Y') if d else '?'} — {r.get('teacher_name', '')}")


by_id = {e["id"]: e for e in entries}
entry_id = st.selectbox("Report", list(by_id),
                        format_func=lambda i: label_for(by_id[i]))
choice = by_id[entry_id]
saved = choice.get("report", {})
k = f"{entry_id}_"          # widget keys are per-report, so switching is clean

if choice.get("status") == store.SENT:
    st.success(f"Already sent {choice.get('sent_at', '')} → To: "
               f"{choice.get('sent_to', '')} / Cc: {choice.get('sent_cc', '') or '-'}")

edit_col, side_col = st.columns([3, 2], gap="large")

# --- Edit the report field by field --------------------------------------
with edit_col:
    st.subheader("✏️ Edit")

    c1, c2 = st.columns(2)
    with c1:
        student_name = st.text_input("Student Name", saved.get("student_name", ""),
                                     key=k + "student_name")
        teacher_name = st.text_input("Teacher", saved.get("teacher_name", ""),
                                     key=k + "teacher_name")
    with c2:
        class_date = st.date_input(
            "Date", value=report_lib.to_date(saved.get("class_date")),
            format="MM/DD/YYYY", key=k + "class_date")
        start_time = st.selectbox(
            "Start Time", TIME_OPTIONS,
            index=TIME_OPTIONS.index(saved["start_time"])
            if saved.get("start_time") in TIME_OPTIONS else 0,
            key=k + "start_time")

    subject = st.text_input("Subject", saved.get("subject", ""), key=k + "subject")

    st.markdown("**📝 School Homework & Exam**")
    h1, h2 = st.columns(2)
    with h1:
        has_homework = st.selectbox(
            "Has Homework?", ["Yes", "No"],
            index=0 if saved.get("has_homework") == "Yes" else 1,
            key=k + "has_homework")
        homework_subject = st.text_input(
            "Homework Subject", saved.get("homework_subject", ""),
            disabled=has_homework == "No", key=k + "homework_subject")
        homework_due = st.date_input(
            "Due Date", value=report_lib.to_date(saved.get("homework_due")),
            format="MM/DD/YYYY", disabled=has_homework == "No", key=k + "homework_due")
    with h2:
        has_exam = st.selectbox(
            "Has Exam?", ["Yes", "No"],
            index=0 if saved.get("has_exam") == "Yes" else 1, key=k + "has_exam")
        exam_subject = st.text_input(
            "Exam Subject", saved.get("exam_subject", ""),
            disabled=has_exam == "No", key=k + "exam_subject")
        exam_date = st.date_input(
            "Exam Date", value=report_lib.to_date(saved.get("exam_date")),
            format="MM/DD/YYYY", disabled=has_exam == "No", key=k + "exam_date")

    lesson_content = st.text_area("📚 Topics Covered in Class",
                                  saved.get("lesson_content", ""), height=120,
                                  key=k + "lesson_content")
    attitude = st.text_area("👨‍🎓 Attitude & Participation",
                            saved.get("attitude", ""), height=80, key=k + "attitude")
    quiz = st.text_area("🧪 Quiz & Assessment", saved.get("quiz", ""), height=80,
                        key=k + "quiz")
    elite_homework = st.text_area("🏠 Today's Homework (Elite Homework)",
                                  saved.get("elite_homework", ""), height=100,
                                  key=k + "elite_homework")

edited = report_lib.new_report(
    student_name=student_name, class_date=class_date, start_time=start_time,
    teacher_name=teacher_name, subject=subject,
    has_homework=has_homework,
    homework_subject=homework_subject if has_homework == "Yes" else "",
    homework_due=homework_due if has_homework == "Yes" else "",
    has_exam=has_exam,
    exam_subject=exam_subject if has_exam == "Yes" else "",
    exam_date=exam_date if has_exam == "Yes" else "",
    lesson_content=lesson_content, attitude=attitude, quiz=quiz,
    elite_homework=elite_homework,
    elite_homework_status=saved.get("elite_homework_status", ""),
    elite_homework_comment=saved.get("elite_homework_comment", ""),
)

# --- Recipients, preview, send -------------------------------------------
with side_col:
    st.subheader("📤 Send")

    match = None
    if roster:
        from src.students import find_student
        match = find_student(roster, student_name)
        if match:
            who = f"{match.name}" + (f" (parent: {match.parent_name})"
                                     if match.parent_name else "")
            st.caption(f"✅ Roster match — {who}")
            if not match.active:
                st.warning(f"⚠️ {match.name} is marked inactive in the roster "
                           "(Active = No). Check before sending.")
        else:
            st.caption("⚠️ No roster match for this student name — enter emails by hand.")

    default_to = choice.get("sent_to") or (match.parent_email if match else "")
    default_cc = choice.get("sent_cc") or (match.student_email if match else "")

    to_addr = st.text_input("To (parent)", default_to, key=k + "to",
                            placeholder="parent@example.com")
    cc_addr = st.text_input("Cc (student)", default_cc, key=k + "cc",
                            placeholder="student@example.com")
    subject_line = st.text_input("Email subject",
                                 report_lib.email_subject(edited), key=k + "subject_line")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Save edits", use_container_width=True):
            store.update_report(entry_id, edited)
            st.success("Saved.")
    with b2:
        send_clicked = st.button("📨 Send to parent", type="primary",
                                 use_container_width=True)

    # Sending is irreversible and the addresses are pre-filled from the roster,
    # so the button only asks; a second, deliberate click actually sends.
    confirming = k + "confirming"
    if send_clicked:
        bad = invalid_addresses(to_addr) + invalid_addresses(cc_addr)
        if not to_addr.strip():
            st.error("Enter the parent's email address first.")
        elif bad:
            st.error("Invalid email address: " + ", ".join(bad))
        else:
            st.session_state[confirming] = True

    if st.session_state.get(confirming):
        st.warning(
            f"Send **{edited.get('student_name') or 'this report'}**'s report to "
            f"these addresses?\n\n"
            f"- **To:** {to_addr}\n"
            f"- **Cc:** {cc_addr or '(none)'}")
        c1, c2 = st.columns(2)
        cancelled = c2.button("↩️ Cancel", key=k + "confirm_no",
                              use_container_width=True)
        if c1.button("✅ Yes, send", type="primary", key=k + "confirm_yes",
                     use_container_width=True):
            del st.session_state[confirming]
            store.update_report(entry_id, edited)
            ok, msg = send_email(
                subject_line, report_lib.render_text(edited),
                report_lib.render_html(edited), to_addr, cc_addr,
                sender=config.SENDER_EMAIL, password=config.SENDER_PASSWORD,
                host=config.SMTP_HOST, port=config.SMTP_PORT)
            if ok:
                store.mark_sent(entry_id, to_addr, cc_addr,
                                config.LOCAL_TZ)
                st.success(f"Sent to {to_addr}" + (f" (cc {cc_addr})" if cc_addr else ""))
                st.rerun()
            else:
                st.error(msg)
        elif cancelled:
            del st.session_state[confirming]
            st.rerun()

    with st.expander("⚙️ More"):
        if choice.get("status") == store.SENT and st.button("↩️ Move back to Pending"):
            store.reopen(entry_id)
            st.rerun()
        if st.button("🗑️ Delete this report"):
            store.delete(entry_id)
            st.rerun()

    st.subheader("👀 Preview")
    st.components.v1.html(report_lib.render_html(edited), height=560, scrolling=True)
