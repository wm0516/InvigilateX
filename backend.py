# db_operations.py

from database.py import get_db_connection  # Import the function to get DB connection

def insert_user_to_db(userid, username, department, email, contact, password):
    db = get_db_connection()  # Establish DB connection
    try:
        with db.cursor() as cursor:
            sql = """
                INSERT INTO Users (userid, username, department, email, contact, password)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (userid, username, department, email, contact, password))
            db.commit()  # Commit changes to the DB
        return True, None  # Success
    except pymysql.IntegrityError:
        return False, "Staff ID already exists."  # Handle unique constraint violations (e.g., duplicate staff ID)
    except Exception as e:
        return False, str(e)  # Return error message for any other exceptions
    finally:
        db.close()  # Ensure DB connection is closed after the operation
