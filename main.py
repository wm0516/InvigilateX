from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def login_page():
    login_text = ''
    password_text = ''
    error_message = None

    if request.method == 'POST':
        login_text = request.form.get('textbox', '')
        password_text = request.form.get('password', '')

        if not all([login_text, password_text]):
            error_message = "Both fields are required."
        else:
            # Your login validation logic here
            # If login fails, set error_message again
            return redirect(url_for('home_page'))

    return render_template('login_page.html', error_message=error_message)



@app.route('/register', methods=['GET', 'POST'])
def register_page():
    error_message = None

    if request.method == 'POST':
        userid_text = request.form.get('userid', '')
        username_text = request.form.get('username', '')
        department_text = request.form.get('department', '')
        email_text = request.form.get('email', '')
        contact_text = request.form.get('contact', '')
        password1_text = request.form.get('password1', '')
        password2_text = request.form.get('password2', '')

        # Validation
        if not all([userid_text, username_text, department_text, email_text, contact_text]):
            error_message = "All fields are required."
        elif password1_text != password2_text:
            error_message = "Passwords do not match."
        else:
            return redirect(url_for('login_page'))

    return render_template('register_page.html', error_message=error_message)





@app.route('/home')
def home_page():
    return render_template('home_page.html')



@app.route('/forgotPassword', methods=['GET', 'POST'])  # Allow both GET and POST
def forgot_password_page():
    error_message = None
    if request.method == 'POST':
        forgot_email_text = request.form.get('email', '')  # Get email from form
        
        if not forgot_email_text:
            error_message = "Field can't be empty."
        else:
            return redirect(url_for('reset_password_page'))  # Redirect to reset page after form submission

    return render_template('forgotPassword_page.html', error_message=error_message)



@app.route('/resetPassword', methods=['GET', 'POST'])
def reset_password_page():
    error_message = None
    if request.method == 'POST':
        password_text_1 = request.form.get('password1', '')
        password_text_2 = request.form.get('password2', '')

        if password_text_1 != password_text_2:
            error_message = "Passwords do not match."
        if not all([password_text_1, password_text_2]):
            error_message = "All fields are required."
        else:
            return redirect(url_for('login_page'))

    return render_template('resetPassword_page.html', error_message=error_message)




if __name__ == '__main__':
    app.run(debug=True)
