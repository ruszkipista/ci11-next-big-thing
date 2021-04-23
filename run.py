import os
from flask import Flask, render_template, g, request, redirect, flash, send_from_directory
from werkzeug.utils import secure_filename
import time

#!pip install dnspython pymongo
import pymongo

# env.py should exist only in Development
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

# take app configuration from OS environment variables
app.secret_key               = os.environ.get("FLASK_SECRET_KEY")            # => Heroku Congig Vars
app.config["FLASK_IP"]       = os.environ.get("FLASK_IP",      "0.0.0.0")
# the source 'PORT' name is mandated by Heroku app deployment
app.config["FLASK_PORT"]     = int(os.environ.get("PORT"))
app.config["FLASK_DEBUG"]    = os.environ.get("FLASK_DEBUG",   "False").lower() in {'1','true','t','yes','y'}
app.config["UPLOAD_FOLDER"]  = os.environ.get("UPLOAD_FOLDER", "./data/")
app.config["UPLOAD_EXTENSIONS"] = set(['png', 'jpg', 'jpeg', 'gif'])
# SQLite parameters
app.config["SQLITE_INIT"]    = os.environ.get("SQLITE_INIT",   "False").lower() in {'1','true','t','yes','y'}# => Heroku Congig Vars
app.config["SQLITE_DB"]      = os.environ.get("SQLITE_DB",     "./data/taskmaster.sqlite") 
app.config["SQLITE_SCHEMA"]  = os.environ.get("SQLITE_SCHEMA", "./data/schema.sql")
app.config["SQLITE_CONTENT"] = os.environ.get("SQLITE_CONTENT","./data/content.sql")
app.config["TABLE_TODOS"]    = "Todos"
app.config["TABLE_TODOV"]    = "TodosView"
app.config["COLUMNS_TODOS"]  = ('TaskId','Content','Completed','SourceFileName','LocalFileName','DatTimIns', 'DatTimUpd')
app.config["DEFAULTS_TODOS"] = (0,'','','','','','')
# MongoDB parameters
app.config["MONGO_DB_NAME"]    = os.environ.get("MONGO_DB_NAME")
app.config["MONGO_CLUSTER"]    = os.environ.get("MONGO_CLUSTER")
app.config["MONGO_COLLECTION"] = os.environ.get("MONGO_COLLECTION")
app.config["MONGO_URI"] = f"mongodb+srv:" + \
                          f"//{os.environ.get('MONGO_DB_USER')}" + \
                          f":{os.environ.get('MONGO_DB_PASS')}" + \
                          f"@{app.config['MONGO_CLUSTER']}" + \
                          f".ueffo.mongodb.net" + \
                          f"/{app.config['MONGO_DB_NAME']}" + \
                          f"?retryWrites=true&w=majority"

# SQLite3 DB helpers
#=====================
import sqlite3
# SQLite pattern from https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config["SQLITE_DB"])
        # use built-in row translator
        db.row_factory = sqlite3.Row
    return db


