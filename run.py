import os
from flask import Flask, render_template, g, request, flash
if os.path.exists("env.py"):
    import env

app = Flask(__name__)

# SQLite patterns from https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
import sqlite3

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        DATABASE = os.environ.get("SQLITE_DB", './data/taskmaster.sqlite')
        db = g._database = sqlite3.connect(DATABASE)
        # use built-in row translator
        db.row_factory = sqlite3.Row
    return db

def init_db():
    """
    # To create the empty database, run this at python prompt:
    # > from run import init_db
    # > init_db()
    """
    with app.app_context():
        db = get_db()
        SCHEMA = os.environ.get("SQLITE_SCHEMA", './data/schema.sql')
        print(SCHEMA)
        with app.open_resource(SCHEMA, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

#================================
# App routing
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

# Run the App
if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_IP", "0.0.0.0"),  #get value or use given default
        port=int(os.environ.get("PORT", "443")),#get value or use given default
        debug = True if os.environ.get("FLASK_DEBUG", '').lower() == 'true' else False)