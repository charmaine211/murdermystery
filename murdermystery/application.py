import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, special_chars, slogify, deslogify, validate_player, send_invite, checkIfDuplicates, validate_teamhost, teamtable
from safespace import gmail

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

    return render_template("index.html", valid_teams = valid_teams, team_list = team_list)


@app.route("/games")
def games():

    valid_account = True

    if session.get("user_id") is None:

        valid_account = False

    games = db.execute("SELECT * FROM games")

    return render_template("games.html", games = games, valid_account = valid_account)


@app.route("/<game_or_team>")
@login_required
def game_or_team(game_or_team):

    user_id = session["user_id"]

    name = deslogify(game_or_team)

    # Check if game_or_team is a team the user is part of
    if validate_player(user_id, game_or_team) == True:

        teamname_url = game_or_team

        team = []

        # Query over the characters
        team_ids = db.execute("SELECT user_id, char_id FROM :teamtable", teamtable = teamtable(teamname_url))

        # Make sure the characters are assigned before it is safed in teams
        if team_ids[0]["char_id"] != 0:

            for i in range(len(team_ids)):

                player = db.execute("SELECT username, email FROM users WHERE id = :user_id", user_id = team_ids[i]["user_id"])
                player.update(db.execute("SELECT name, description FROM characters WHERE id = :char_id", char_id = team_ids[i]["char_id"]))
                team.append(player)

        return render_template("team.html", teamname = name, host = validate_teamhost(user_id, teamname_url), invite = send_invite(teamname_url), teamname_url = teamname_url, team = team)

    # Query over the game names
    game_info = db.execute("SELECT * FROM games WHERE name = :name", name = name)

    # When there's a match, go to the game page
    if len(game_info) != 0:

        characters = db.execute("SELECT name, description FROM characters WHERE game_id=:game_id", game_id=game_info[0]["id"])

        return render_template("game.html", game_info=game_info[0], characters=characters)

    else:

        # When it's neither a team or a game, redirect the user back to
        return redirect("/")


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

        for game_name in gamename_list:
            if game_name["name"] == teamname_url:
                return apology("Sorry, this teamname is not allowed. Try something else", 403)

        # Query over db for amount of players and game id
        game_info = db.execute("SELECT id, players FROM games WHERE name = :game", game = game)
        game_id = game_info[0]["id"]

        team_id = db.execute("INSERT INTO teams (name, game_id, teamtable) VALUES (:teamname, :game_id, '0')", {"teamname": teamname_url, "game_id": game_id})

        teamtable = "team_" + str(team_id)

        db.execute("UPDATE teams SET teamtable = :teamtable WHERE id = :team_id", {"teamtable": teamtable, "team_id": team_id})

        # Create a new table with teamname
        db.execute("CREATE TABLE :teamtable (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER NOT NULL, char_id INTEGER NOT NULL, current_round INTEGER NOT NULL)", teamtable = teamtable)

        db.execute("INSERT INTO :teamtable (user_id, char_id, current_round) VALUES (:user_id, 0, 0)", {"user_id": user_id, "teamtable": teamtable})

        for player in range(game_info[0]["players"]):

            columnname = "player_id_" + str(player+1)

            db.execute("ALTER TABLE :teamtable ADD COLUMN :columnname text DEFAULT 'blank' NOT NULL", {"teamtable" : teamtable, "columnname" : columnname})

        return redirect(url_for('game_or_team', game_or_team = teamname_url))

    else:

        return render_template("create-a-new-team.html")


@app.route("/<teamname_url>/invite", methods=["GET", "POST"])
@login_required
def invite(teamname_url):

    user_id = session["user_id"]

    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":

        # Check if the player is the teamhost
        if validate_teamhost(user_id, teamname_url) == False:

            return redirect("/create-new-team")

        if send_invite(teamname_url) == False:

            return redirect(url_for('game_or_team', game_or_team = teamname_url))

        game_id = (db.execute("SELECT game_id FROM teams WHERE name = :teamname_url", teamname_url = teamname_url))[0]["game_id"]

        players = (db.execute("SELECT players FROM games WHERE id = :game_id", game_id = game_id))[0]["players"]

        return render_template("invite.html", players = players, teamname_url = teamname_url)

    else:

        names = []

        usernames = db.execute("SELECT id, username FROM users")

        game_id = (db.execute("SELECT game_id FROM teams WHERE name = :teamname_url", teamname_url = teamname_url))[0]["game_id"]

        players = (db.execute("SELECT players FROM games WHERE id = :game_id", game_id = game_id))[0]["players"]

        # Current user is also part of team
        friends = players - 1

        # Check if all the usernames are put in correctly
        for index in range(friends):

            player = index + 1

            form_name = "username" + str(player)

            if not request.form.get(form_name):

                return apology("Please fill out all the usernames", 403)

            names.append(request.form.get(form_name))


        if checkIfDuplicates(names) == True:

            return apology("You can't invite the same friend twice", 403)

        # Check if username exist
        player_ids = []

        error_list = []

        for friend in range(friends):

            exist = False

            # Check if user already exists
            for user in usernames:

                if user["username"] == names[friend]:

                    player_ids.append(user["id"])
                    exist = True

            if exist == False:

                error_list.append(names[friend])


        if len(error_list) > 0:

            errors = ', '.join(error_list)

            warning_message = "The following users do not exist: " + errors

            return apology(warning_message, 403)

        for i in range(len(player_ids)):

            db.execute("INSERT INTO :teamtable (user_id, char_id, current_round) VALUES(:user_id, 0, 0)", {"teamtable" : teamtable(teamname_url), "user_id" : player_ids[i]})

        # Redirect user to home page
        return redirect(url_for('choose_characters', teamname_url = teamname_url))


