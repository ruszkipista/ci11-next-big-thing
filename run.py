import os
from flask import Flask, render_template, request, flash
if os.path.exists("env.py"):
    import env

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_FLASH_KEY")

@app.route("/")  # trigger point through webserver: "/"= root directory
def index():
    return render_template("index.html", page_title="Home")

@app.route("/about")
def about():
    return render_template("about.html", page_title="About")

@app.route("/contact", methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        flash(f"Thanks {request.form.get('name')}, we have received your message!")

    return render_template("contact.html", page_title="Contact")

if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_IP", "0.0.0.0"),  #get value or use given default
        port=int(os.environ.get("PORT", "443")),#get value or use given default
        debug = True if os.environ.get("FLASK_DEBUG", '').lower() == 'true' else False)