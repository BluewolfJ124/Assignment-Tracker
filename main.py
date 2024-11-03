from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import hashlib
import sqlite3
from datetime import datetime

app = Flask(__name__)

gilberts = 0 
app.secret_key = 'sdghsadghi'  # Required for session management
# HI CORBIN
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

def read_from_db(query, params=()):
    conn = sqlite3.connect("login.db")
    cursor = conn.cursor()  
    cursor.execute(query, params)
    items = cursor.fetchall()
    conn.close()
    return items
def write_to_db(query, params=()):
    conn = sqlite3.connect("login.db")
    cursor = conn.cursor()  
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return

@app.route('/')
def index():
    return render_template('index.html',name=get_username())  

@app.route('/assignments')
def assignments():
    if session.get('user') is not None:
        items = read_from_db("SELECT id, name, date_due, completed from assignments WHERE user=?", (session["user"],))
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
        write_to_db("INSERT INTO assignments (name, date_due, user) VALUES (?, ?, ?)", (name, due, get_username()))
        return redirect(url_for("assignments"))
    else:
        return jsonify("Not allowed",403)
@app.route('/finish/<id>', methods=["GET"])
def finish(id):
    if session.get('user') is not None:
        conn = sqlite3.connect("login.db")
        cursor = conn.cursor() 
        try: 
            cursor.execute("UPDATE assignments SET completed=TRUE WHERE id=?", (id,))
            conn.commit()
        except:
            return redirect(url_for("assignments"))
        conn.close()
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
        email = read_from_db("SELECT email from login WHERE name=?", (session["user"],))
        session['email']=email[0][0]
        return render_template('loggedin.html',name=get_username(),email=session["email"])
    if request.method == "POST":
        name = request.form["name"]
        name = name.lower()
        password = request.form["password"]
        passwrd = hashlib.sha256()
        passwrd.update(password.encode('utf-8'))
        valid = read_from_db("SELECT COUNT(*) FROM login WHERE name=? AND password=?", (name, passwrd.hexdigest()))[0]
        if valid[0] >= 1:
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
            same_name = read_from_db("SELECT COUNT(*) FROM login WHERE name=?", (name,))[0]
            same_email=read_from_db("SELECT COUNT(*) FROM login WHERE email=?", (email,))[0]
            if same_name[0] == 0 and same_email[0] == 0:
                password = password.encode('utf-8')
                passwd = hashlib.sha256()
                passwd.update(password) 
                write_to_db("INSERT INTO login (name, password, email) VALUES (?, ?, ?)", (name,passwd.hexdigest(),email))
                session["user"] = name
                return redirect(url_for("index"))
            else:
                return render_template('signup.html', error="Username or Email has been taken",name=get_username())
    return render_template('signup.html', error="",name=get_username())

@app.route("/resetpassword", methods=["GET", "POST"])
def resetpassword():
    if request.method == "POST":
        old = request.form["current"]
        password = request.form["password"]
        confirm_password = request.form["cpassword"]
        old = old.encode('utf-8')
        oldpasswd = hashlib.sha256()
        oldpasswd.update(old) 
        valid = read_from_db("SELECT COUNT(*) FROM login WHERE name=? AND password=?", (get_username(), oldpasswd.hexdigest()))[0]
        if password != confirm_password:
            return render_template('resetpass.html', error="Passwords do not match!")
        elif password=="":
            return render_template('resetpass.html', error="Password cannot be empty")
        elif len(password)>50:
            return render_template('resetpass.html', error="Password cannot be empty")
        elif valid[0] >= 1:
            password = password.encode('utf-8')
            newpasswd = hashlib.sha256()
            newpasswd.update(password) 
            write_to_db('UPDATE login SET password=? WHERE name=? AND password=?;',(newpasswd.hexdigest(),session['user'],oldpasswd.hexdigest()))
            return redirect(url_for("index"))  
        else:
            return render_template('resetpass.html', error="Current password does not exist in the database")
    else:
        return render_template("resetpass.html", name=get_username())

if __name__ == '__main__':
    init_sqlite_db()
    app.run(debug=True, host="0.0.0.0")