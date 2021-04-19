import os
from flask import Flask, render_template, g, request, redirect, flash
if os.path.exists("env.py"):
    import env

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_FLASH_KEY")

# SQLite3 helpers
#=====================
import sqlite3
# SQLite pattern from https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        DATABASE = os.environ.get("SQLITE_DB", './data/taskmaster.sqlite')
        db = g._database = sqlite3.connect(DATABASE)
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
        SCHEMA = os.environ.get("SQLITE_SCHEMA", './data/schema.sql')
        with app.open_resource(SCHEMA, mode='r') as f:
            db.cursor().executescript(f.read())
        CONTENT = os.environ.get("SQLITE_CONTENT", './data/content.sql')
        with app.open_resource(CONTENT, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# inspired by SQLite pattern from https://flask.palletsprojects.com/en/1.1.x/patterns/sqlite3/        
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

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

def insert_row(table:str, row:sqlite3.Row) -> bool:
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
        return cur.rowcount
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
#================================
# App routing
#================================
@app.route("/")  # trigger point through webserver: "/"= root directory
def index():
    return render_template("index.html", page_title="Home")

@app.route("/about")
def about():
    return render_template("about.html", page_title="About")

@app.route("/todo", methods=['GET','POST'])
def todo():
    task={}
    if request.method == 'POST':
        columns = ('Content','Completed')
        values  = [request.form.get(column) for column in columns]
        values[1] = 1 if values[1]=="on" else 0
        # checkbox value conversion to integer
        task = create_row(columns, values)
        result = insert_row('Todos', task)
        if type(result) == int:
            flash("Record successfully added")
            task = create_row(columns, ("",0))
        else:
            flash("Error in insert operation:", result)

    tasks = query_db("SELECT * FROM TodosView ORDER BY Completed;")
    return render_template("todo.html", page_title="Task Master", page_url=request.path, tasks=tasks, last_task=task)

@app.route("/todo/delete/<int:task_id>")
def delete(task_id):
    result = delete_row('Todos', task_id)
    if type(result) == int:
        flash(f"{result} Record successfully deleted")
    else:
        flash("Error in delete operation: ", result)

    return redirect('/todo')

@app.route("/contact", methods=['GET','POST'])
def contact():
    if request.method == 'POST':
        flash(f"Thanks {request.form.get('name')}, we have received your message!")
    return render_template("contact.html", page_title="Contact")

# Run the App
if __name__ == "__main__":
    if os.environ.get("SQLITE_INIT", "False").lower() == 'true':
        init_db()
    app.run(
        host=os.environ.get("FLASK_IP", "0.0.0.0"),  #get value or use given default
        port=int(os.environ.get("PORT", "443")),#get value or use given default
        debug = True if os.environ.get("FLASK_DEBUG", '').lower() == 'true' else False)