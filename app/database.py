from app import db
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String  # correct import
from datetime import datetime, timezone
# db.String  -> string
# db.Date    -> date format
# db.Time    -> time format
# db.Integer -> number

# SHOW DATABASES;                                                                           -> display out all the database created
# USE WM05$InvigilateX;                                                                     -> use this database
# SHOW TABLES;                                                                              -> display out all the table created
# DROP TABLE (tableName);                                                                   -> to delete that table
# SELECT * FROM (tableName);                                                                -> display out that table data
# UPDATE User SET userEmail='p21013604@student.newinti.edu.my' WHERE userId='ADMIN1';       -> changing the data
# DELETE FROM Exam WHERE examId = '1';                                                      -> remove certain row of data
# NOT NULL = MUST HAVE DATA 
# NULL = OPTIONAL HAVE DATA






class Department(db.Model):
    __tablename__ = 'Department'
    departmentCode = db.Column(db.String(10), primary_key=True)                     # [PK] Department Code
    departmentName = db.Column(db.String(60), nullable=False)                       # Department Name
    deanId = db.Column(db.String(20), db.ForeignKey('User.userId'), nullable=True)  # Dean (FK to User)
    hopId = db.Column(db.String(20), db.ForeignKey('User.userId'), nullable=True)   # HOP (FK to User)

    # Relationship
    dean = db.relationship("User", foreign_keys=[deanId], backref="dean_of_departments")
    hop = db.relationship("User", foreign_keys=[hopId], backref="hop_of_departments")
    '''
    CREATE TABLE Department (
        departmentCode VARCHAR(10) NOT NULL PRIMARY KEY,
        departmentName VARCHAR(60) NOT NULL,
        deanId VARCHAR(20) NULL,
        hopId VARCHAR(20) NULL
    );
    '''


class User(db.Model):
    __tablename__ = 'User'
    userId = db.Column(db.String(20), primary_key=True)                                                               # [PK]Refer to Staff ID
    userDepartment = db.Column(db.String(10), db.ForeignKey('Department.departmentCode'))                             # [FK] Refer to Staff Department
    userName = db.Column(db.String(255))                                                                              # Refer to Staff Name
    userLevel = db.Column(db.Integer)                                                                                 # Lecturer = 1, Dean = 2, HOP = 3, Admin = 4
    userEmail = db.Column(db.String(255))                                                                             # Refer to Staff INTI email
    userContact = db.Column(db.String(15))                                                                            # Refer to Staff Contact Number [Use String to Store '01', If Use INT Can't Store '0']
    userGender = db.Column(db.String(10))                                                                             # Refer to Staff Gender
    userPassword = db.Column(db.String(255))                                                                          # Refer to Staff Password
    userStatus = db.Column(db.Boolean, default=False)                                                                 # Refer to Staff Account Status, if by self register as 'Active', else as 'Deactived"
    userRegisterDateTime = db.Column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))          # Refer to user register time (if more than 2 years deactivated will be deleted automatically)
    userCumulativeHours = db.Column(db.Float, default=0.0, nullable=False)                                            # Refer to the total hours of invigilator (using float allow store with mins, and each of them with min 36 hours)
    userPendingCumulativeHours = db.Column(db.Float, default=0.0, nullable=False)                                     # Refer to the pending total hours of invigilator
    
    # Relationship
    department = db.relationship("Department", backref="users", foreign_keys=[userDepartment])
    '''
    CREATE TABLE User (
        userId VARCHAR(20) PRIMARY KEY,
        userName VARCHAR(255),
        userGender VARCHAR(10),
        userEmail VARCHAR(255),
        userContact VARCHAR(15),
        userLevel INT,
        userDepartment VARCHAR(10),
        userPassword VARCHAR(255),
        userStatus BOOLEAN DEFAULT FALSE,
        userRegisterDateTime DATETIME,
        userCumulativeHours FLOAT NOT NULL DEFAULT 0.0,
        userPendingCumulativeHours FLOAT NOT NULL DEFAULT 0.0,
        FOREIGN KEY (userDepartment) REFERENCES Department(departmentCode)
    );
    '''


