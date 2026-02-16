from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Enum, ForeignKey, JSON, Text, func
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
from app import db

# db.String  -> string
# db.Date    -> date format
# db.Time    -> time format
# db.Integer -> number

# SHOW DATABASES;                                                                           -> display out all the database created
# USE WM05$InvigilateX;                                                                     -> use this database
# SHOW TABLES;                                                                              -> display out all the table created
# DROP TABLE (tableName);                                                                   -> to delete that table
# SELECT * FROM (tableName);                                                                -> display out that table data
# UPDATE User SET userEmail='p21013604@student.newinti.edu.my' WHERE userId='21013604';       -> changing the data
# DELETE FROM Exam WHERE examId = '1';                                                      -> remove certain row of data
# NOT NULL = MUST HAVE DATA 
# NULL = OPTIONAL HAVE DATA
# UPDATE User SET userPendingCumulativeHours = 0, userCumulativeHours = 0;
# UPDATE VenueSessionInvigilator SET timeAction = NULL, rejectReason = NULL, invigilationStatus = 0;
# UPDATE Exam SET examOutput = NULL, examStatus = 1;
# DELETE FROM User WHERE userId = 21013604; 

# ------------------------------
# DEPARTMENT
# ------------------------------
class Department(db.Model):
    __tablename__   = 'Department'
    departmentCode  = Column(String(10), primary_key=True)
    departmentName  = Column(String(60), nullable=False)
    deanId          = Column(Integer, ForeignKey('User.userId'), nullable=True)
    hopId           = Column(Integer, ForeignKey('User.userId'), nullable=True)
    hosId           = Column(Integer, ForeignKey('User.userId'), nullable=True)

    # Relationships
    dean  = relationship("User", foreign_keys=[deanId], backref="dean_of_departments")
    hop   = relationship("User", foreign_keys=[hopId], backref="hop_of_departments")
    hos   = relationship("User", foreign_keys=[hosId], backref="hos_of_departments")
    users = relationship("User", back_populates="department", foreign_keys="User.userDepartment")
    '''
    CREATE TABLE Department (
        departmentCode VARCHAR(10) NOT NULL PRIMARY KEY,
        departmentName VARCHAR(60) NOT NULL,
        deanId INT NULL,
        hopId INT NULL,
        hosId INT NULL  
    );
    '''

# ------------------------------
# USER
# ------------------------------
class User(db.Model):
    __tablename__               = 'User'
    userId                      = Column(Integer, primary_key=True)
    userDepartment              = Column(String(10), ForeignKey('Department.departmentCode'), nullable=False)
    userName                    = Column(String(255), nullable=False)
    userLevel                   = Column(String(50), nullable=False)
    userEmail                   = Column(String(255), nullable=False)
    userContact                 = Column(String(15), nullable=True)
    userGender                  = Column(Boolean, nullable=False)
    userPassword                = Column(String(255), nullable=False)
    userStatus                  = Column(Integer, default=0, nullable=False)
    userCumulativeHours         = Column(Float, default=0.0, nullable=False)
    userPendingCumulativeHours  = Column(Float, default=0.0, nullable=False)
    userCardId                  = Column(String(15), nullable=True)
    isLocked                    = Column(Boolean, default=False, nullable=False)
    failedAttempts              = Column(Integer, default=0, nullable=False)

    # Relationships
    department = relationship("Department", back_populates="users", foreign_keys=[userDepartment])
    timetable   = relationship("Timetable", back_populates="user", uselist=False)
    '''
    CREATE TABLE User (
        userId INT NOT NULL PRIMARY KEY,
        userDepartment VARCHAR(10) NOT NULL,
        userName VARCHAR(255) NOT NULL,
        userLevel VARCHAR(50) NOT NULL,
        userEmail VARCHAR(255) NOT NULL,
        userContact VARCHAR(15) NULL,
        userGender BOOLEAN NOT NULL,
        userPassword VARCHAR(255) NOT NULL,
        userStatus INT NOT NULL DEFAULT 0,
        userCumulativeHours FLOAT NOT NULL DEFAULT 0.0,
        userPendingCumulativeHours FLOAT NOT NULL DEFAULT 0.0,
        userCardId VARCHAR(15) NULL,
        isLocked BOOLEAN NOT NULL DEFAULT FALSE,
        failedAttempts INT NOT NULL DEFAULT 0,
        FOREIGN KEY (userDepartment) REFERENCES Department(departmentCode)
    );
    '''

