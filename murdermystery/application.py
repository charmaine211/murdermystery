import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Mail, Message

from helpers import apology, login_required, special_chars, slogify, deslogify, validate_player, send_invite, checkIfDuplicates, validate_teamhost, teamtable
from safespace import gmail

# Configure application
app = Flask(__name__)

# Mail setup
mail_settings = {
    "MAIL_SERVER": 'smtp.gmail.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": 'charmaine211@gmail.com',
    "MAIL_PASSWORD": gmail()
}


app.config.update(mail_settings)
mail = Mail(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"

    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///murdermystery.db")


@app.route("/")
@login_required
def index():

    return redirect("/teams")


@app.route("/games")
@login_required
def games():

    games = db.execute("SELECT * FROM games")

    return render_template("games.html", games=games)


@app.route("/<game>")
@login_required
def game(game):

    user_id = session["user_id"]

    name = deslogify(game)

    game_info = db.execute("SELECT * FROM games WHERE name = :name", name = name)

    if len(game_info) < 1:

        if validate_player(user_id, game) == False:

            return redirect ("/games")

    characters = db.execute("SELECT name, description FROM characters WHERE game_id=:game_id", game_id=game_info["id"])

    return render_template("game.html", game_info=game_info, characters=characters)


@app.route("/teams")
@login_required
def teams():

    user_id = session["user_id"]

    team_list = []

    teams = db.execute("SELECT id, name, teamtable FROM teams")

    nr_of_teams = len(teams)

    for index in range(nr_of_teams):

        users = db.execute("SELECT user_id FROM :teamtable", teamtable = teams[index]["teamtable"])

        for user in users:
            if user["user_id"] == user_id:

                team_list.append(teams[index]["name"])

    valid_teams = len(team_list)

    return render_template("teams.html", valid_teams = valid_teams, team_list = team_list)


@app.route("/create-a-new-team", methods=["GET", "POST"])
@login_required
def create_a_new_team():

    user_id = session["user_id"]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        new_teamname = request.form.get("teamname")
        game = deslogify(request.form.get("games"))

        if not game:
            return apology("Please select a game", 403)

        if not new_teamname:
            return apology("Must provide a teamname", 403)

        if special_chars(new_teamname):
            return apology("It is not allowed to use special characters", 403)

        teamname_url = slogify(new_teamname)

        # Query database for teamnames
        teamname_list = db.execute("SELECT name FROM teams")

        gamename_list = db.execute("SELECT name FROM games")

        # Check if username is already exists.
        for row in teamname_list:
            if row["name"] == teamname_url:
                return apology("Sorry, this teamname has already been taken. Try something else", 403)

        for game in gamename_list:
            if game["name"] == teamname_url:
                return apology("Sorry, this teamname is not allowed. Try something else", 403)

        # Query over db for amount of players and game id
        game_id = db.execute("SELECT id FROM games WHERE name = :game", game = game)[0]["id"]

        team_id = db.execute("INSERT INTO teams (name, game_id, teamtable) VALUES (:teamname, :game_id, '0')", {"teamname": teamname_url, "game_id": game_id})

        teamtable = "team_" + str(team_id)

        db.execute("UPDATE teams SET teamtable = :teamtable WHERE id = :team_id", {"teamtable": teamtable, "team_id": team_id})

        # Create a new table with teamname
        db.execute("CREATE TABLE :teamtable (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER NOT NULL, char_id INTEGER NOT NULL, current_round INTEGER NOT NULL)", teamtable = teamtable)

        db.execute("INSERT INTO :teamtable (user_id, char_id, current_round) VALUES (:user_id, 0, 0)", {"user_id": user_id, "teamtable": teamtable})

        return redirect("/<teamname_url>")

    else:

        return render_template("create-a-new-team.html")


@app.route("/<teamname_url>")
@login_required
def teamname_url(teamname_url):

    user_id = session["user_id"]


    if validate_player(user_id, teamname_url) == True:

            # Do stuff with the information from the tables
            teamname = deslogify(teamname_url)

            return render_template("teampage.html", teamname = teamname, invite = send_invite(teamname_url), teamname_url=teamname_url)

    return redirect("/create-a-new-team")


@app.route("/<teamname_url>/invite", methods=["GET", "POST"])
@login_required
def invite(teamname_url):

    user_id = session["user_id"]

    game_id = (db.execute("SELECT game_id FROM teams WHERE name = :teamname_url", teamname_url = teamname_url))[0]["game_id"]

    players = (db.execute("SELECT players FROM games WHERE id = :game_id", game_id = game_id))[0]["players"]

    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":

        # Check if the player is the teamhost
        if validate_teamhost(user_id, teamname_url) == False:

            return redirect("/create-new-team")

        elif send_invite(teamname_url) == False:

            return redirect("/")

        return render_template("invite.html", players = players, teamname_url = teamname_url)

    else:

        emails = []
        names = []

        user_emails = db.execute("SELECT email FROM users")

        # User is also part of team
        friends = players - 1

        # Min 1 omdat de eerste user al in de lijst staat
        for index in range(friends):

            player = index + 1

            email_id = "email" + str(player)
            name_id = "name" + str(player)

            if not request.form.get(email_id):

                warning_email = "Please provide the email" + str(player)

                return apology(warning_email, 403)

            if not request.form.get(name_id):

                warning_name = "Please provide the name" + str(player)

                return apology(warning_name, 403)

            emails.append(request.form.get(email_id))
            names.append(request.form.get(name_id).title())

            """with app.app_context():
                msg = Message(subject="Hello",
                              sender=app.config.get("MAIL_USERNAME"),
                              recipients=['charmaine211@hotmail.com'],
                              body="This is a test email I sent with Gmail and Python!")
                mail.send(msg)"""

        # Check for doubles
        if checkIfDuplicates(emails) == True:

            return apology("You can't invite the same friend twice", 403)

        # Check for user_id friend
        for index in range(len(emails)):
            id_counter = 0

            # Check if user already exists
            for row in user_emails:
                id_counter += 1

                if row["email"] == emails[index]:
                    user_id = id_counter

            # No user_id found, then create one
            if not user_id:
                user_id = db.execute("INSERT INTO users (email) VALUES(:email)", email = emails[index])

            db.execute("INSERT INTO :teamtable (user_id, char_id, current_round) VALUES(:user_id, 0, 0)", {"teamtable" : teamtable(teamname_url), "user_id" : user_id})

        # Redirect user to home page
        return redirect("/<teamname_url>/choose-characters")


@app.route("/<teamname_url>/choose-characters", methods=["GET", "POST"])
@login_required
def choose_characters(teamname_url):

    user_id = session["user_id"]

    player_ids = []
    characters = []
    users = []

    if request.method == "GET":

        # Check if player is the team host
        if validate_teamhost(user_id, teamname_url) == False:

            return redirect("/create-new-team")

        # Check if all the candidates are invited
        elif send_invite(teamname_url) == True:

            # return redirect("/<teamname_url>/invite")
            return redirect("/<teamname_url>")

        player_ids = db.execute("SELECT user_id, id FROM :teamtable", teamtable = teamtable(teamname_url))
        game_id = db.execute("SELECT game_id FROM teams WHERE name = :team_name", team_name = teamname_url)[0]["game_id"]

        characters = db.execute("SELECT id, name, description FROM characters WHERE game_id = :game_id", game_id = game_id)

        nr_characters = len(characters)

        for i in range(nr_characters):

            users.append(db.execute("SELECT username, email FROM users WHERE id = :id", id = player_ids[i]["user_id"]))

        # Returns 2 lists with dicts containing character en user info
        return render_template("choose-characters.html", characters = characters, users = users, nr_characters = nr_characters)

    else:

        player_list = []

        for i in range(len(characters)):

            player_list.append(request.form.get(str(i)))

        # Make sure the host only assigns 1 character to 1
        if checkIfDuplicates(player_list):

            return apology("Players can only have 1 character", 403)

        # Add the char id to the teamtable


        # Redirect user to home page
        return redirect("/<teamname_url>")


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
        user_list = db.execute("SELECT username, email FROM users")

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

        # Ask for a password
        password = request.form.get("password")

        # Check if password valid
        if not len(password) > 7:
            return apology("Password has to be at least 8 characters long", 403)

        elif not special_chars(password):
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

       # Check if username or email is already exists.
        for row in user_list:
            # Check username, seperate from email bc can't exist already
            if row["username"] == new_username:
                return apology("Sorry, this username has already been taken. Try something else", 403)

            if row["email"] == new_email:
                # When the player is already added to the userlist, username and password are temp
                if row["username"] == "temp":
                    db.execute("UPDATE users SET username = :new_username, hash = :hash_password WHERE email = :new_email", {"new_username": new_username, "hash_password": hash_password, "new_email": new_email})
                    user_id = row + 1
                else:
                    return apology("Sorry, this email already has an account.", 403)

        if not user_id:
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
