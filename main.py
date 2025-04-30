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
        return redirect(url_for('second_page'))

    return render_template('index.html', login_text=login_text, password_text=password_text)

@app.route('/second')
def second_page():
    return "You have logged in!"

if __name__ == '__main__':
    app.run(debug=True)
