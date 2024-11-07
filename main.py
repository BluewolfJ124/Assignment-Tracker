from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'm42MtecMxOW5STDs'  # Required for session management
def days_between_dates(dt): # Function to get the difference in dates
    date1 = datetime.now().date() 
    date2 = datetime.strptime(dt, '%Y-%m-%d').date() 
    delta = date2 - date1
    return delta.days # Returns the difference in days
 
def get_username(): # Function that returns the username, mostly for the navbar
    if session.get('user') is not None:
        return session['user']
    else:
        return "Login" # If there is no user, just set the word to login
    
def init_sqlite_db(): # Create the db if it doesn't exist
    conn = sqlite3.connect('login.db') 
    conn.execute('CREATE TABLE IF NOT EXISTS login (id INTEGER PRIMARY KEY AUTOINCREMENT, name VARCHAR(255), password VARCHAR(255), email STR)')     # Execute SQL command to create 'login' table with id, username, password, and email columns
    conn.execute('CREATE TABLE IF NOT EXISTS assignments (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, date_due TEXT, user TEXT, completed BOOLEAN DEFAULT FALSE)')     # Execute SQL command to create 'assignments' table with id, name, due_date, user, and completed columns
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
    return render_template('index.html',name=get_username())  

@app.route('/assignments') 
def assignments():
    if session.get('user') is not None: 
        items = rw_from_db(False, "SELECT id, name, date_due, completed from assignments WHERE user=?", (session["user"],)) # Get assignment data
        uncompleted = [] # Create empty lists
        completed = []   # Of completed and uncompleted assignments
        for i in items: # Iterate through every item from the database
            if i[3] == False: # Check if it is comepleted
                uncompleted.append((i[1],days_between_dates(i[2]),i[0])) # Add the name, difference in dates, and the id
            else:
                if days_between_dates(i[2]) < -14: 
                    delete(i[0]) 
                else:
                    completed.append((i[0],i[1])) # Add the name and id
        return render_template('assignments.html',name=get_username(), items=uncompleted, completed=completed) # Send the completed + uncompleted assignments to the webpage  
    else:
        return redirect(url_for("login")) # If there is no user, send them to login page
    
@app.route('/newassignment', methods=["POST"]) # Post request made by the form
def newassignment():
    if session.get('user') is not None: 
        name = request.form["name"] # Get the name of the assignment
        due = request.form["due"] # Get the due date of the assignment
        rw_from_db(True,"INSERT INTO assignments (name, date_due, user) VALUES (?, ?, ?)", (name, due, get_username())) # Add the data to the database
        return redirect(url_for("assignments"))
    else:
        return jsonify("Not allowed",403) # Non authenticated users are not able to create assignments
    
@app.route('/finish/<id>', methods=["GET"]) # Form sends a get request to delete the assignment by id
def finish(id):
    if session.get('user') is not None:
        try: 
            rw_from_db(True,"UPDATE assignments SET completed=TRUE WHERE id=?", (id,)) # Set the assignment to completed
        except:
            return redirect(url_for("assignments")) 
        return redirect(url_for("assignments")) # If there is no id just return back 
    else:
        return jsonify("Not allowed",403) # Non authenticated users are not able to delete assignments
    
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
        email = rw_from_db(False,"SELECT email from login WHERE name=?", (session["user"],))
        email=email[0][0] # Display the email data
        return render_template('loggedin.html',name=get_username(),email=email)
    if request.method == "POST": # If it is a login POST request
        name = request.form["name"] # Get the name and password
        name = name.lower()
        password = request.form["password"]
        valid = rw_from_db(False, "SELECT password FROM login WHERE name=?", (name,)) # Get hashed password from database from user
        print(valid)
        if len(valid) > 0 and check_password_hash(valid[0][0],password): # Check if the hash of the password is the same
            session['user'] = name
            return redirect(url_for("index"))
        else:
            return render_template('login.html',error='Username or password do not match any accounts in the database.',name=get_username()) # If the password hash is invalid, return error
    return render_template('login.html',error='',name=get_username()) # If it is a GET request, send them to the login page with no error
    
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
                session["user"] = name # Login to the session by setting the session user
                return redirect(url_for("index"))
            else:
                return render_template('signup.html', error="Username or Email has been taken",name=get_username()) # Return if there is the same username
    return render_template('signup.html', error="",name=get_username()) # If it is a GET request, render the webpage with no error

if __name__ == '__main__':
    init_sqlite_db() # Initialise the database
    app.run(debug=True, host="0.0.0.0")