from flask import Flask, request, render_template_string, render_template, redirect, url_for
from flask_mail import Mail, Message

app = Flask(__name__,template_folder='app')

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'minglw04@gmail.com'
app.config['MAIL_PASSWORD'] = 'jsco bvwc qpor fvku'
app.config['MAIL_DEFAULT_SENDER'] = 'minglw04@gmail.com'

mail = Mail(app)

# HTML form for sending reset email
html_form = '''
<!DOCTYPE html>
<html>
<head><title>Reset Password Request</title></head>
<body>
    <h2>Request Password Reset</h2>
    <form method="POST" action="/send_reset_email">
        <label for="email">Recipient Email:</label><br>
        <input type="email" name="email" required><br><br>
        <input type="submit" value="Send Reset Link">
    </form>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(html_form)

@app.route('/send_reset_email', methods=['POST'])
def send_reset_email():
    recipient = request.form['email']
    reset_link = url_for('reset_password_page', _external=True)
    msg = Message('Reset Your Password', recipients=[recipient])
    msg.body = f'Click the link to reset your password: {reset_link}'
    try:
        mail.send(msg)
        return f"<h3>Reset email sent to {recipient}!</h3><a href='/'>Back</a>"
    except Exception as e:
        return f"<h3>Failed to send email. Error: {str(e)}</h3><a href='/'>Back</a>"



@app.route('/reset_password_page', methods=['GET', 'POST'])
def reset_password_page():
    if request.method == 'POST':
        new_password = request.form['new_password']
        # You can save the new password here (in DB, file, etc.)
        return "<h3>Password has been reset successfully!</h3><a href='/'>Back</a>"
    return render_template('forgotPassword_page.html')

if __name__ == '__main__':
    app.run(debug=True)
