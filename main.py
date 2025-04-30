from flask import Flask, render_template, request, url_for, redirect
import backend

app = Flask(__name__)

@app.route("/login_page", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        text = request.form.get('textbox')
        return render_template("login_page.html",
                               output=backend.meters_feet(float(text)),
                               user_text=text)
    return render_template("login_page.html")

@app.route("/second", methods=["GET", "POST"])
def second_page():
    if request.method == "POST":
        text = request.form.get('textbox')
        return render_template("second.html",
                               output=backend.meters_feet(float(text)),
                               user_text=text)
    return render_template("second.html")


if __name__ == "__main__":
    app.run()
