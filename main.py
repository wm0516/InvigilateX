from flask import Flask, render_template, request, redirect, url_for
import pymysql

app = Flask(__name__)

# Database connection
db = pymysql.connect(
    host="wmm.mysql.pythonanywhere-services.com",
    user="wmm",
    password="Law204500",
    database="wmm$InvigilateX"
)

@app.route('/', methods=['GET', 'POST'])
def login():
    login_text = ""
    password_text = ""
    
    if request.method == 'POST':
        login_text = request.form.get('textbox', '')
        password_text = request.form.get('password', '')
        # You could validate here, then redirect or process login
        return redirect(url_for('home_page'))

    return render_template('login_page.html', login_text=login_text, password_text=password_text)



@app.route('/register', methods=['GET', 'POST'])
def register():
    username = ""
    userid = ""
    department = ""
    email = ""
    contact = ""
    password1 = ""
    password2 = ""

    if request.method == 'POST':
        # Get data from form
        username = request.form['username']
        userid = request.form['userid']
        department = request.form['department']
        email = request.form['email']
        contact = request.form['contact']
        password1 = request.form['password1']
        password2 = request.form['password2']

        # Check passwords match
        if password1 != password2:
            return "Passwords do not match"

        # Insert into database
        cursor = db.cursor()
        sql = """
            INSERT INTO users (username, userid, department, email, contact, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (username, userid, department, email, contact, password1))
        db.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('register.html',
                        username_text=username,
                        userid_text=userid,
                        department_text=department,
                        email_text=email,
                        contact_text=contact,
                        password1_text=password1,
                        password2_text=password2)


@app.route('/home')
def home_page():
    return render_template('home_page.html')

@app.route('/forgotPassword')
def forgot_password_page():
    return render_template('forgotPassword_page.html')

@app.route('/resetPassword')
def reset_password_page():
    return render_template('resetPassword_page.html')

if __name__ == '__main__':
    app.run(debug=True)
