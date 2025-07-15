from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
from docx import Document
from docx.shared import Inches
from flask import send_file
from io import BytesIO
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

EXCEL_FILE = "Attendance Test.xlsx"


def is_valid_sheet(sheet_name):
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet_name)
        return 'Student ID' in df.columns
    except:
        return False


sheet_names = [s for s in pd.ExcelFile(
    EXCEL_FILE).sheet_names if is_valid_sheet(s)]


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['student_id']
        try:
            student_id = int(student_id)
            summary = []
            selected_record = None
            selected_term = None
            week_cols = []

            for sheet in sheet_names:
                df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
                weeks = [col for col in df.columns if col.startswith("Week")]
                df[weeks] = df[weeks].clip(upper=1.0)
                df["Capped Average (%)"] = df[weeks].mean(axis=1) * 100
                df["Capped Average (%)"] = df["Capped Average (%)"].round(2)

                student_data = df[df['Student ID'] == student_id]
                if not student_data.empty:
                    record = student_data.to_dict('records')[0]
                    summary.append({
                        "term": sheet.replace("_", " "),
                        "average": record["Capped Average (%)"]
                    })
                    if selected_record is None:
                        selected_record = record
                        selected_term = sheet
                        week_cols = weeks

            if selected_record:
                return render_template(
                    'dashboard.html',
                    student=selected_record,
                    weeks=week_cols,
                    term=selected_term.replace("_", " "),
                    terms=sheet_names,
                    selected_term=selected_term,
                    summary=summary
                )
            else:
                return render_template('login.html', error="Student ID not found.")
        except Exception as e:
            return render_template('login.html', error=f"Error: {str(e)}")

    return render_template('login.html')


@app.route('/term', methods=['POST'])
def change_term():
    student_id = request.form['student_id']
    selected_term = request.form['term']
    try:
        student_id = int(student_id)
        summary = []
        selected_record = None
        week_cols = []

        for sheet in sheet_names:
            df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
            weeks = [col for col in df.columns if col.startswith("Week")]
            df[weeks] = df[weeks].clip(upper=1.0)
            df["Capped Average (%)"] = df[weeks].mean(axis=1) * 100
            df["Capped Average (%)"] = df["Capped Average (%)"].round(2)

            student_data = df[df['Student ID'] == student_id]
            if not student_data.empty:
                record = student_data.to_dict('records')[0]
                summary.append({
                    "term": sheet.replace("_", " "),
                    "average": record["Capped Average (%)"]
                })
                if sheet == selected_term:
                    selected_record = record
                    week_cols = weeks

        if selected_record:
            return render_template(
                'dashboard.html',
                student=selected_record,
                weeks=week_cols,
                term=selected_term.replace("_", " "),
                terms=sheet_names,
                selected_term=selected_term,
                summary=summary
            )
        else:
            return render_template('login.html', error="Student ID not found.")
    except Exception as e:
        return render_template('login.html', error=f"Error: {str(e)}")


# === Admin Routes ===
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")
    return render_template('admin_login.html')


@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    selected_term = request.form.get(
        'term') if 'term' in request.form else sheet_names[0]
    student_id = request.form.get('student_id')
    student_summary = []
    student_name = None

    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=selected_term)
        week_cols = [col for col in df.columns if col.startswith("Week")]
        df[week_cols] = df[week_cols].clip(upper=1.0)
        df["Capped Average (%)"] = df[week_cols].mean(axis=1) * 100
        df["Capped Average (%)"] = df["Capped Average (%)"].round(2)
        students = df[["Student ID", "First Name", "Surname",
                       "Capped Average (%)"]].to_dict('records')

        if student_id:
            try:
                student_id = int(student_id)
                for sheet in sheet_names:
                    df_term = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
                    weeks = [
                        col for col in df_term.columns if col.startswith("Week")]
                    df_term[weeks] = df_term[weeks].clip(upper=1.0)
                    df_term["Capped Average (%)"] = df_term[weeks].mean(
                        axis=1) * 100
                    df_term["Capped Average (%)"] = df_term["Capped Average (%)"].round(
                        2)
                    student_data = df_term[df_term['Student ID'] == student_id]
                    if not student_data.empty:
                        record = student_data.to_dict('records')[0]
                        weekly = {week: round(
                            record[week] * 100, 2) for week in weeks}
                        student_summary.append({
                            "term": sheet.replace("_", " "),
                            "average": record["Capped Average (%)"],
                            "weeks": weekly
                        })
                        if not student_name:
                            student_name = f"{record['First Name']} {record['Surname']}"
            except:
                pass

        return render_template(
            'admin_dashboard.html',
            students=students,
            terms=sheet_names,
            selected_term=selected_term.replace("_", " "),
            student_summary=student_summary,
            student_id=student_id,
            student_name=student_name
        )
    except Exception as e:
        return render_template('admin_dashboard.html', students=[], terms=sheet_names, selected_term=selected_term, error=str(e))


