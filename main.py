from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

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
    if request.method == 'POST':
        # Retrieve form data
        userid = request.form['userid']
        username = request.form['username']
        department = request.form['department']
        email = request.form['email']
        contact = request.form['contact']
        password1 = request.form['password1']
        password2 = request.form['password2']

        # Validate passwords match
        if password1 != password2:
            return "Passwords do not match."

        return redirect(url_for('login'))

    return render_template('register.html')

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
