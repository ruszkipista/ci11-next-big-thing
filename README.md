# Task Master
A Flask and SQLite based CRUD demo application. Inspired by [this](https://www.youtube.com/watch?v=Z1RJmh_OqeA) video.
The aim here is to build a simple Flask-SQLite-CRUD template.

You can create the empty database from the Python shell:
```python
from run import init_db()
init_db()
```

### How To Run
1. Install `virtualenv`:
```
$ pip install virtualenv
```

2. Open a terminal in the project root directory and run:
```
$ virtualenv env
```

3. Then run the command:
```
$ .\env\Scripts\activate
```

4. Then install the dependencies:
```
$ (env) pip install -r requirements.txt
```

5. Finally start the web server:
```
$ (env) python app.py
```

The project is deployed on [Heroku](https://task-master-ruszkipista.herokuapp.com/)