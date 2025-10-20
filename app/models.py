from .extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


# ---------------------- USER MODEL ----------------------
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='teacher')  # 'teacher' or 'admin'
    assigned_year = db.Column(db.Integer, nullable=True)
    assigned_class = db.Column(db.String(50), nullable=True)

    # link to students added by this user
    students = db.relationship('Student', backref='user', cascade='all, delete-orphan')

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


# ---------------------- STUDENT MODEL ----------------------
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=True)
    class_name = db.Column(db.String(50), nullable=True)

    # link to teacher who added this student
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    grades = db.relationship('Grade', backref='student', cascade='all, delete-orphan')

    def total_marks(self):
        return sum(g.score for g in self.grades) if self.grades else 0

    def percentage(self):
        if not self.grades:
            return 0
        return round(self.total_marks() / (len(self.grades) * 100) * 100, 2)

    def grade_letter(self):
        p = self.percentage()
        if p >= 80:
            return 'A'
        elif p >= 60:
            return 'B'
        elif p >= 40:
            return 'C'
        else:
            return 'F'

    def average(self):
        if not self.grades:
            return None
        return round(self.total_marks() / len(self.grades), 2)


# ---------------------- GRADE MODEL ----------------------
class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    score = db.Column(db.Float, nullable=False)
