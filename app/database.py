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


# Use examID as PK because the auto increment only able with PK
# Update: using examCourseSectionCode as PK
class ExamDetails(db.Model):
    __tablename__ = 'ExamDetails'
    # examID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    examDate = db.Column(db.Date, nullable=False)
    examDay = db.Column(db.String(10), nullable=False)
    examStartTime = db.Column(db.String(20), nullable=False)
    examEndTime = db.Column(db.String(20), nullable=False)
    examProgramCode = db.Column(db.String(10), nullable=False)
    examCourseSectionCode = db.Column(db.String(20), primary_key=True,)
    examLecturer = db.Column(db.String(255), nullable=False)
    examTotalStudent = db.Column(db.Integer, nullable=False)
    examVenue = db.Column(db.String(50), nullable=True)
    '''
    examID INT AUTO_INCREMENT PRIMARY KEY,
    CREATE TABLE ExamDetails (
        examDate DATE,
        examDay VARCHAR(10),
        examStartTime VARCHAR(20),
        examEndTime VARCHAR(20),
        examProgramCode VARCHAR(10),
        examCourseSectionCode VARCHAR(20) PRIMARY KEY,
        examLecturer VARCHAR(255),
        examTotalStudent INT,
        examVenue VARCHAR(50)
    );

    '''

class LecturerDetails(db.Model):
    __tablename__ = 'LecturerDetails'
    lecturerID = db.Column(db.String(20), primary_key=True)
    lecturerName = db.Column(db.String(100))
    lecturerDepartment =db.Column(db.String(100))
    lecturerEmail = db.Column(db.String(100))
    lecturerContact =db.Column(db.Integer)
    '''
    CREATE TABLE LecturerDetails (  
        lecturerID VARCHAR(20) PRIMARY KEY,
        lecturerName VARCHAR(100),
        lecturerDepartment VARCHAR(100),
        lecturerEmail VARCHAR(100),
        lecturerContact INT
    );
    '''