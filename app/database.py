from app import db
from sqlalchemy.orm import Mapped, mapped_column
# db.String
# db.Date -> date format
# db.Time -> time format
# db.Integer -> number

# In MySQL
# SHOW DATABASES;               -> display out all the database created
# USE WM05$InvigilateX;         -> use this database
# SHOW TABLES;                  -> display out all the table created
# DROP TABLE (tableName);       -> to delete that table
# SELECT * FROM (tableName);    -> display out that table data
# UPDATE User SET userEmail='p21013604@student.newinti.edu.my' WHERE userId='123'; -> changing the data
# UPDATE Lecturer SET lecturerEmail='p21013604@student.newinti.edu.my' WHERE lecturerId='123'; 


class User(db.Model):
    __tablename__ = 'User'
    userId = db.Column(db.String(20), primary_key=True) # Refer to Staff ID
    userName = db.Column(db.String(255))                # Refer to Staff Name
    userDepartment = db.Column(db.String(60))           # Lecturer and Dean have this selection
    userLevel = db.Column(db.Integer)                   # Lecturer = 1, Dean = 2, HOP = 3, Admin = 4
    userEmail = db.Column(db.String(50))                # Refer to Staff INTI email
    userContact = db.Column(db.String(15))              # Refer to Staff Contact Number
    userPassword = db.Column(db.String(255))            # Refer to Staff Password
    userStatus = db.Column(db.String(15))               # Refer to Staff Account Status, if by self register as 'Active', if by upload as 'Deactived"
    '''
    CREATE TABLE User (
        userId VARCHAR(20) NOT NULL PRIMARY KEY,
        userName VARCHAR(255),
        userDepartment VARCHAR(60),
        userLevel INT,
        userEmail VARCHAR(50),
        userContact VARCHAR(15),
        userPassword VARCHAR(255),
        userStatus VARCHAR(15)
    );
    '''

# Use examID as PK because the auto increment only able with PK
# Update: using examCourseSectionCode as PK
class Exam(db.Model):
    __tablename__ = 'Exam'
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
    CREATE TABLE Exam (
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

class LecturerTimetable(db.Model):
    __tablename__ = 'LecturerTimetable'
    lecturerId = db.Column(db.String(20), primary_key=True)
    lecturerMon = db.Column(db.String(255), nullable=False)
    lecturerTues = db.Column(db.String(255), nullable=False)
    lecturerWed = db.Column(db.String(255), nullable=False)
    lecturerThurs = db.Column(db.String(255), nullable=False)
    lecturerFri = db.Column(db.String(255), nullable=False)
    '''
    CREATE TABLE LecturerTimetable (
        lecturerId VARCHAR(20) NOT NULL,
        lecturerMon VARCHAR(255) NOT NULL,
        lecturerTues VARCHAR(255) NOT NULL,
        lecturerWed VARCHAR(255) NOT NULL,
        lecturerThurs VARCHAR(255) NOT NULL,
        lecturerFri VARCHAR(255) NOT NULL,
        PRIMARY KEY (lecturerId)
    );
    '''

class Invigilation(db.Model):
    __tablename__ = 'Invigilation'
    invigilationCourseSectionCode = db.Column(db.String(20), primary_key=True)
    invigilationLecturerId = db.Column(db.String(20), nullable=False)
    invigilationInvigilatorId1 = db.Column(db.String(20), nullable=False)
    invigilationInvigilatorId2 = db.Column(db.String(20), nullable=False)
    invigilationStartTime = db.Column(db.String(20), nullable=False)
    invigilationEndTime = db.Column(db.String(20), nullable=False)
    invigilationCheckIn = db.Column(db.String(20), nullable=False)
    invigilationCheckOut = db.Column(db.String(20), nullable=False)
    invigilationProgramCode = db.Column(db.String(10), nullable=False)
    invigilationTotalCandidates = db.Column(db.Integer, nullable=False)
    invigilationVenue = db.Column(db.String(50), nullable=True)
    '''
    CREATE TABLE Invigilation (
        invigilationCourseSectionCode VARCHAR(20) PRIMARY KEY,
        invigilationLecturerId VARCHAR(20) NOT NULL,
        invigilationInvigilatorId1 VARCHAR(20) NOT NULL,
        invigilationInvigilatorId2 VARCHAR(20) NOT NULL,
        invigilationStartTime VARCHAR(20) NOT NULL,
        invigilationEndTime VARCHAR(20) NOT NULL,
        invigilationCheckIn VARCHAR(20) NOT NULL,
        invigilationCheckOut VARCHAR(20) NOT NULL,
        invigilationProgramCode VARCHAR(10) NOT NULL,
        invigilationTotalCandidates INT NOT NULL,
        invigilationVenue VARCHAR(50)
    );
    '''

class Department(db.Model):
    __tablename__ = 'Department'
    departmentCode = db.Column(db.String(10), primary_key=True)
    departmentName = db.Column(db.String(60), nullable=False)
    departmentRatio = db.Column(db.Integer)
    '''
    CREATE TABLE Department (
        departmentCode VARCHAR(10) PRIMARY KEY,
        departmentName VARCHAR(60) NOT NULL,
        departmentRatio INT
    );
    '''

class Course(db.Model):
    __tablename__ = 'Course'
    courseCodeSection = db.Column(db.String(20), primary_key=True)
    courseCode = db.Column(db.String(10))
    courseSection = db.Column(db.String(10), nullable=False)
    courseName = db.Column(db.String(50), nullable=False)
    courseHour = db.Column(db.Integer)
    '''
    CREATE TABLE Course (
        courseCodeSection VARCHAR(20) PRIMARY KEY,
        courseCode VARCHAR(10) NOT NULL,
        courseSection VARCHAR(10) NOT NULL,
        courseName VARCHAR(50) NOT NULL,
        courseHour INT
    );
    '''



