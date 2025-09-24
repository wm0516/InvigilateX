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
    userDepartment = db.Column(db.String(10), db.ForeignKey('Department.departmentCode'), nullable=True)              # [FK] Refer to Staff Department
    userName = db.Column(db.String(255), nullable=False)                                                              # Refer to Staff Name
    userLevel = db.Column(db.Integer, nullable=False)                                                                 # Lecturer = 1, Dean = 2, HOP = 3, Admin = 4
    userEmail = db.Column(db.String(255), nullable=False)                                                             # Refer to Staff INTI email
    userContact = db.Column(db.String(15), nullable=False)                                                            # Refer to Staff Contact Number [Use String to Store '01', If Use INT Can't Store '0']
    userGender = db.Column(db.String(10), nullable=False)                                                             # Refer to Staff Gender
    userPassword = db.Column(db.String(255), nullable=False)                                                          # Refer to Staff Password
    userStatus = db.Column(db.Integer, default=0)                                                                     # Refer to Staff Account Status, if by self register as 'Active', else as 'Deactived" (0=Deactivated, 1=Activated, 2=Deleted) 
    userRegisterDateTime = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))          # Refer to user register time (if more than 2 years deactivated will be deleted automatically)
    userCumulativeHours = db.Column(db.Float, default=0.0, nullable=False)                                            # Refer to the total hours of invigilator (using float allow store with mins, and each of them with min 36 hours)
    userPendingCumulativeHours = db.Column(db.Float, default=0.0, nullable=False)                                     # Refer to the pending total hours of invigilator
    timetable = db.relationship('Timetable', back_populates='user', uselist=False)                                    # [FK] Refer to that User with Own Timetable

    # Relationship
    department = db.relationship("Department", backref="users", foreign_keys=[userDepartment])
    '''
    CREATE TABLE User (
        userId VARCHAR(20) PRIMARY KEY,
        userDepartment VARCHAR(10) NULL,
        userName VARCHAR(255) NOT NULL,
        userLevel INT NOT NULL,
        userEmail VARCHAR(255) NOT NULL,
        userContact VARCHAR(15) NOT NULL,
        userGender VARCHAR(10) NOT NULL,
        userPassword VARCHAR(255) NOT NULL,
        userStatus INT DEFAULT 0,
        userRegisterDateTime DATETIME DEFAULT CURRENT_TIMESTAMP,
        userCumulativeHours FLOAT DEFAULT 0.0,
        userPendingCumulativeHours FLOAT DEFAULT 0.0,
        FOREIGN KEY (userDepartment) REFERENCES Department(departmentCode)
    );
    '''

class Venue(db.Model):
    __tablename__ = 'Venue'
    venueNumber = db.Column(db.String(20), primary_key=True)                                     # [PK] Venue identifier
    venueFloor = db.Column(db.String(10), nullable=False)                                        # Floor of venue
    venueCapacity = db.Column(db.Integer, nullable=False)                                        # Capacity of venue
    venueStatus = db.Column(db.Enum('AVAILABLE', 'UNAVAILABLE', 'IN SERVICE'), nullable=False)   # Venue overall status

    # Relationships
    availabilities = db.relationship("VenueAvailability", back_populates="venue")               # One Venue ↔ Many VenueAvailability
    exams = db.relationship("Exam", back_populates="venue")                                     # One Venue ↔ Many Exams
    '''
    CREATE TABLE Venue (
        venueNumber VARCHAR(20) NOT NULL PRIMARY KEY,
        venueFloor VARCHAR(10) NOT NULL,
        venueCapacity INT NOT NULL,
        venueStatus ENUM('AVAILABLE','UNAVAILABLE','IN SERVICE') NOT NULL
    );
    '''

