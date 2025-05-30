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
# UPDATE Admin SET adminEmail='p21013604@student.newinti.edu.my' WHERE adminId='123'; -> changing the data
# UPDATE Lecturer SET lecturerEmail='p21013604@student.newinti.edu.my' WHERE lecturerId='123'; 


class User(db.Model):
    __tablename__ = 'User'
    # Refer to Staff ID
    userId = db.Column(db.String(20), primary_key=True)
    # Refer to Staff Name
    userName = db.Column(db.String(255))
    # Lecturer and Dean have this selection, Admin will automatic set as Admin
    userDepartment = db.Column(db.String(20))
    # Lecturer = 1, Dean = 2, Admin = 3 (Admin with higher level to access of)
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
        userPassword VARCHAR(255),
        userStatus VARCHAR(15)
    );
    '''


# (Not Used) Admin database
class Admin(db.Model):
    __tablename__ = 'Admin'
    adminId = db.Column(db.String(20), primary_key=True)
    adminName = db.Column(db.String(255))
    # Department and Level admin set by default as admin
    adminDepartment = db.Column(db.String(20)) # Level mean access (admin with higher access, level 3 (able to view all dean and lecturer))
    adminLevel = db.Column(db.String(10))
    adminEmail = db.Column(db.String(50))
    adminContact = db.Column(db.String(15))
    adminPassword = db.Column(db.String(255))
    '''
    CREATE TABLE Admin (
        adminId VARCHAR(20) PRIMARY KEY,
        adminName VARCHAR(255),
        adminDepartment VARCHAR(20),
        adminLevel VARCHAR(10),
        adminEmail VARCHAR(50),
        adminContact VARCHAR(15),
        adminPassword VARCHAR(255)
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