# ------------------------------
# ACTION
# ------------------------------
class Action(db.Model):
    __tablename__       = 'Action'
    actionId            = Column(Integer, primary_key=True, autoincrement=True)
    actionTake          = Column(String(50), nullable=False)
    actionTargetType    = Column(String(50), nullable=False)
    actionTargetId      = Column(String(50), nullable=False)
    actionTime          = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    actionBy            = Column(Integer, ForeignKey('User.userId'), nullable=False)
    actionDevice        = Column(String(100), nullable=False)
    actionIp            = Column(String(20), nullable=False)
    actionBrowser       = Column(String(50), nullable=False)

    # Relationship
    user = relationship("User")
    '''
    CREATE TABLE Action (
        actionId INT AUTO_INCREMENT PRIMARY KEY,
        actionTake VARCHAR(50) NOT NULL,
        actionTargetType VARCHAR(50) NOT NULL,
        actionTargetId VARCHAR(50) NOT NULL,
        actionTime DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actionBy INT NOT NULL,
        actionDevice VARCHAR(100) NOT NULL,
        actionIp VARCHAR(20) NOT NULL,
        actionBrowser VARCHAR(50) NOT NULL,
        CONSTRAINT fk_action_user
            FOREIGN KEY (actionBy)
            REFERENCES User(userId)
    );
    '''

# ------------------------------
# VENUE
# ------------------------------
class Venue(db.Model):
    __tablename__   = 'Venue'
    venueNumber     = Column(String(20), primary_key=True)
    venueLevel      = Column(String(10), nullable=False)
    venueCapacity   = Column(Integer, nullable=False)

    # Relationship
    sessions = relationship("VenueSession", back_populates="venue", cascade="all, delete-orphan")
    '''
    CREATE TABLE Venue (
        venueNumber VARCHAR(20) NOT NULL PRIMARY KEY,
        venueLevel VARCHAR(10) NOT NULL,
        venueCapacity INT NOT NULL
    );
    '''

# ------------------------------
# VENUE SESSION
# ------------------------------
class VenueSession(db.Model):
    __tablename__ = 'VenueSession'
    venueSessionId      = Column(Integer, primary_key=True, autoincrement=True)
    venueNumber         = Column(String(20), ForeignKey('Venue.venueNumber'), nullable=False)
    startDateTime       = Column(DateTime, nullable=False)
    endDateTime         = Column(DateTime, nullable=False)
    noInvigilator       = Column(Integer, nullable=True)
    backupInvigilatorId = Column(Integer, ForeignKey('User.userId'), nullable=True)

    # Relationships
    venue = relationship("Venue", back_populates="sessions")
    exams = relationship("VenueExam", back_populates="session")
    invigilators = relationship("VenueSessionInvigilator", back_populates="session", cascade="all, delete-orphan")
    backupInvigilator = relationship("User", foreign_keys=[backupInvigilatorId])
    '''
    CREATE TABLE VenueSession (
        venueSessionId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        venueNumber VARCHAR(20) NOT NULL,
        startDateTime DATETIME NOT NULL,
        endDateTime DATETIME NOT NULL,
        noInvigilator INT NULL,
        backupInvigilatorId INT NULL,
        UNIQUE (venueNumber, startDateTime, endDateTime),
        FOREIGN KEY (venueNumber) REFERENCES Venue(venueNumber),
        FOREIGN KEY (backupInvigilatorId) REFERENCES User(userId)
    );
    '''