class Exam(db.Model):
    __tablename__ = 'Exam'
    examId = db.Column(db.Integer, primary_key=True, autoincrement=True)                         # [PK] Refer to Exam ID
    examVenue = db.Column(db.String(10), db.ForeignKey('Venue.venueNumber'), nullable=True)      # Refer to Exam Venue
    examStartTime = db.Column(db.DateTime, nullable=True)                                        # Refer to Exam StartTime
    examEndTime = db.Column(db.DateTime, nullable=True)                                          # Refer to Exam EndTime
    examNoInvigilator = db.Column(db.Integer, nullable=True)                                     # Number of invigilators needed

    # Relationships
    course = db.relationship("Course", back_populates="exam", uselist=False)                     # One Exam ↔ One Course
    venue = db.relationship("Venue", back_populates="exams")                                     # Many Exams ↔ One Venue
    venue_availabilities = db.relationship("VenueAvailability", back_populates="exam")           # One Exam ↔ Many VenueAvailability
    invigilation_reports = db.relationship("InvigilationReport", backref="exam")                 # One Exam ↔ Many InvigilationReport

    '''
    CREATE TABLE Exam (
        examId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        examStartTime DATETIME NULL,
        examEndTime DATETIME NULL,
        examVenue VARCHAR(10) NULL,
        examNoInvigilator INT NULL,
        FOREIGN KEY (examVenue) REFERENCES Venue(venueNumber)
    );
    '''

class VenueAvailability(db.Model):
    __tablename__ = 'VenueAvailability'
    examVenueId = db.Column(db.Integer, primary_key=True, autoincrement=True)                 # [PK] Availability ID
    examId = db.Column(db.Integer, db.ForeignKey('Exam.examId'), nullable=False)                 # [FK] Exam ID
    venueNumber = db.Column(db.String(10), db.ForeignKey('Venue.venueNumber'), nullable=True)   # [FK] Venue Number
    startDateTime = db.Column(db.DateTime, nullable=False)                                       # Start DateTime
    endDateTime = db.Column(db.DateTime, nullable=False)                                         # End DateTime

    # Relationships
    exam = db.relationship("Exam", back_populates="venue_availabilities")
    venue = db.relationship("Venue", back_populates="availabilities")

    '''
    CREATE TABLE VenueAvailability (
        examVenueId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        examId INT NOT NULL,
        venueNumber VARCHAR(10) NULL,
        startDateTime DATETIME NOT NULL,
        endDateTime DATETIME NOT NULL,
        FOREIGN KEY (examId) REFERENCES Exam(examId),
        FOREIGN KEY (venueNumber) REFERENCES Venue(venueNumber)
    );
    '''


class Course(db.Model):
    __tablename__ = 'Course'
    courseCodeSection = db.Column(db.String(20), primary_key=True)                                              # [PK] Refer to CourseCodeSection
    courseDepartment = db.Column(db.String(10), db.ForeignKey('Department.departmentCode'), nullable=True)      # [FK] Refer to CourseDepartment
    coursePractical = db.Column(db.String(20), db.ForeignKey('User.userId'), nullable=True)                     # [FK ]Refer to Course Practical Lecturer
    courseTutorial = db.Column(db.String(20), db.ForeignKey('User.userId'), nullable=True)                      # [FK] Refer to Course Tutorial Lecturer
    courseExamId = db.Column(db.Integer, db.ForeignKey('Exam.examId'), nullable=True)                           # Refer to courseExamStatus whether have exam or not
    courseName = db.Column(db.String(50), nullable=True)                                                        # Refer to CourseName
    courseHour = db.Column(db.Integer, nullable=True)                                                           # Refer to CourseHour
    courseStudent = db.Column(db.Integer, nullable=True)                                                        # Refer to Course Total Number of Students
    courseStatus = db.Column(db.Boolean, default=True, nullable=False)                                          # Refer to Course Status, when course deleted, it will show False
    
    # Relationship
    department = db.relationship("Department", backref="course")
    practicalLecturer = db.relationship("User", foreign_keys=[coursePractical])
    tutorialLecturer = db.relationship("User", foreign_keys=[courseTutorial])   
    exam = db.relationship("Exam", back_populates="course", uselist=False)  # One Course ↔ One Exam

    '''
    CREATE TABLE Course (
        courseCodeSection VARCHAR(20) NOT NULL PRIMARY KEY,
        courseName VARCHAR(50) NULL,
        courseHour INT NULL,
        courseStudent INT NULL,
        courseDepartment VARCHAR(10) NULL,
        coursePractical VARCHAR(20) NULL,
        courseTutorial VARCHAR(20) NULL,
        courseExamId INT NULL,
        courseStatus TINYINT(1) NOT NULL DEFAULT 1,
        FOREIGN KEY (courseDepartment) REFERENCES Department(departmentCode),
        FOREIGN KEY (coursePractical) REFERENCES User(userId),
        FOREIGN KEY (courseTutorial) REFERENCES User(userId),
        FOREIGN KEY (courseExamId) REFERENCES Exam(examId)
    );
    '''

    

