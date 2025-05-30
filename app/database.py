from app import db
from sqlalchemy.orm import Mapped, mapped_column
# db.String
# db.Date -> date format
# db.Time -> time format
# db.Integer -> number

# Admin record after register
class Admin(db.Model):
    __tablename__ = 'Admin'
    adminId = db.Column(db.String(20), primary_key=True)
    adminName = db.Column(db.String(255))
    # Department and Level admin set by default as admin
    adminDepartment = db.Column(db.String(20)) # Level mean access (admin with higher access, level 3 (able to view all dean and lecturer))
    adminLevel = db.Column(db.String(10))
    adminEmail = db.Column(db.String(50))
    adminContact = db.Column(db.Integer)
    adminPassword = db.Column(db.String(255))

# Dean record after register 
class Dean(db.Model):
    __tablename__ = 'Dean'
    deanId = db.Column(db.String(20), primary_key=True)
    deanName = db.Column(db.String(255))
    deanDepartment = db.Column(db.String(20))
    deanLevel = db.Column(db.Integer) # Level mean access (dean with middle access, level 2 (able to view own lecturer))
    deanEmail = db.Column(db.String(50))
    deanContact = db.Column(db.Integer)
    deanPassword = db.Column(db.String(255))

class Lecturer(db.Model):
    __tablename__ = 'Lecturer'
    lecturerId = db.Column(db.String(20), primary_key=True)
    lecturerName = db.Column(db.String(100))
    lecturerDepartment =db.Column(db.String(100))
    lecturerLevel = db.Column(db.Integer) # Level mean access (admin with lower access, level 1 (only able to view own data))
    lecturerEmail = db.Column(db.String(100))
    lecturerContact =db.Column(db.Integer)
    lecturerPassword = db.Column(db.String(255))



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