@app.route("/<teamname_url>/choose-characters", methods=["GET", "POST"])
@login_required
def choose_characters(teamname_url):

    user_id = session["user_id"]

    player_ids = []
    characters = []
    users = []
    nr_characters = 0

    if request.method == "GET":

        # Check if player is the team host
        if validate_teamhost(user_id, teamname_url) == False:

            return redirect("/create-new-team")

        # Check if all the candidates are invited
        elif send_invite(teamname_url) == True:

            return redirect(url_for('invite', teamname_url = teamname_url))

        player_ids = db.execute("SELECT user_id, id FROM :teamtable", teamtable = teamtable(teamname_url))
        game_id = db.execute("SELECT game_id FROM teams WHERE name = :team_name", team_name = teamname_url)[0]["game_id"]

        characters = db.execute("SELECT id, name, description FROM characters WHERE game_id = :game_id", game_id = game_id)

        nr_characters = len(characters)

        for i in range(nr_characters):

            if player_ids[i]["user_id"] == user_id:

                current_user = db.execute("SELECT id FROM users WHERE id = :id", id = player_ids[i]["user_id"])[0]
                current_user.update(username = 'Me')
                users.append(current_user)

            else:

                users.append(db.execute("SELECT id, username FROM users WHERE id = :id", id = player_ids[i]["user_id"])[0])

        # Returns 2 lists with dicts containing character en user info
        return render_template("choose-characters.html", characters = characters, teamname_url = teamname_url, users = users, nr_characters = nr_characters)

    else:

        # Create a new list to store the user indexes in the character index
        character_userlist = []

        # The characters are static, 0 - len(characters). So the the teamid's are placed in the index of the character.
        for i in range(nr_characters):

            character_userlist.append(request.form.get(str(i)))

        # Make sure the host only assigns 1 character to 1
        if checkIfDuplicates(character_userlist):

            return apology("Players can only have 1 character", 403)


        # Add the char id to the teamtable
        for j in range(nr_characters):

            # character_userlist[j] is the users index
            # users[character_userlist[j]]["id"]
            # characters[j]["id"] is the character id

            # Add the character index to the teamtable where user_id = characterlist[j]
            db.execute("UPDATE :teamtable SET char_id = :char_id WHERE user_id = :user_id", {"teamtable" : teamtable(teamname_url), "char_id" : characters[j]["id"], "user_id" : users[character_userlist[j]]["id"]})

        # Redirect user to home page
        return redirect(url_for('game_or_team', game_or_team = teamname_url))


@app.route("/<teamname_url>/<int:r>", methods=["GET", "POST"])
@login_required
def round(teamname_url, r):

    user_id = session["user_id"]

    # Check if player is part of the team
    if validate_player(user_id, teamname_url) == False:

        return redirect("/create-new-team")

    # Check if all the candidates are invited
    if send_invite(teamname_url) == True:

        return redirect(url_for('invite', teamname_url = teamname_url))

    # Check if the characters have been chosen, at the same time check if they started the game (round 0)
    team_info = db.execute("SELECT char_id, current_round FROM :teamtable", teamtable = teamtable(teamname_url))

    if team_info[0]["char_id"] == 0 or r == 0:

        return redirect(url_for('game_or_team', game_or_team = teamname_url))

    # Round is only available when all the characters are there.
    for i in range(len(team_info)):

        if team_info[i]["current_round"] < r:

            # Send the user back to the lowest previous round
            return redirect(url_for('round', teamname_url = teamname_url, r = i))

    game_id = db.execute("SELECT game_id FROM teams WHERE id = :team_id", team_id = int(teamtable(teamname_url).replace("team_","")))[0]["game_id"]

    game_name = db.execute("SELECT name FROM games WHERE id = :game_id", game_id = game_id)[0]["name"]

    game_table = game_name.lower().replace(" ","")

    game_info = db.execute("SELECT * FROM :game_table WHERE char_id = :char_id AND round = :r", {"game_table": game_table, "char_id" : team_info[0]["char_id"], "r" : r})

    # Return the round template that is dynamically created
    return render_template("round.html", r = r, game_info = game_info)


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

        # Ensure username was submitted or not already in list
        new_username = request.form.get("username")

        # Check if user has provided a new username
        if len(new_username) < 4 or len(new_username) > 15:
            return apology("Choose a username with a length between 4 and 15 characters", 403)

        # Check if username is already exists.
        for row in username_list:
            if row["username"] == new_username:
                return apology("Sorry, this username has already been taken. Try something else", 403)

        """ PROVIDE PASSWORD """

        # Ask for a password
        password = request.form.get("password")

        # Check if password valid
        if not len(password) > 7:
            return apology("Password has to be at least 8 characters long", 403)

        elif special_chars(password) == False:
            return apology("Password has to have at least 1 special character: ", 403)

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
        user_id = db.execute("INSERT INTO users (username, hash) VALUES (:new_username, :hash_password)", {"new_username": new_username, "hash_password": hash_password})

        # Remember which user has logged in
        session["user_id"] = user_id

        return redirect ("/")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