class VenueSessionInvigilator(db.Model):
    __tablename__       = 'VenueSessionInvigilator'
    sessionId           = Column(Integer, primary_key=True, autoincrement=True) 
    venueSessionId      = Column(Integer, ForeignKey('VenueSession.venueSessionId'), nullable=False)
    invigilatorId       = Column(Integer, ForeignKey('User.userId'), nullable=True)
    position            = Column(String(20), nullable=True)
    checkIn             = Column(DateTime, nullable=True)
    checkOut            = Column(DateTime, nullable=True)
    timeAction          = Column(DateTime, nullable=True)
    timeCreate          = Column(DateTime, nullable=False)
    timeExpire          = Column(DateTime, nullable=False)
    invigilationStatus  = Column(Boolean, default=False)
    remark              = Column(Enum("PENDING","CHECK IN LATE","CHECK IN","CHECK OUT EARLY","COMPLETED","EXPIRED", "REJECTED", name="attendance_remark_enum"), nullable=False, default="PENDING")
    rejectReason        = Column(String(255), nullable=True)
    
    # Relationships
    session     = relationship("VenueSession", back_populates="invigilators")
    invigilator = relationship("User")
    '''
    CREATE TABLE VenueSessionInvigilator (
        sessionId INT NOT NULL AUTO_INCREMENT,
        venueSessionId INT NOT NULL,
        invigilatorId INT NULL,
        position VARCHAR(20) NULL,
        checkIn DATETIME NULL,
        checkOut DATETIME NULL,
        timeAction DATETIME NULL,
        timeCreate DATETIME NOT NULL,
        timeExpire DATETIME NOT NULL,
        invigilationStatus BOOLEAN NOT NULL DEFAULT FALSE,
        remark ENUM('PENDING', 'CHECK IN LATE', 'CHECK IN', 'CHECK OUT EARLY', 'COMPLETED', 'EXPIRED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
        rejectReason VARCHAR(255) NULL,
        PRIMARY KEY (sessionId),
        UNIQUE KEY unique_session_invigilator (venueSessionId, invigilatorId),
        FOREIGN KEY (venueSessionId) REFERENCES VenueSession(venueSessionId) ON DELETE CASCADE,
        FOREIGN KEY (invigilatorId) REFERENCES User(userId) ON DELETE SET NULL
    );
    '''

# ------------------------------
# EXAM
# ------------------------------
class Exam(db.Model):
    __tablename__       = 'Exam'
    examId              = Column(Integer, primary_key=True, autoincrement=True)
    examStatus          = Column(Boolean, default=True, nullable=False)
    examOutput          = Column(JSON, nullable=True)

    # Relationships
    course                  = relationship("Course", back_populates="exam", uselist=False)
    venue_availabilities    = relationship("VenueExam", back_populates="exam")
    '''
    CREATE TABLE Exam (
        examId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        examStatus BOOLEAN NOT NULL DEFAULT TRUE,
        examOutput JSON NULL
    );
    '''
    
class VenueExam(db.Model):
    __tablename__   = 'VenueExam'
    examVenueId     = Column(Integer, primary_key=True, autoincrement=True)
    examId          = Column(Integer, ForeignKey('Exam.examId'), nullable=False)
    venueSessionId  = Column(Integer, ForeignKey('VenueSession.venueSessionId'), nullable=False)
    studentCount    = Column(Integer, nullable=False)

    # Relationships
    exam    = relationship("Exam", back_populates="venue_availabilities")
    session = relationship("VenueSession", back_populates="exams")
    '''
    CREATE TABLE VenueExam (
        examVenueId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        examId INT NOT NULL,
        venueSessionId INT NOT NULL,
        studentCount  INT NOT NULL,
        FOREIGN KEY (examId) REFERENCES Exam(examId),
        FOREIGN KEY (venueSessionId) REFERENCES VenueSession(venueSessionId)
    );
    '''

