from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd

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


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


if __name__ == '__main__':
    app.run(debug=True)
