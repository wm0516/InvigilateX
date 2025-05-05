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
def register_page():
    if request.method == 'POST':
        # Retrieve form data
        userid_text = request.form['userid']
        username_text = request.form['username']
        department_text = request.form['department']
        email_text = request.form['email']
        contact_text = request.form['contact']
        password1_text = request.form['password1']
        password2_text = request.form['password2']

        # Print form data for debugging
        print(f"Form data: {userid_text}, {username_text}, {department_text}, {email_text}, {contact_text}")

        # Validate passwords match
        if password1_text != password2_text:
            return "Passwords do not match."
        
        if not (userid_text and username_text and department_text and email_text and contact_text):
            return "Field can't be empty."


        # If everything is fine, redirect to login
        return redirect(url_for('login'))

    return render_template('register_page.html')

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
