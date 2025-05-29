from app import db
from sqlalchemy.orm import Mapped, mapped_column
# db.String
# db.Date -> date format
# db.Time -> time format
# db.Integer -> number

'''class User(db.Model):
    __tablename__ = 'User'
    # using the mapped[str] to set the variables
    # Else if not using in this way, need a long code to perform this logic
    userid: Mapped[str] = mapped_column(db.String(50), primary_key=True)
    username: Mapped[str] = mapped_column(db.String(100))
    department: Mapped[str] = mapped_column(db.String(100))
    email: Mapped[str] = mapped_column(db.String(100))
    contact: Mapped[int] = mapped_column(db.Integer)
    password: Mapped[str] = mapped_column(db.String(255))

    def __init__(self, userid, username, department, email, contact, password):
        self.userid = userid
        self.username = username
        self.department = department
        self.email = email
        self.contact = contact
        self.password = password'''


class User(db.Model):
    __tablename__ = 'User'
    userid = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100))
    department = db.Column(db.String(100))
    email = db.Column(db.String(100))
    contact = db.Column(db.Integer)
    password = db.Column(db.String(255))


class Exam(db.Model):
    __tablename__ = 'Exam'
    examCourseCode = db.Column(db.String(50), primary_key=True)
    examProgram = db.Column(db.String(100))
    examSection = db.Column(db.String(100))  
    examDate = db.Column(db.Date)  
    examTimePeriod = db.Column(db.Time)  
    examLecturer = db.Column(db.String(100))
    examNoOfCandidates = db.Column(db.Integer) 
    examVenue = db.Column(db.String(100)) 


class ExamSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_date = db.Column(db.Date, nullable=False)
    day = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    program = db.Column(db.String(10), nullable=False)
    course_sec = db.Column(db.String(50), nullable=False)
    lecturer = db.Column(db.String(255), nullable=False)
    num_of_students = db.Column(db.Integer, nullable=False)
    room = db.Column(db.String(50), nullable=True)