class Venue(db.Model):
    __tablename__ = 'Venue'
    venueNumber = db.Column(db.String(10), primary_key=True)                                     # [PK] Venue identifier
    venueFloor = db.Column(db.String(10), nullable=False)                                        # Floor of venue
    venueCapacity = db.Column(db.Integer, nullable=False)                                        # Capacity of venue
    venueStatus = db.Column(db.Enum('AVAILABLE', 'UNAVAILABLE', 'IN SERVICE'), nullable=False)   # {'Available', 'Unavailable', 'In Service'}
    
    # Relationship
    availabilities = db.relationship("VenueAvailability", back_populates="venue")
    exams = db.relationship("Exam", back_populates="venue")
    '''
    CREATE TABLE Venue (
        venueNumber VARCHAR(10) NOT NULL PRIMARY KEY,
        venueFloor VARCHAR(10) NOT NULL,
        venueCapacity INT NOT NULL,
        venueStatus ENUM('AVAILABLE','UNAVAILABLE','IN SERVICE') NOT NULL
    );
    '''


class VenueAvailability(db.Model):
    __tablename__ = 'VenueAvailability'
    availabilityId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    venueNumber = db.Column(db.String(10), db.ForeignKey('Venue.venueNumber'), nullable=False)
    startDateTime = db.Column(db.DateTime, nullable=False)   # Start date & time
    endDateTime = db.Column(db.DateTime, nullable=False)     # End date & time
    status = db.Column(db.Enum('AVAILABLE', 'UNAVAILABLE', 'IN SERVICE'), nullable=False)
    
    # Relationship
    venue = db.relationship("Venue", back_populates="availabilities")
    '''
    CREATE TABLE VenueAvailability (
        availabilityId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        venueNumber VARCHAR(10) NOT NULL,
        startDateTime DATETIME NOT NULL,
        endDateTime DATETIME NOT NULL,
        status ENUM('AVAILABLE', 'UNAVAILABLE', 'IN SERVICE') NOT NULL,
        FOREIGN KEY (venueNumber) REFERENCES Venue(venueNumber)
    );
    '''


class Exam(db.Model):
    __tablename__ = 'Exam'
    examId = db.Column(db.Integer, primary_key=True, autoincrement=True)                        # [PK] Refer to Exam ID
    examVenue = db.Column(db.String(10), db.ForeignKey('Venue.venueNumber'), nullable=True)     # Refer to Exam Venue
    examStartTime = db.Column(db.DateTime, nullable=True)                                       # Refer to Exam StartTime
    examEndTime = db.Column(db.DateTime, nullable=True)                                         # Refer to Exam EndTime
    examNoInvigilator = db.Column(db.Integer, nullable=True)                                    # Refer to total of invigilator need for the exam sessions
    
    # Relationship
    courses = db.relationship("Course", back_populates="exam")  # many exams -> one course
    venue = db.relationship("Venue", back_populates="exams")
    '''
    CREATE TABLE Exam (
        examId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        examDate DATE NULL,
        examDay VARCHAR(10) NULL,
        examStartTime DateTime NULL,
        examEndTime DateTime NULL,
        examVenue VARCHAR(10) NULL,
        examNoInvigilator INT NULL,
        FOREIGN KEY (examVenue) REFERENCES Venue(venueNumber)
    );
    '''

