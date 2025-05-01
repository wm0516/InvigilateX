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


@app.route('/home')
def home_page():
    return render_template('home_page.html')


@app.route('/forgotPassword')
def forgot_password_page():
    return render_template('forgotPassword_page.html')

@app.route('/forgotPassword_OTP')
def forgot_password_OTP_page():
    return render_template('forgotPasswordOTP_page.html')

@app.route('/resetPassword')
def reset_password_page():
    return render_template('resetPassword.html')


@app.route('/register')
def register_page():
    return render_template('register_page.html')

if __name__ == '__main__':
    app.run(debug=True)
