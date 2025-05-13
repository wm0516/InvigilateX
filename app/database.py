from app import db

# db.String
# db.Date -> date format
# db.Time -> time format
# db.Integer -> number

class User(db.Model):
    __tablename__ = 'User'
    userid = db.Column(db.String(50), primary_key=True)
    username = db.Column(db.String(100))
    department = db.Column(db.String(100))
    email = db.Column(db.String(100))
    contact = db.Column(db.Integer(20))
    password = db.Column(db.String(255))

class Exam(db.Model):
    __tablename__ = 'Exam'
    examCourseCode = db.Column(db.String(50), primary_key=True)
    examProgram = db.Column(db.String(100))
    # Default as 1, when over students only will have 2
    examSection = db.Column(db.String(100))
    examDate = db.Column(db.Date(100))
    examTimePeriod = db.Column(db.Time(100))
    examLecturer = db.Column(db.String(100))
    examNoOfCandidates = db.Integer(db.String(100))
    examVenue = db.Column(db.String(100))