class InvigilationReport(db.Model):
    __tablename__ = 'InvigilationReport'
    invigilationReportId = db.Column(db.Integer, primary_key=True, autoincrement=True)           # [PK] Refer to Invigilation Report ID
    examId = db.Column(db.Integer, db.ForeignKey('Exam.examId'), nullable=False)                 # [FK] Refer to Which Exam, and with the details of
    remarks = db.Column(db.Text, nullable=True)                                                  # Remarks on session

    # Relationships
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
    checkIn = db.Column(db.DateTime, nullable=True)                                                                # Check-in time
    checkOut = db.Column(db.DateTime, nullable=True)                                                               # Check-out time
    remark = db.Column(db.Text, nullable=True)                                                                     # Notes

    # Relationships
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

# Timetable model
class Timetable(db.Model):
    __tablename__ = 'Timetable'
    timetableId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(20), db.ForeignKey('User.userId'), unique=True)
    user = db.relationship('User', back_populates='timetable')
    rows = db.relationship('TimetableRow', back_populates='timetable')
    '''
    CREATE TABLE Timetable (
        timetableId INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(20) UNIQUE,
        FOREIGN KEY (user_id) REFERENCES User(userId)
    );
    '''

# Need Double Check, Record In Database
class TimetableRow(db.Model):
    __tablename__ = 'TimetableRow'
    rowId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('Timetable.timetableId')) 
    timetable = db.relationship('Timetable', back_populates='rows')               
    filename = db.Column(db.Text, nullable=False)
    lecturerName = db.Column(db.String(255), nullable=False)
    classType = db.Column(db.String(10), nullable=False)
    classDay = db.Column(db.String(3), nullable=False)
    classTime = db.Column(db.String(20), nullable=False)
    classRoom = db.Column(db.String(20), nullable=False)
    courseName = db.Column(db.String(255), nullable=False)
    courseIntake = db.Column(db.String(50), nullable=False)
    courseCode = db.Column(db.String(20), nullable=False)
    courseSection = db.Column(db.String(20), nullable=False)
    classWeekRange = db.Column(db.Text, nullable=False)
    classWeekDate = db.Column(db.Text, nullable=False)
    '''
    CREATE TABLE TimetableRow (
        rowId INT AUTO_INCREMENT PRIMARY KEY,
        timetable_id INT,
        filename TEXT NOT NULL,
        lecturerName VARCHAR(255) NOT NULL,
        classType VARCHAR(10) NOT NULL,
        classDay VARCHAR(3) NOT NULL,
        classTime VARCHAR(20) NOT NULL,
        classRoom VARCHAR(20) NOT NULL,
        courseName VARCHAR(255) NOT NULL,
        courseIntake VARCHAR(50) NOT NULL,
        courseCode VARCHAR(20) NOT NULL,
        courseSection VARCHAR(20) NOT NULL,
        classWeekRange TEXT NOT NULL,
        classWeekDate TEXT NOT NULL,
        FOREIGN KEY (timetable_id) REFERENCES Timetable(timetableId)
    );
    '''