class Course(db.Model):
    __tablename__ = 'Course'
    courseCodeSection = db.Column(db.String(20), primary_key=True)                                               # [PK] Refer to CourseCodeSection
    courseDepartment = db.Column(db.String(10), db.ForeignKey('Department.departmentCode'), nullable=False)      # [FK] Refer to CourseDepartment
    coursePractical = db.Column(db.String(20), db.ForeignKey('User.userId'), nullable=False)                     # [FK ]Refer to Course Practical Lecturer
    courseTutorial = db.Column(db.String(20), db.ForeignKey('User.userId'), nullable=False)                      # [FK] Refer to Course Tutorial Lecturer
    courseExamId = db.Column(db.Integer, db.ForeignKey('Exam.examId'), nullable=True)                            # Refer to courseExamStatus whether have exam or not
    courseCode = db.Column(db.String(10), nullable=False)                                                        # Refer to CourseCode
    courseSection = db.Column(db.String(10), nullable=False)                                                     # Refer to CourseSection
    courseName = db.Column(db.String(50), nullable=False)                                                        # Refer to CourseName
    courseHour = db.Column(db.Integer, nullable=False)                                                           # Refer to CourseHour
    courseStudent = db.Column(db.Integer, nullable=False)                                                        # Refer to Course Total Number of Students
    
    # Relationship
    department = db.relationship("Department", backref="courses")
    practicalLecturer = db.relationship("User", foreign_keys=[coursePractical])
    tutorialLecturer = db.relationship("User", foreign_keys=[courseTutorial])
    exam = db.relationship("Exam", back_populates="course") # one course -> one exam
    '''
    CREATE TABLE Course (
        courseCodeSection VARCHAR(20) NOT NULL PRIMARY KEY,
        courseCode VARCHAR(10) NOT NULL,
        courseSection VARCHAR(10) NOT NULL,
        courseName VARCHAR(50) NOT NULL,
        courseHour INT NOT NULL,
        courseStudent INT NOT NULL,
        courseDepartment VARCHAR(10) NOT NULL,
        coursePractical VARCHAR(20) NOT NULL,
        courseTutorial VARCHAR(20) NOT NULL,
        courseExamId INT NULL,
        FOREIGN KEY (courseDepartment) REFERENCES Department(departmentCode),
        FOREIGN KEY (coursePractical) REFERENCES User(userId),
        FOREIGN KEY (courseTutorial) REFERENCES User(userId),
        FOREIGN KEY (courseExamId) REFERENCES Exam(examId)
    );
    '''

class InvigilationReport(db.Model):
    __tablename__ = 'InvigilationReport'
    invigilationReportId = db.Column(db.Integer, primary_key=True, autoincrement=True)      # [PK] Refer to Invigilation Report ID
    examId = db.Column(db.Integer, db.ForeignKey('Exam.examId'), nullable=False)            # [FK] Refer to Which Exam, and with the details of 
    remarks = db.Column(db.Text, nullable=True)                                             # Refer to any remarks of exam sessions

    # Relationship
    exam = db.relationship("Exam", backref="invigilation_reports")
    attendances = db.relationship("InvigilatorAttendance", backref="report", cascade="all, delete-orphan")
    '''
    CREATE TABLE InvigilationReport (
        invigilationReportId INT AUTO_INCREMENT PRIMARY KEY,
        examId INT NOT NULL,
        remarks TEXT NULL,
        FOREIGN KEY (examId) REFERENCES Exam(examId)
    );  
    '''


class InvigilatorAttendance(db.Model):
    __tablename__ = 'InvigilatorAttendance'
    attendanceId = db.Column(db.Integer, primary_key=True, autoincrement=True)                                     # [PK] Refer to Attendance ID
    reportId = db.Column(db.Integer, db.ForeignKey('InvigilationReport.invigilationReportId'), nullable=False)     # [FK] Refer to Invigilation Report with the exam details
    invigilatorId = db.Column(db.String(20), db.ForeignKey('User.userId'), nullable=False)                         # [FK] Refer to which invigilator in charge
    checkIn = db.Column(db.DateTime, nullable=True)                                                                # Refer to invigilator check in time (must before 1 hour exam start)
    checkOut = db.Column(db.DateTime, nullable=True)                                                               # Refer to invigilator check out time (must before 1 hour exam end)
    remark = db.Column(db.Text, nullable=True)                                                                     # Refer to invigilator checkin and checkout early or late, and show exam process

    # Relationship
    invigilator = db.relationship("User")
    '''
    CREATE TABLE InvigilatorAttendance (
        attendanceId INT AUTO_INCREMENT PRIMARY KEY,
        reportId INT NOT NULL,
        invigilatorId VARCHAR(20) NOT NULL,
        checkIn DATETIME NULL,
        checkOut DATETIME NULL,
        remark TEXT NULL,
        FOREIGN KEY (reportId) REFERENCES InvigilationReport(invigilationReportId),
        FOREIGN KEY (invigilatorId) REFERENCES User(userId)
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