@app.route('/admin/download_word_selected', methods=['POST'])
def download_word_selected():
    student_id = int(request.form['student_id'])
    selected_terms = request.form.getlist('selected_terms')

    student_summary = []
    student_name = None
    for sheet in sheet_names:
        term_name = sheet.replace("_", " ")
        if term_name not in selected_terms:
            continue
        df = pd.read_excel(EXCEL_FILE, sheet_name=sheet)
        weeks = [col for col in df.columns if col.startswith("Week")]
        df[weeks] = df[weeks].clip(upper=1.0)
        df["Capped Average (%)"] = df[weeks].mean(axis=1) * 100
        df["Capped Average (%)"] = df["Capped Average (%)"].round(2)
        student_data = df[df['Student ID'] == student_id]
        if not student_data.empty:
            record = student_data.to_dict('records')[0]
            weekly = [round(record[week] * 100, 2) for week in weeks]
            student_summary.append({
                "term": term_name,
                "weeks": weekly,
                "average": record["Capped Average (%)"]
            })
            if not student_name:
                student_name = f"{record['First Name']} {record['Surname']}"

    # Word generation (same as before)
    doc = Document()
    doc.add_heading('Attendance Letter', 0)
    doc.add_paragraph(
        "Whitecliffe\n67 Symonds Street, Auckland 1010\n0800 800 300\nwhitecliffe.ac.nz")
    doc.add_paragraph(f"Date: {datetime.date.today().strftime('%d %B %Y')}")
    doc.add_paragraph(f"Student Name: {student_name}")
    doc.add_paragraph(f"Student ID: {student_id}")
    doc.add_paragraph("NSN Number: [INSERT NSN]")
    doc.add_paragraph(
        "Dear Immigration Officer,\n\nRE: Attendance Summary Letter")
    doc.add_paragraph("Please be advised that the above student was enrolled in the Bachelor of Applied Information Technology (NZQF Level 7) at Whitecliffe College of Arts and Design (NZQA Provider Code 8509).")
    doc.add_paragraph("Attendance summary records:")

    table = doc.add_table(rows=1, cols=11)
    hdr = table.rows[0].cells
    hdr[0].text = "Term"
    for i in range(1, 10):
        hdr[i].text = f"W{i}"
    hdr[10].text = "AVG"

    for term in student_summary:
        row = table.add_row().cells
        row[0].text = term['term']
        for i in range(9):
            row[i+1].text = f"{term['weeks'][i]}%"
        row[10].text = f"{term['average']}%"

    doc.add_paragraph(
        "We have provided this letter to confirm the student's progress and commitment towards studies.\n\n"
        "If you have any concerns relating to the above student, please do not hesitate to contact me."
    )
    doc.add_paragraph(
        "\nYours sincerely,\n\n"
        "Dr. Muhammad Azam (Ph.D., CITPNZ, MIITP, MPEC)\n"
        "Programme Head – Information Technology, Whitecliffe\n"
        "Level 3, Ranchhode House, Lambton Quay, Wellington\n"
        "DDI +64 44941693\n"
        "muhammada@whitecliffe.ac.nz"
    )

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'attendance_letter_{student_id}.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


if __name__ == '__main__':
    app.run(debug=True)
