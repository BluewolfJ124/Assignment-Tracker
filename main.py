from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'sdghsadghi'  # Required for session management
def days_between_dates(dt):
    date1 = datetime.now().date()
    date2 = datetime.strptime(dt, '%Y-%m-%d').date()
    delta = date2 - date1
    return delta.days
 
def get_username():
    if session.get('user') is not None:
        return session['user']
    else:
        return "Login"
    
def init_sqlite_db():
    conn = sqlite3.connect('login.db')  # Connect to SQLite database named 'database.db'
    # Execute SQL command to create 'users' table with id, username, and password columns
    conn.execute('CREATE TABLE IF NOT EXISTS login (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(255), password VARCHAR(255), email STR)')
    conn.execute('CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, date_due TEXT, user TEXT, completed BOOLEAN DEFAULT FALSE)')
    conn.close()  # Close the database connection

def rw_from_db(write,query, params=()): # Read and write to sql database function
    conn = sqlite3.connect("login.db")
    cursor = conn.cursor()  
    cursor.execute(query, params)
    conn.commit()
    if write==False:
        items = cursor.fetchall()
        conn.close()
        return items
    else:
        conn.close()
        return

@app.route('/')
def index():
    return render_template('index.html',name=get_username())  

@app.route('/assignments')
def assignments():
    if session.get('user') is not None:
        items = rw_from_db(False, "SELECT id, name, date_due, completed from assignments WHERE user=?", (session["user"],))
        uncompleted = []
        completed = []
        for i in items:
            if i[3] == False:
                uncompleted.append((i[1],days_between_dates(i[2]),i[0]))
            else:
                if days_between_dates(i[2]) < -14:
                    delete(i[0])
                else:
                    completed.append((i[0],i[1]))
        return render_template('assignments.html',name=get_username(), items=uncompleted, completed=completed)  
    else:
        return redirect(url_for("login"))
    
@app.route('/newassignment', methods=["POST"])
def newassignment():
    if session.get('user') is not None:
        name = request.form["name"]
        due = request.form["due"]
        rw_from_db(True,"INSERT INTO assignments (name, date_due, user) VALUES (?, ?, ?)", (name, due, get_username()))
        return redirect(url_for("assignments"))
    else:
        return jsonify("Not allowed",403)
    
@app.route('/finish/<id>', methods=["GET"])
def finish(id):
    if session.get('user') is not None:
        try: 
            rw_from_db(True,"UPDATE assignments SET completed=TRUE WHERE id=?", (id,))
        except:
            return redirect(url_for("assignments"))
        return redirect(url_for("assignments"))
    else:
        return jsonify("Not allowed",403)
    
@app.route('/delete/<id>', methods=["GET"])
def delete(id):
    # Theres a pretty major vunerablility here where anyone can delete an assignment if they just input and id, and are logged into any account
    # TODO: Check if the user is the owner of the assignment before deleting it
    if session.get('user') is not None:
        conn = sqlite3.connect("login.db")
        cursor = conn.cursor() 
        try: 
            cursor.execute("DELETE FROM assignments WHERE id=?", (id,))
            conn.commit()
        except:
            return redirect(url_for("assignments"))
        conn.close()
        return redirect(url_for("assignments"))
    else:
        return jsonify("Not allowed",403)

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get('user') is not None:
        email = rw_from_db(False,"SELECT email from login WHERE name=?", (session["user"],))
        session['email']=email[0][0]
        return render_template('loggedin.html',name=get_username(),email=session["email"])
    if request.method == "POST":
        name = request.form["name"]
        name = name.lower()
        password = request.form["password"]
        valid = rw_from_db(False, "SELECT password FROM login WHERE name=?", (name,))[0][0]
        if check_password_hash(valid,password):
            session['user'] = name
            return redirect(url_for("index"))
        else:
            return render_template('login.html',error='Username or password do not match any accounts in the database. Please note usernames are not case sensitive, but passwords are.',name=get_username())
    return render_template('login.html',error='',name=get_username())
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/create", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        name = request.form["name"]
        name = name.lower()
        email = request.form["email"]
        email = email.lower()
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]
        if " " in name or " " in password or name=="login" or " " in email:
            return render_template('signup.html', error="Username or Email is invalid")
        elif len(name) > 20:
            return render_template('signup.html', error="Username has to be less than 20 characters")
        elif len(password) > 50:
            return render_template('signup.html', error="Password has to be less than 50 characters")
        elif not confirm_password == password:
            return render_template('signup.html', error="Passwords do not match!")
        else:
            same_name = rw_from_db(False, "SELECT COUNT(*) FROM login WHERE name=?", (name,))[0]
            same_email=rw_from_db(False,"SELECT COUNT(*) FROM login WHERE email=?", (email,))[0]
            if same_name[0] == 0 and same_email[0] == 0:
                rw_from_db(True,"INSERT INTO login (name, password, email) VALUES (?, ?, ?)", (name,generate_password_hash(password),email))
                session["user"] = name
                return redirect(url_for("index"))
            else:
                return render_template('signup.html', error="Username or Email has been taken",name=get_username())
    return render_template('signup.html', error="",name=get_username())

if __name__ == '__main__':
    init_sqlite_db()
    app.run()