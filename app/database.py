from app import db
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String  # correct import
# db.String  -> string
# db.Date    -> date format
# db.Time    -> time format
# db.Integer -> number

# SHOW DATABASES;               -> display out all the database created
# USE WM05$InvigilateX;         -> use this database
# SHOW TABLES;                  -> display out all the table created
# DROP TABLE (tableName);       -> to delete that table
# SELECT * FROM (tableName);    -> display out that table data
# UPDATE User SET userEmail='p21013604@student.newinti.edu.my' WHERE userId='ADMIN'; -> changing the data

class User(db.Model):
    __tablename__ = 'User'
    userId = db.Column(db.String(20), primary_key=True) # [PK]Refer to Staff ID
    userName = db.Column(db.String(255))                # Refer to Staff Name
    userDepartment = db.Column(db.String(60))           # [FK] Refer to Staff Department
    userLevel = db.Column(db.Integer)                   # Lecturer = 1, Dean = 2, HOP = 3, Admin = 4
    userEmail = db.Column(db.String(50))                # Refer to Staff INTI email
    userContact = db.Column(db.String(15))              # Refer to Staff Contact Number
    userGender = db.Column(db.String(10))               # Refer to Staff Gender
    userPassword = db.Column(db.String(255))            # Refer to Staff Password
    userStatus = db.Column(db.String(15))               # Refer to Staff Account Status, if by self register as 'Active', else as 'Deactived"
    '''
    CREATE TABLE User (
        userId VARCHAR(20) NOT NULL PRIMARY KEY,
        userName VARCHAR(255),
        userDepartment VARCHAR(60),
        userLevel INT,
        userEmail VARCHAR(50),
        userContact VARCHAR(15),
        userGender VARCHAR(10),
        userPassword VARCHAR(255),
        userStatus VARCHAR(15)
    );
    '''

class Exam(db.Model):
    __tablename__ = 'Exam'
    examId = db.Column(db.Integer, primary_key=True)                   # [PK] Refer to Exam ID
    examDate = db.Column(db.Date, nullable=True)                       # Refer to Exam Date
    examDay = db.Column(db.String(10), nullable=False)                 # Refer to Exam Day
    examStartTime = db.Column(db.String(20), nullable=False)           # Refer to Exam StartTime
    examEndTime = db.Column(db.String(20), nullable=False)             # Refer to Exam EndTime
    examCourseCodeSection = db.Column(db.String(20))                   # [FK] Refer to examCourseCodeSection
    examProgramCode = db.Column(db.String(10), nullable=False)         # Refer to Course DepartmentCode
    examPracticalLecturer = db.Column(db.String(255), nullable=False)  # Refer to Course Practical Lecturer
    examTutorialLecturer = db.Column(db.String(255), nullable=False)   # Refer to Course Tutorial Lecturer
    examTotalStudent = db.Column(db.Integer, nullable=False)           # Refer to Course Total Number of Students  
    examVenue = db.Column(db.String(50), nullable=True)                # Refer to Exam Venue
    '''
    CREATE TABLE Exam (
        examId INT AUTO_INCREMENT PRIMARY KEY,
        examDate DATE,
        examDay VARCHAR(10),
        examStartTime VARCHAR(20),
        examEndTime VARCHAR(20),
        examCourseCodeSection VARCHAR(20),
        examProgramCode VARCHAR(10),
        examPracticalLecturer VARCHAR(255),
        examTutorialLecturer VARCHAR(255),
        examTotalStudent INT,
        examVenue VARCHAR(50)
    );
    '''

class Department(db.Model):
    __tablename__ = 'Department'
    departmentCode = db.Column(db.String(10), primary_key=True)  # [PK] Refer to Department Code
    departmentName = db.Column(db.String(60), nullable=False)    # Refer to Department Name
    '''
    CREATE TABLE Department (
        departmentCode VARCHAR(10) PRIMARY KEY,
        departmentName VARCHAR(60) NOT NULL
    );
    '''

class Venue(db.Model):
    __tablename__ = 'Venue'
    venueNumber = db.Column(db.String(10), primary_key=True)  # [PK] Refer to VenueNumber
    venueFloor = db.Column(db.String(10), nullable=False)     # Refer to the Floor of Venue
    venueCapacity = db.Column(db.Integer, nullable=False)     # Refer to the Capacity of Venue
    venueStatus = db.Column(db.String(15), nullable=False)    # Refer to Status of Venue {'Available', 'Unavailable', 'In Service'}
    '''
    CREATE TABLE Venue (
        venueNumber VARCHAR(10) PRIMARY KEY,
        venueFloor VARCHAR(10) NOT NULL,
        venueCapacity INT NOT NULL,
        venueStatus VARCHAR(15) NOT NULL
    );
    '''

class Course(db.Model):
    __tablename__ = 'Course'
    courseCodeSection = db.Column(db.String(20), primary_key=True)   # [PK] Refer to CourseCodeSection
    courseCode = db.Column(db.String(10), nullable=False)            # Refer to CourseCode
    courseSection = db.Column(db.String(10), nullable=False)         # Refer to CourseSection
    courseDepartment = db.Column(db.String(60), nullable=False)      # Refer to CourseDepartment
    courseName = db.Column(db.String(50), nullable=False)            # Refer to CourseName
    courseHour = db.Column(db.Integer, nullable=False)               # Refer to CourseHour
    coursePractical = db.Column(db.String(255), nullable=False)      # Refer to Course Practical Lecturer
    courseTutorial = db.Column(db.String(255), nullable=False)       # Refer to Course Tutorial Lecturer
    courseStudent = db.Column(db.Integer, nullable=False)            # Refer to Course Total Number of Students
    '''
    CREATE TABLE Course (
        courseCodeSection VARCHAR(20) PRIMARY KEY,
        courseCode VARCHAR(10) NOT NULL,
        courseSection VARCHAR(10) NOT NULL,
        courseDepartment VARCHAR(60) NOT NULL,
        courseName VARCHAR(50) NOT NULL,
        courseHour INT,
        coursePractical VARCHAR(255) NOT NULL,
        courseTutorial VARCHAR(255) NOT NULL,
        courseStudent INT
    );
    '''









# Need Double Check, Haven't Record In Database
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

# Need Double Check, Haven't Record In Database
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











