import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
'''app.jinja_env.filters["usd"] = usd'''

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///murdermystery.db")

'''# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")'''


@app.route("/")
@login_required
def index():

    user_id = session["user_id"]

    # Return current_balance, stock (a list containg lists with the stock info) and nr_symbols (number of symbols)
    return render_template("index.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    # User reached route via GET
    if request.method == "GET":

        # Display quote
        return render_template("buy.html")

    # User reached route via POST
    else:

        # Redirect user to home page
        return redirect("/")


@app.route("/history")
@login_required
def history():

    """Show history of transactions """
    user_id = session["user_id"]

    return render_template("history.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User reached route via GET
    if request.method == "GET":

        # Display quote
        return render_template("sell.html")

    # User reached route via POST
    else:

        # Redirect user to home page
        return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def teams():
    """Team page"""

    # User reached route via GET, when the team is set
    if request.method == "GET":

        # Display quote
        return render_template("teams.html")

    # User "host" reached route via POST. Only when host hasn't invited players
    else:

        # Display the quote for requested symbol
        return render_template("team_register.html")


@app.route("/login", methods=["GET", "POST"])
def user():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        ''' When the user wants to change their password, username or email. '''

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Show user information
        return render_template("user.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        ''' What if the user forgets their password? '''

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Forget any user_id
    session.clear()

    """ PROVIDE USERNAME """

    # User reached route via GET
    if request.method == "GET":

        # Display registration form
        return render_template("register.html")

    # User reached route via POST
    else:

        # Query database for username
        username_list = db.execute("SELECT username FROM users")

        # Query database for username
        email_list = db.execute("SELECT email FROM users")

        # Ensure username was submitted or not already in list
        new_username = request.form.get("username")

        # Ensure username was submitted or not already in list
        new_email = request.form.get("email")

        # Check if user has provided a new username
        if len(new_username) == 0:
            return apology("Please choose a username", 403)

        # Check if user has provided a new username
        if len(new_email) == 0:
            return apology("Please enter your email", 403)

        # Check if username is already exists.
        for row in username_list:
            if row["username"] == new_username:
                return apology("Sorry, this username has already been taken. Try something else", 403)

       # Check if username is already exists.
        for row in email_list:
            if row["email"] == new_email:
                return apology("Sorry, this email already has an account.", 403)


        """ PROVIDE PASSWORD """

        characters = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '<', '>', '[', ']', '{','}','|',';',':','§','±','€']

        # Ask for a password
        password = request.form.get("password")

        # Check if password valid
        if not len(password) > 7:
            return apology("Password has to be at least 8 characters long", 403)

        elif not any(spec_char in characters for spec_char in password):
            return apology("Password has to have at least 1 special character", 403)

        elif not any(char.isdigit() for char in password):
            return apology("Password has to contain at least 1 number", 403)

        elif not any(char.isupper() for char in password):
            return apology("Password has to contain at least 1 capitalized character", 403)

        # Apology if password and confirmation aren't the same
        elif not request.form.get("confirmation") == password:
            return apology("Passwords do not match", 403)

        """ INSERT NEW USER IN DB"""

        # Hash password
        hash_password = generate_password_hash(password, "sha256")

        # Insert username & hash in users
        user_id = db.execute("INSERT INTO users (username, hash, email) VALUES (:new_username, :hash_password, :new_email)", {"new_username": new_username, "hash_password": hash_password, "new_email": new_email})

        # Remember which user has logged in
        session["user_id"] = user_id

        return redirect ("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
