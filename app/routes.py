from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from .extensions import db, login_manager
from .models import Student, Grade, User
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, logout_user, login_required, current_user
from io import BytesIO
import os, pandas as pd, matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
from collections import Counter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

main_blueprint = Blueprint('main', __name__)
SUBJECTS = ['Math', 'Science', 'English', 'History']

# ---------------------- LOGIN MANAGER ----------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------------- HOME ----------------------
@main_blueprint.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('home.html')


# ---------------------- DASHBOARD ----------------------
@main_blueprint.route('/dashboard')
@login_required
def index():
    students = Student.query.filter_by(user_id=current_user.id).all()
    total_students = len(students)
    avg_score = round(sum(s.average() or 0 for s in students) / total_students, 2) if total_students else 0
    top_student = max(students, key=lambda s: s.average() or 0).name if students else "N/A"
    a_grade_count = sum(1 for s in students if s.grade_letter() == 'A')

    return render_template(
        'index.html',
        students=students,
        total_students=total_students,
        avg_score=avg_score,
        top_student=top_student,
        a_grade_count=a_grade_count
    )


# ---------------------- ADD STUDENT ----------------------
@main_blueprint.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        roll = request.form.get('roll_number', '').strip()
        if not name or not roll:
            flash('Name and Roll Number are required.', 'danger')
            return redirect(url_for('main.add_student'))

        student = Student(name=name, roll_number=roll, user_id=current_user.id)
        db.session.add(student)
        try:
            db.session.commit()
            flash('Student added successfully!', 'success')
            return redirect(url_for('main.index'))
        except IntegrityError:
            db.session.rollback()
            flash('Roll number already exists.', 'danger')
            return redirect(url_for('main.add_student'))
    return render_template('add_student.html')


# ---------------------- ADD / UPDATE GRADE ----------------------
@main_blueprint.route('/student/<int:sid>/grade', methods=['POST'])
@login_required
def add_grade(sid):
    student = Student.query.get_or_404(sid)
    if student.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('main.index'))

    subject = request.form.get('subject')
    try:
        score = float(request.form.get('score'))
    except Exception:
        flash('Score must be a number (0–100).', 'danger')
        return redirect(url_for('main.student_details', sid=sid))

    if not (0 <= score <= 100):
        flash('Score must be between 0 and 100.', 'danger')
        return redirect(url_for('main.student_details', sid=sid))

    grade = Grade.query.filter_by(student_id=sid, subject=subject).first()
    if grade:
        grade.score = score
    else:
        db.session.add(Grade(student_id=sid, subject=subject, score=score))

    db.session.commit()
    flash('Grade saved successfully!', 'success')
    return redirect(url_for('main.student_details', sid=sid))


# ---------------------- STUDENT DETAILS ----------------------
@main_blueprint.route('/student/<int:sid>')
@login_required
def student_details(sid):
    student = Student.query.get_or_404(sid)
    if student.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))

    grades_map = {g.subject: g.score for g in student.grades}
    avg = student.average()

    return render_template('student_details.html', student=student, subjects=SUBJECTS,
                           grades=grades_map, avg=avg)


# ---------------------- REPORT CARD (PDF + LINE GRAPH IN MEMORY) ----------------------
@main_blueprint.route('/student/<int:sid>/report')
@login_required
def generate_pdf(sid):
    student = Student.query.get_or_404(sid)
    if student.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))

    grades = {g.subject: g.score for g in student.grades}
    avg = round(student.average() or 0, 2)
    grade_letter = student.grade_letter() or 'N/A'

    # 🟢 Generate line chart in memory
    img_bytes = BytesIO()
    if grades:
        subjects = list(grades.keys())
        scores = list(grades.values())
        plt.figure(figsize=(5, 3))
        plt.plot(subjects, scores, marker='o', color='blue', linewidth=2)
        plt.title('Performance Line Chart')
        plt.xlabel('Subjects')
        plt.ylabel('Marks')
        plt.ylim(0, 100)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(img_bytes, format='png')
        plt.close()
    img_bytes.seek(0)
    chart_image = ImageReader(img_bytes)

    # 🟢 Generate PDF in memory
    pdf_bytes = BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, height - 50, "Student Performance Report")

    c.setFont("Helvetica", 12)
    y = height - 100
    c.drawString(50, y, f"Name: {student.name}")
    y -= 20
    c.drawString(50, y, f"Roll Number: {student.roll_number}")
    y -= 20
    c.drawString(50, y, f"Average Marks: {avg}")
    y -= 20
    c.drawString(50, y, f"Grade: {grade_letter}")

    y -= 40
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, "Subject")
    c.drawString(250, y, "Marks")

    c.setFont("Helvetica", 12)
    for subj, score in grades.items():
        y -= 20
        c.drawString(50, y, subj)
        c.drawString(250, y, str(score))

    if grades:
        c.drawImage(chart_image, 100, 120, width=400, height=200)

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 50, "Generated by Student Performance Tracker")

    c.save()
    pdf_bytes.seek(0)

    return send_file(
        pdf_bytes,
        as_attachment=True,
        download_name=f"{student.name}_report.pdf",
        mimetype='application/pdf'
    )


