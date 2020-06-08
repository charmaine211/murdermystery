import os
import requests
import urllib.parse

from cs50 import SQL
from flask import redirect, render_template, request, session
from functools import wraps


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///murdermystery.db")

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/games")
        return f(*args, **kwargs)
    return decorated_function


def special_chars(word):

    characters = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '<', '>', '[', ']', '{','}','|',';',':','§','±','€', '_', '-', '+', '=', '%', '^', '?', '/', '.']

    if any(spec_char in characters for spec_char in word):

        return True

    return False


def deslogify(word):

    word = word.replace("_", " ").replace("-", " ").title()

    return word


def slogify(word):

    word = word.replace(" ", "-").lower()

    return word


def validate_player(user_id, teamname_url):

    # Select the team_id where teamname is teamname
    team = db.execute("SELECT id, teamtable FROM teams WHERE name = :teamname", teamname = teamname_url)

    if len(team) != 0:

        users = db.execute("SELECT user_id FROM :teamtable", teamtable = team[0]["teamtable"])

         # Check if username is already exists.
        for user in users:

            if user["user_id"] == user_id:

                return True

    return False


def validate_teamhost(user_id, teamname_url):

    # Select the team_id where teamname is teamname
    team = db.execute("SELECT id, teamtable FROM teams WHERE name = :teamname", teamname = teamname_url)

    if len(team) != 0:

        # The first user added to the team is the host
        user = db.execute("SELECT user_id FROM :teamtable WHERE id = 1", teamtable = team[0]["teamtable"])

         # Check if username is already exists.
        if user[0]["user_id"] == user_id:

            return True

    return False


def send_invite(teamname_url):

    # Select the team_id where teamname is teamname
    team = db.execute("SELECT teamtable FROM teams WHERE name = :teamname", teamname = teamname_url)

    users = db.execute("SELECT user_id FROM :teamtable", teamtable = team[0]["teamtable"])

    if len(users) > 1:

        return False

    return True


# Souce: https://thispointer.com/python-3-ways-to-check-if-there-are-duplicates-in-a-list/
def checkIfDuplicates(listOfElems):
    ''' Check if given list contains any duplicates '''
    if len(listOfElems) == len(set(listOfElems)):

        return False

    else:

        return True

# Teamtable
def teamtable(teamname_url):
    # Add user_id to teamtable
    teamtable = db.execute("SELECT teamtable FROM teams WHERE name = :teamname", teamname = teamname_url)[0]["teamtable"]

    return teamtable
