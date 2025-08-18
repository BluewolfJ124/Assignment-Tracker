from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'm42MtecMxOW5STDs'  # Required for session management
# Configuration for file uploads
app.config['UPLOAD_FOLDER'] = 'uploads'

def days_between_dates(dt): # Function to get the difference in dates
    date1 = datetime.now().date() 
    date2 = datetime.strptime(dt, '%Y-%m-%d').date() 
    delta = date2 - date1
    return delta.days # Returns the difference in days


    
def init_sqlite_db(): # Create the db if it doesn't exist
    conn = sqlite3.connect('login.db') 
    conn.execute('''
                CREATE TABLE IF NOT EXISTS login (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name VARCHAR(255), password VARCHAR(255), 
                email TEXT NOT NULL)
                ''')   
    conn.execute('''
                CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userid INTEGER, 
                name TEXT NOT NULL, 
                date_due TEXT, 
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                image_filename TEXT)
                ''')     
    conn.close() 

def rw_from_db(write,query, params=()): # Read and write to sql database function
    conn = sqlite3.connect("login.db") # Connect to the database
    cursor = conn.cursor() 
    cursor.execute(query, params) # Excute the command with the given parameters
    conn.commit()
    if write==False: # If the command is reading
        items = cursor.fetchall() # Get the result
        conn.close()
        return items # Return the result
    else:
        conn.close()
        return # If the command is write, return nothing

@app.route('/') # Route for index
def index(): 
    return render_template('index.html')  

@app.route('/assignments') 
def assignments():
    if session.get('user') is not None: 
        items = rw_from_db(False, "SELECT id, name, date_due, subject from assignments WHERE id=?", (session["user"],)) # Get assignment data
        newitems=[]
        for i in items:
            newitems.append((i[0],i[1],i[2],days_between_dates(i[3])))
            
        return render_template('assignments.html', items=newitems) 
    else:
        return redirect(url_for("login")) # If there is no user, send them to login page
# Route to serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/newassignment', methods=["POST"]) # Post request made by the form
def newassignment():
    if request.method == 'POST': 
        date = request.form['date']
        name = request.form['name']
        description = request.form['description']
        subject = request.form['subject']
        image = request.files['image']
        image_filename = None
        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        with sqlite3.connect("login.db") as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO assignments (due_date, name, subject, description, image_filename) VALUES (?, ?, ?, ?)',
                           (date, name, subject, description, image_filename))
            conn.commit()
        return redirect(url_for("assignments"))
    else:
        return render_template('add.html')
    

@app.route('/delete/<id>', methods=["GET"])
def delete(id):
    # Theres a pretty major vunerablility here where anyone can delete an assignment if they just input and id, and are logged into any account
    # TODO: Check if the user is the owner of the assignment before deleting it
    if session.get('user') is not None:
        try: 
            rw_from_db(True,"DELETE FROM assignments WHERE id=?", (id,)) # Delete the item by id
        except:
            return redirect(url_for("assignments"))
        return redirect(url_for("assignments"))
    else:
        return jsonify("Not allowed",403)

@app.route("/login", methods=["GET", "POST"]) # Login route
def login():
    if session.get('user') is not None: # If user is logged in, send them to the logged in page
        data = rw_from_db(False,"SELECT name, email from login WHERE name=?", (session["user"],))
        name= data[0][0]
        email=data[0][1] # Display the email data
        return render_template('loggedin.html',email=email)
    if request.method == "POST": # If it is a login POST request
        name = request.form["name"] # Get the name and password
        name = name.lower()
        password = request.form["password"]
        valid = rw_from_db(False, "SELECT password, id FROM login WHERE name=?", (name,)) # Get hashed password from database from user
        print(valid)
        if len(valid) > 0 and check_password_hash(valid[0][0],password): # Check if the hash of the password is the same
            session['user'] = valid[0][1]
            return redirect(url_for("index"))
        else:
            return render_template('login.html',error='Username or password do not match any accounts in the database.') # If the password hash is invalid, return error
    return render_template('login.html',error='') # If it is a GET request, send them to the login page with no error
    
@app.route('/logout')
def logout(): # When the user sends a logout request, it clears all their session variables
    session.clear()
    return redirect(url_for("index"))

@app.route("/create", methods=["GET", "POST"]) # Route for signing up (creating a new account)
def create(): 
    if request.method == "POST": # If it is a sign up POST request
        name = request.form["name"] # Get the username, email, password and confirm password from the form
        name = name.lower()
        email = request.form["email"]
        email = email.lower()
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]
        if " " in name or " " in password or name=="login" or " " in email: # Check if there are spaces in the characters
            return render_template('signup.html', error="Username or Email is invalid")
        elif len(name) > 20: # Check if the username is over 20 characters
            return render_template('signup.html', error="Username has to be less than 20 characters")
        elif not confirm_password == password: # Check if the password, and confirm password are the same
            return render_template('signup.html', error="Passwords do not match!")
        else:
            same_name = rw_from_db(False, "SELECT COUNT(*) FROM login WHERE name=?", (name,))[0] # Check if there is the same username
            same_email=rw_from_db(False,"SELECT COUNT(*) FROM login WHERE email=?", (email,))[0] # Check if there is the same email
            if same_name[0] == 0 and same_email[0] == 0:
                rw_from_db(True,"INSERT INTO login (name, password, email) VALUES (?, ?, ?)", (name,generate_password_hash(password),email)) # Write the new user data to the database
                id = rw_from_db(False, "SELECT id FROM login WHERE name=?", (name,))
                session["user"] = id # Login to the session by setting the session user
                return redirect(url_for("index"))
            else:
                return render_template('signup.html', error="Username or Email has been taken") # Return if there is the same username
    return render_template('signup.html', error="") # If it is a GET request, render the webpage with no error

if __name__ == '__main__':
    init_sqlite_db() # Initialise the database
    app.run(debug=True)