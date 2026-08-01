"""The tutoring report: its fields, and how they render into an email.

Both apps share this module so the teacher's submission and the director's
reviewed copy are guaranteed to produce the same layout.
"""

from __future__ import annotations

from datetime import date, datetime
from html import escape

# Every field a report carries. The review UI edits these directly.
FIELDS = (
    "student_name", "class_date", "start_time", "teacher_name", "subject",
    "has_homework", "homework_subject", "homework_due",
    "has_exam", "exam_subject", "exam_date",
    "lesson_content", "attitude", "quiz", "elite_homework",
    "elite_homework_status", "elite_homework_comment",
)


def new_report(**values) -> dict:
    """Build a report dict with every field present, dates stored as ISO text."""
    r = {f: "" for f in FIELDS}
    for k, v in values.items():
        if k in r:
            r[k] = v.isoformat() if isinstance(v, (date, datetime)) else v
    return r


def to_date(value) -> date | None:
    """Parse a stored ISO date back into a date, tolerating junk."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except (ValueError, TypeError):
        return None


def _long_date(value) -> str:
    d = to_date(value)
    return d.strftime("%B %d, %Y") if d else str(value or "")


def _short_date(value) -> str:
    d = to_date(value)
    return d.strftime("%m/%d/%Y") if d else str(value or "")


def _html(value) -> str:
    """Escape for HTML and keep the teacher's line breaks visible."""
    return escape(str(value or "")).replace("\n", "<br>")


def email_subject(r: dict) -> str:
    return f"[Tutoring Report] {r.get('student_name', '')} - {_short_date(r.get('class_date'))}"


def render_text(r: dict) -> str:
    body = f"""Hello,
Below is a brief summary of today's tutoring session.

📘 Student Session Summary
• Student Name: {r.get('student_name', '')}
• Date: {_long_date(r.get('class_date'))}
• Time: {r.get('start_time', '')}
• Instructor: {r.get('teacher_name', '')}
• Subjects: {r.get('subject', '')}
----------------------------------
📝 School Homework & Exam Check
• School Homework: {r.get('has_homework', '')}"""

    if r.get("has_homework") == "Yes":
        body += (f"\n• Subject: {r.get('homework_subject', '')}"
                 f"\n• Due Date: {_short_date(r.get('homework_due'))}")

    body += f"\n• School Exam: {r.get('has_exam', '')}"

    if r.get("has_exam") == "Yes":
        body += (f"\n• Subject: {r.get('exam_subject', '')}"
                 f"\n• Exam Date: {_short_date(r.get('exam_date'))}")

    body += f"""
-----------------------------------
📚 Topics Covered in Class
• {r.get('lesson_content', '')}
-----------------------------------
👨‍🎓 Student Attitude & Participation
• {r.get('attitude', '')}
-----------------------------------
🧪 Quiz & Assessment
• {r.get('quiz', '')}
-----------------------------------
🏠 Today's Homework (Elite Homework)
• {r.get('elite_homework', '')}

Thank you.
"""
    return body


_H3 = ('<h3 style="color: #2E86C1; border-bottom: 1px solid #ddd; '
       'padding-bottom: 5px; margin-top: 20px;">')
_UL = '<ul style="list-style-type: none; padding-left: 0; margin-top: 5px;">'


def render_html(r: dict) -> str:
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <p>Hello,<br>Below is a brief summary of today's tutoring session.</p>

        {_H3}📘 Student Session Summary</h3>
        {_UL}
            <li>• <strong>Student Name:</strong> {_html(r.get('student_name'))}</li>
            <li>• <strong>Date:</strong> {_long_date(r.get('class_date'))}</li>
            <li>• <strong>Time:</strong> {_html(r.get('start_time'))}</li>
            <li>• <strong>Instructor:</strong> {_html(r.get('teacher_name'))}</li>
            <li>• <strong>Subjects:</strong> {_html(r.get('subject'))}</li>
        </ul>

        {_H3}📝 School Homework & Exam Check</h3>
        {_UL}
            <li>• <strong>School Homework:</strong> {_html(r.get('has_homework'))}</li>"""

    if r.get("has_homework") == "Yes":
        html += f"""
            <li>• <strong>Subject:</strong> {_html(r.get('homework_subject'))}</li>
            <li>• <strong>Due Date:</strong> {_short_date(r.get('homework_due'))}</li>"""

    html += f"""
            <li>• <strong>School Exam:</strong> {_html(r.get('has_exam'))}</li>"""

    if r.get("has_exam") == "Yes":
        html += f"""
            <li>• <strong>Subject:</strong> {_html(r.get('exam_subject'))}</li>
            <li>• <strong>Exam Date:</strong> {_short_date(r.get('exam_date'))}</li>"""

    html += f"""
        </ul>

        {_H3}📚 Topics Covered in Class</h3>
        {_UL}
            <li>• {_html(r.get('lesson_content'))}</li>
        </ul>

        {_H3}👨‍🎓 Student Attitude & Participation</h3>
        {_UL}
            <li>• {_html(r.get('attitude'))}</li>
        </ul>

        {_H3}🧪 Quiz & Assessment</h3>
        {_UL}
            <li>• {_html(r.get('quiz'))}</li>
        </ul>

        {_H3}🏠 Today's Homework (Elite Homework)</h3>
        {_UL}
            <li>• {_html(r.get('elite_homework'))}</li>
        </ul>

        <p style="margin-top: 30px;">Thank you.</p>
    </body>
    </html>
    """
    return html
