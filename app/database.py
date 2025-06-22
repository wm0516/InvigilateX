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
    # Refer to Staff ID
    userId = db.Column(db.String(20), primary_key=True)
    # Refer to Staff Name
    userName = db.Column(db.String(255))
    # Lecturer and Dean have this selection
    userDepartment = db.Column(db.String(40))
    # Lecturer = 1, Dean = 2 (Dean with higher level to access of)
    userLevel = db.Column(db.Integer)
    # Refer to Staff INTI email
    userEmail = db.Column(db.String(50))
    # Refer to Staff Contact Number
    userContact = db.Column(db.String(15))
    # Refer to Staff Password
    userPassword = db.Column(db.String(255))
    # Refer to Staff Account Status, if by self register as 'Active', if by upload as 'Deactived"
    userStatus = db.Column(db.String(15))
    '''
    CREATE TABLE User (
        userId VARCHAR(20) NOT NULL PRIMARY KEY,
        userName VARCHAR(255),
        userDepartment VARCHAR(20),
        userLevel INT,
        userEmail VARCHAR(50),
        userContact VARCHAR(15),
        userPassword VARCHAR(20),
        userStatus VARCHAR(15)
    );
    '''

# Admin database
class Admin(db.Model):
    __tablename__ = 'Admin'
    adminId = db.Column(db.String(20), primary_key=True)
    adminName = db.Column(db.String(255))
    # Department and Level admin set by default as admin
    adminDepartment = db.Column(db.String(20))
    adminEmail = db.Column(db.String(50))
    adminContact = db.Column(db.String(15))
    adminPassword = db.Column(db.String(255))
    '''
    CREATE TABLE Admin (
        adminId VARCHAR(20) PRIMARY KEY,
        adminName VARCHAR(255),
        adminDepartment VARCHAR(20),
        adminEmail VARCHAR(50),
        adminContact VARCHAR(15),
        adminPassword VARCHAR(255)
    );
    '''

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











# (Not Used) Dean database
class Dean(db.Model):
    __tablename__ = 'Dean'
    deanId = db.Column(db.String(20), primary_key=True)
    deanName = db.Column(db.String(255))
    # Department and Level dean set by default
    deanDepartment = db.Column(db.String(20))
    deanLevel = db.Column(db.Integer) # Level mean access (dean with middle access, level 2 (able to view own lecturer))
    deanEmail = db.Column(db.String(50))
    deanContact = db.Column(db.String(15))
    deanPassword = db.Column(db.String(255))
    '''
    CREATE TABLE Dean (
        deanId VARCHAR(20) PRIMARY KEY,
        deanName VARCHAR(255),
        deanDepartment VARCHAR(20),
        deanLevel INT,
        deanEmail VARCHAR(50),
        deanContact VARCHAR(15),
        deanPassword VARCHAR(255)
    );
    '''

# (Not Used) Lecturer database
class Lecturer(db.Model):
    __tablename__ = 'Lecturer'
    lecturerId = db.Column(db.String(20), primary_key=True)
    lecturerName = db.Column(db.String(255))
    lecturerDepartment =db.Column(db.String(20))
    lecturerLevel = db.Column(db.Integer) # Level mean access (admin with lower access, level 1 (only able to view own data))
    lecturerEmail = db.Column(db.String(50))
    lecturerContact = db.Column(db.String(15))
    lecturerPassword = db.Column(db.String(255))
    '''
    CREATE TABLE Lecturer (
        lecturerId VARCHAR(20) PRIMARY KEY,
        lecturerName VARCHAR(255),
        lecturerDepartment VARCHAR(100),
        lecturerLevel INT,
        lecturerEmail VARCHAR(50),
        lecturerContact VARCHAR(15),
        lecturerPassword VARCHAR(255)
    );
    '''










'''
CREATE TABLE Users (
    id INTEGER PRIMARY KEY,
    number VARCHAR(20) UNIQUE,
    name VARCHAR(30),
    email VARCHAR(30) UNIQUE,
    department VARCHAR(15),
    status VARCHAR(10),
    role VARCHAR(10) NOT NULL CHECK (role IN ('admin', 'lecturer', 'invigilator')),
    password_hash VARCHAR(255)
);

CREATE TABLE Timetable (
    userId INTEGER,
    day VARCHAR(10),
    classStart VARCHAR(10),
    classEnd VARCHAR(10),
    FOREIGN KEY (userId) REFERENCES Users(id)
);

CREATE TABLE InvigilatorStatus (
    id INTEGER PRIMARY KEY,
    status VARCHAR(20) NOT NULL
);

CREATE TABLE Invigilation (
    id INTEGER PRIMARY KEY,
    invigilatorId INTEGER,
    statusId INTEGER,
    maxSlot INTEGER,
    availableSlot INTEGER,
    unavailableSlot INTEGER,
    FOREIGN KEY (invigilatorId) REFERENCES Users(id),
    FOREIGN KEY (statusId) REFERENCES InvigilatorStatus(id)
);

CREATE TABLE Exam (
    id INTEGER PRIMARY KEY,
    courseSectionCode VARCHAR(20),
    invigilatorId1 INTEGER,
    invigilatorId2 INTEGER,
    examDate DATE,
    examTime VARCHAR(10),
    uploadedBy INTEGER,
    FOREIGN KEY (invigilatorId1) REFERENCES Users(id),
    FOREIGN KEY (invigilatorId2) REFERENCES Users(id),
    FOREIGN KEY (uploadedBy) REFERENCES Users(id)
);






'''