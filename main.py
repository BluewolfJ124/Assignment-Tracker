from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import hashlib, time
import sqlite3
from datetime import datetime
from datetime import date
month_map = {
    '01': 'January',
    '02': 'February',
    '03': 'March',
    '04': 'April',
    '05': 'May',
    '06': 'June',
    '07': 'July',
    '08': 'August',
    '09': 'September',
    '10': 'October',
    '11': 'November',
    '12': 'December'
}

app = Flask(__name__)
gilberts = 0 
app.secret_key = 'sdghsadghi'  # Required for session management
# HI CORBIN
def convert_date(date_str):
    # Split the date string into components
    year, month, day = date_str.split('-')
    day = int(day)
    # Map the month number to the month name
    if 10 <= day % 100 <= 20:  # Handle 11th, 12th, 13th
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    month_name = month_map[month]
    return f"{month_name} {day}{suffix}"  # Convert day to int to remove leading zero
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
    
@app.route('/')
def index():
    return render_template('index.html',name=get_username())  
@app.route('/about')
def about():
    return render_template('about.html', name=get_username())  
@app.route('/assignments')
def assignments():
    if session.get('user') is not None:
        #assignments = get_assignments()
        conn = sqlite3.connect("login.db")
        cursor = conn.cursor()  
        cursor.execute("SELECT id, name, date_due from assignments WHERE user=?", (session["user"],))
        items = cursor.fetchall()
        real_items = []
        for i in items:
            real_items.append((i[1],days_between_dates(i[2]),i[0]))
        print(real_items)
        conn.close()
        return render_template('assignments.html',name=get_username(), items=real_items)  
    else:
        return redirect(url_for("login"))
@app.route('/newassignment', methods=["POST"])
def newassignment():
    if session.get('user') is not None:
        name = request.form["name"]
        due = request.form["due"]
        print(name)
        print(due)
        conn = sqlite3.connect("login.db")
        cursor = conn.cursor()  
        cursor.execute("INSERT INTO assignments (name, date_due, user) VALUES (?, ?, ?)", (name, due, get_username()))
        conn.commit()
        conn.close()
        return redirect(url_for("assignments"))
    else:
        return jsonify("Not allowed",403)
@app.route('/delete/<id>', methods=["GET"])
def delete(id):
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
@app.route('/home')
def home():
    return redirect(url_for("index"))
@app.route("/login", methods=["GET", "POST"])
def login():
    print(session.get('user'))
    if session.get('user') is not None:
        conn = sqlite3.connect("login.db")
        cursor = conn.cursor()  
        cursor.execute("SELECT email from login WHERE name=?", (session["user"],))
        session['email']=cursor.fetchall()[0][0]
        conn.close()
        return render_template('loggedin.html',name=get_username(),email=session["email"])
    if request.method == "POST":
        name = request.form["name"]
        name = name.lower()
        password = request.form["password"]
        passwrd = hashlib.sha256()
        passwrd.update(password.encode('utf-8'))
        conn = sqlite3.connect("login.db")
        cursor = conn.cursor()  
        cursor.execute("SELECT COUNT(*) FROM login WHERE name=? AND password=?", (name, passwrd.hexdigest()))
        conn.commit()
        valid = cursor.fetchall()[0]
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
            conn = sqlite3.connect("login.db")
            cursor = conn.cursor()  
            cursor.execute("SELECT COUNT(*) FROM login WHERE name=?", (name,))
            conn.commit()
            same_name = cursor.fetchall()[0]
            cursor.execute("SELECT COUNT(*) FROM login WHERE email=?", (email,))
            conn.commit()
            same_email = cursor.fetchall()[0]
            if same_name[0] == 0 and same_email[0] == 0:
                password = password.encode('utf-8')
                passwd = hashlib.sha256()
                passwd.update(password) 
                cursor.execute("INSERT INTO login (name, password, email) VALUES (?, ?, ?)", (name,passwd.hexdigest(),email))
                conn.commit()
                conn.close()
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
        conn = sqlite3.connect("login.db")
        cursor = conn.cursor()  
        cursor.execute("SELECT COUNT(*) FROM login WHERE name=? AND password=?", (get_username(), oldpasswd.hexdigest()))
        conn.commit()
        valid = cursor.fetchall()[0]
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
            cursor = conn.cursor()
            cursor.execute('UPDATE login SET password=? WHERE name=? AND password=?;',(newpasswd.hexdigest(),session['user'],oldpasswd.hexdigest()))
            conn.commit()
            conn.close()    
            return redirect(url_for("index"))  
        else:
            return render_template('resetpass.html', error="Current password does not exist in the database")
    else:
        return render_template("resetpass.html", name=get_username())

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")