# SQLite pattern from https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# inspired by SQLite pattern from https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
def init_db(load_content=False):
    with app.app_context():
        db = get_db()
        with app.open_resource(app.config["SQLITE_SCHEMA"], mode='r') as f:
            db.cursor().executescript(f.read())
        with app.open_resource(app.config["SQLITE_CONTENT"], mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


# inspired by SQLite pattern from https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/        
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return (rv[0] if type(rv)==list else rv) if one else rv


# inspired by Example 1 from https://www.programcreek.com/python/example/3926/sqlite3.Row
def create_row(columns, values):
    """ convert column names and corresponding values into sqlite3.Row type object """
    cur = get_db().cursor()
    if not cur:
        return None
    # generate "? AS <column>, ..."
    col_list = ", ".join([f"? AS '{col}'" for col in columns])
    query=f"SELECT {col_list};"
    return cur.execute(query, values).fetchone()


def insert_row(table:str, row:sqlite3.Row):
    """ insert one row into given table """
    cur = get_db().cursor()
    if not cur:
        return 0
    try:
        columns = row.keys()
        values  = tuple(row[key] for key in columns)
        # generate list of column names
        col_list = ",".join(columns)
        # generate list of question marks
        qmark_list = ','.join('?'*len(columns))
        query=f"INSERT INTO {table} ({col_list}) VALUES ({qmark_list});"
        cur.execute(query, values)
        cur.connection.commit()
        return cur.lastrowid
    except sqlite3.Error as error:
        cur.connection.rollback()
        return error
 

def delete_row(table:str, id:int):
    """ delete one row by <rowid> from given table """
    cur = get_db().cursor()
    if not cur:
        return ""
    try:
        query=f"DELETE FROM {table} WHERE rowid=?;"
        cur.execute(query, (id,))
        cur.connection.commit()
        return cur.rowcount
    except sqlite3.Error as error:
        cur.connection.rollback()
        return error


def update_row(table:str, row:sqlite3.Row, id:int):
    """ update one row by <rowid> from given table """
    cur = get_db().cursor()
    if not cur:
        return ""
    try:
        columns = row.keys()
        values  = tuple([row[column] for column in columns]+[id])
        # generate "<column>=?,..." list
        set_list = ",".join([column+"=? " for column in columns])
        cur.execute(f"UPDATE {table} SET {set_list} WHERE rowid=?;", values)
        cur.connection.commit()
        return cur.rowcount
    except sqlite3.Error as error:
        cur.connection.rollback()
        return error

# MongoDB helpers
#=================
def mongo_connect(url, db_name):
    try:
        conn = pymongo.MongoClient(url)
        print(f"{db_name} is connected")
        return conn
    except pymongo.errors.ConnectionFailure as e:
        print(f"Could not connect to MongoDB {db_name}: {e}")


# App routing
#==============
@app.route("/")  # trigger point through webserver: "/"= root directory
def index():
    return render_template("index.html", page_title="Home")


@app.route("/about")
def about():
    return render_template("about.html", page_title="About")


@app.route("/todos", methods=['GET','POST'])
def todos():
    if request.method == 'POST':
        task = save_task_to_db(request, None)
    else:
        # create an empty task
        task = create_row(app.config["COLUMNS_TODOS"],app.config["DEFAULTS_TODOS"])
    task = convertFromDBtoPrint(task, app.config["COLUMNS_TODOS"], app.config["DEFAULTS_TODOS"])
    # get all tasks from DB
    tasks = query_db(f"SELECT * FROM {app.config['TABLE_TODOV']} ORDER BY Completed;")
    tasks = [convertFromDBtoPrint(t, app.config["COLUMNS_TODOS"], app.config["DEFAULTS_TODOS"]) for t in tasks]
    if not tasks:
        flash("There are no tasks. Create one above!")
    return render_template("todos.html", page_title="Task Master", request_path=request.path, tasks=tasks, last_task=task)


@app.route("/todos/update/<int:task_id>", methods=['GET','POST'])
def update_task(task_id):
    task = query_db(f"SELECT * FROM {app.config['TABLE_TODOS']} WHERE rowid=?;", (task_id,), one=True)
    if task is None:
        flash(f"Task {task_id} does not exist")
        return redirect("/todos")

    if request.method == 'POST':
        task = save_task_to_db(request, task)
        return redirect("/todos")

    task = convertFromDBtoPrint(task, app.config["COLUMNS_TODOS"], app.config["DEFAULTS_TODOS"])
    tasks = query_db(f"SELECT * FROM {app.config['TABLE_TODOV']} ORDER BY Completed;")
    tasks = [convertFromDBtoPrint(t,app.config["COLUMNS_TODOS"], app.config["DEFAULTS_TODOS"]) for t in tasks]
    return render_template("todos.html", page_title="Task Master", tasks=tasks, last_task=task)


def save_task_to_db(request, task_old):
    columns = ['Content','Completed']
    values  = [request.form.get(column,'') for column in columns]
    # checkbox value conversion to integer
    values[1] = 1 if values[1]=="on" else 0

    # following instructions from https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
    filename_source = ''
    filename_local  = ''
    data = request.files['SourceFileName']
    if data:
        filename_source = secure_filename(data.filename)
        extension = filename_source.rsplit('.', 1)[1] if '.' in filename_source else ''
        if extension in app.config["UPLOAD_EXTENSIONS"]:
            # generate a new image file name
            filename_local = str(time.time()).replace('.','')+'.'+extension
            columns += ['SourceFileName','LocalFileName']
            values  += [filename_source, filename_local]

    task_new = create_row(columns, values)
    if task_old:
        row_id = update_row(app.config["TABLE_TODOS"], task_new, task_old['TaskId'])
    else:
        row_id = insert_row(app.config["TABLE_TODOS"], task_new)
    # update was successful
    if type(row_id) == int:
        # save new file
        if data:
            data.save(os.path.join(app.config["UPLOAD_FOLDER"], filename_local))
            # delete old file
            if task_old and task_old['LocalFileName']:
                try:
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], task_old['LocalFileName']))
                except FileNotFoundError as error:
                    flash(f"Could not delete {task_old['SourceFileName']}: {error}")

        # create empty task - this will be displayed, because the update was OK
        task_new = create_row(app.config["COLUMNS_TODOS"],app.config["DEFAULTS_TODOS"])
        flash(f"One record successfully {'updated' if task_old else 'added'}")
    else:
        flash(f"Error in {'update' if task_old else 'insert'} operation: {row_id}")
    return task_new


@app.route("/todos/delete/<int:task_id>")
def delete_task(task_id):
    task = query_db(f"SELECT SourceFileName, LocalFileName FROM {app.config['TABLE_TODOS']} WHERE TaskId=?;", (task_id,), one=True)
    if task is None:
        flash(f"Task {task_id} does not exist")
    else:
        result = delete_row(app.config['TABLE_TODOS'], task_id)
        if type(result) == int:
            filename_local = task['LocalFileName']
            if filename_local:
                try:
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], filename_local))
                except FileNotFoundError as error:
                    flash(f"Could not delete {task['SourceFileName']}: {error}")
            flash(f"{result} Record deleted")
        else:
            flash(f"Error in delete operation: {result}")
    return redirect('/todos')


def convertFromDBtoPrint(row:sqlite3.Row, columns, defaults):
    return {c:(d if row[c] is None else row[c]) for (c,d) in zip(columns,defaults)}

@app.route("/uploads/<filename_local>")
def uploads(filename_local):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename_local)


@app.route("/contact", methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        flash(f"Thanks {request.form.get('name')}, we have received your message!")
    return render_template("contact.html", page_title="Contact")

# MongoDB routes
#=================
@app.route("/celebs")
def celebs():
        return render_template("celebs.html", page_title="Celebrities", celebs=[], last_celeb={})

# Run the App
#=================
if __name__ == "__main__":
    if app.config["SQLITE_INIT"]:
        init_db()

    conn = mongo_connect(app.config["MONGO_URI"], app.config["MONGO_DB_NAME"])
    coll = conn[app.config["MONGO_DB_NAME"]][app.config["MONGO_COLLECTION"]]

    app.run(
        host  = app.config["FLASK_IP"],
        port  = app.config["FLASK_PORT"],
        debug = app.config["FLASK_DEBUG"])