# ---------------------- DELETE STUDENT ----------------------
@main_blueprint.route('/student/<int:sid>/delete', methods=['POST'])
@login_required
def delete_student(sid):
    student = Student.query.get_or_404(sid)
    if student.user_id != current_user.id:
        flash('Unauthorized delete.', 'danger')
        return redirect(url_for('main.index'))

    db.session.delete(student)
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('main.index'))


# ---------------------- REPORTS ----------------------
@main_blueprint.route('/reports')
@login_required
def reports():
    students = Student.query.filter_by(user_id=current_user.id).all()
    SUBJECTS_LIST = sorted({g.subject for s in students for g in s.grades}) or SUBJECTS

    subject_avgs, toppers = {}, {}
    for subj in SUBJECTS_LIST:
        grades = [g for s in students for g in s.grades if g.subject == subj]
        if grades:
            scores = [g.score for g in grades]
            subject_avgs[subj] = round(sum(scores) / len(scores), 2)
            toppers[subj] = max(grades, key=lambda x: x.score).student
        else:
            subject_avgs[subj], toppers[subj] = None, None

    ranked = sorted(students, key=lambda s: s.total_marks() or 0, reverse=True)
    top5 = ranked[:5]
    bottom5 = ranked[-5:][::-1]
    grade_count = dict(Counter([s.grade_letter() for s in students if s.grades]))

    return render_template('reports.html',
                           subjects=SUBJECTS_LIST,
                           subject_avgs=subject_avgs,
                           toppers=toppers,
                           top_names=[s.name for s in top5],
                           top_scores=[s.total_marks() for s in top5],
                           bottom_names=[s.name for s in bottom5],
                           bottom_scores=[s.total_marks() for s in bottom5],
                           grade_count=grade_count)


# ---------------------- LEADERBOARD ----------------------
@main_blueprint.route('/leaderboard')
@login_required
def leaderboard():
    students = Student.query.filter_by(user_id=current_user.id).all()
    ranked = sorted(students, key=lambda s: s.average() or 0, reverse=True)
    return render_template('leaderboard.html', students=ranked)


# ---------------------- BULK UPLOAD ----------------------
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)

@main_blueprint.route('/bulk-upload', methods=['GET', 'POST'])
@login_required
def bulk_upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('Please select a CSV file.', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.csv'):
            flash('Only CSV files are allowed.', 'danger')
            return redirect(request.url)

        path = os.path.join(UPLOAD_DIR, filename)
        file.save(path)

        try:
            df = pd.read_csv(path)
        except Exception as e:
            flash(f'Error reading CSV: {e}', 'danger')
            return redirect(request.url)

        created = 0
        for _, row in df.iterrows():
            name = str(row.get('name') or row.get('Name') or '').strip()
            roll = str(row.get('roll_number') or row.get('Roll') or '').strip()
            if not name or not roll:
                continue

            student = Student.query.filter_by(roll_number=roll, user_id=current_user.id).first()
            if not student:
                student = Student(name=name, roll_number=roll, user_id=current_user.id)
                db.session.add(student)
                db.session.flush()

            for subj in SUBJECTS:
                if subj in row and not pd.isna(row[subj]):
                    score = float(row[subj])
                    grade = Grade.query.filter_by(student_id=student.id, subject=subj).first()
                    if grade:
                        grade.score = score
                    else:
                        db.session.add(Grade(student_id=student.id, subject=subj, score=score))
            created += 1

        db.session.commit()
        flash(f'Successfully processed {created} students from CSV!', 'success')
        return redirect(url_for('main.index'))

    return render_template('bulk_upload.html')


# ---------------------- AUTH ----------------------
@main_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        if not username or not password:
            flash('Username and password required', 'danger')
            return redirect(url_for('main.register'))

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username already exists. Please choose another.', 'warning')
            return redirect(url_for('main.register'))

        user = User(username=username, role='teacher')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can log in now.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')


@main_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully', 'success')
            return redirect(url_for('main.index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')


@main_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('main.login'))