# ------------------------------
# COURSE
# ------------------------------
class Course(db.Model):
    __tablename__           = 'Course'
    courseCodeSectionIntake = Column(String(50), primary_key=True)
    courseDepartment        = Column(String(10), ForeignKey('Department.departmentCode'), nullable=False)
    coursePractical         = Column(Integer, ForeignKey('User.userId'), nullable=True)
    courseTutorial          = Column(Integer, ForeignKey('User.userId'), nullable=True)
    courseLecturer          = Column(Integer, ForeignKey('User.userId'), nullable=True)
    courseExamId            = Column(Integer, ForeignKey('Exam.examId'), nullable=False)
    courseName              = Column(String(50), nullable=False)
    courseHour              = Column(Integer, nullable=False)
    courseStudent           = Column(Integer, nullable=False)
    courseStatus            = Column(Boolean, default=True, nullable=False)

    # Relationships
    department          = relationship("Department", backref="courses")
    practicalLecturer   = relationship("User", foreign_keys=[coursePractical])
    tutorialLecturer    = relationship("User", foreign_keys=[courseTutorial])
    classLecturer       = relationship("User", foreign_keys=[courseLecturer])
    exam                = relationship("Exam", back_populates="course", uselist=False)
    '''
    CREATE TABLE Course (
        courseCodeSectionIntake VARCHAR(50) NOT NULL PRIMARY KEY,
        courseDepartment VARCHAR(10) NOT NULL,
        coursePractical INT NULL,
        courseTutorial INT NULL,
        courseLecturer INT NULL,
        courseExamId INT NOT NULL,
        courseName VARCHAR(50) NOT NULL,
        courseHour INT NOT NULL,
        courseStudent INT NOT NULL,
        courseStatus BOOLEAN NOT NULL DEFAULT TRUE,
        FOREIGN KEY (courseDepartment) REFERENCES Department(departmentCode),
        FOREIGN KEY (coursePractical) REFERENCES User(userId),
        FOREIGN KEY (courseTutorial) REFERENCES User(userId),
        FOREIGN KEY (courseLecturer) REFERENCES User(userId),
        FOREIGN KEY (courseExamId) REFERENCES Exam(examId)
    );
    '''
    
# ------------------------------
# TIMETABLE
# ------------------------------
class Timetable(db.Model):
    __tablename__   = 'Timetable'
    timetableId     = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(Integer, ForeignKey('User.userId'), unique=True)
    user            = relationship('User', back_populates='timetable')
    rows            = relationship('TimetableRow', back_populates='timetable')
    '''
    CREATE TABLE Timetable (
        timetableId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT UNIQUE,
        FOREIGN KEY (user_id) REFERENCES User(userId)
    );
    '''

class TimetableRow(db.Model):
    __tablename__   = 'TimetableRow'
    rowId           = Column(Integer, primary_key=True, autoincrement=True)
    timetable_id    = Column(Integer, ForeignKey('Timetable.timetableId'))
    timetable       = relationship('Timetable', back_populates='rows')
    filename        = Column(Text, nullable=False)
    lecturerName    = Column(String(255), nullable=False)
    classType       = Column(String(10), nullable=False)
    classDay        = Column(String(3), nullable=False)
    classTime       = Column(String(20), nullable=False)
    classRoom       = Column(String(20), nullable=False)
    courseName      = Column(String(255), nullable=False)
    courseIntake    = Column(String(50), nullable=False)
    courseCode      = Column(String(20), nullable=False)
    courseSection   = Column(String(20), nullable=False)
    classWeekRange  = Column(Text, nullable=False)
    classWeekDate   = Column(Text, nullable=False)
    '''
    CREATE TABLE TimetableRow (
        rowId INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
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
