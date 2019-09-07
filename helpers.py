import csv
import os
import urllib.request
import sqlite3
from flask import redirect, render_template, request, session
from functools import wraps

conn = sqlite3.connect("/home/8bitRebellion/tvent/tvent3.6/flask-blog/workspace/blog/app.db")

def apology(message, code):
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
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def sanitize(a):
    b = ''
    a = str(a)
    for char in a:
        if char == "'":
            b = b + '\\\\' + char           #requires two slashes but need to escape those for python
        else:
            b = b + char
    b = "'" + str(b) + "'"
    return b

def sanitize_t(a):
    a = str(a)[:-2]
    a = a[1:]
    return a

def shag(a):
    a = a[0]
    b = []
    for i in a:
        b.append(i)
    return b

def flatten(a):
    flat_list = ''
    for sublist in a:
        for elem in list(sublist):
            flat_list += str(elem)
    return(flat_list)

def admin_only(f):
    """
    for admin only routes
    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("perms") != "admin":
            return apology("Sorry you aren't an elite hacker like myself", 69420)
        return f(*args, **kwargs)
    return decorated_function
