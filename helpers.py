import csv
import os
import urllib.request
import sqlite3
from flask import redirect, render_template, request, session
from functools import wraps
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

port = 465  # For SSL
smtp_server = "smtp.gmail.com"
sender_email = "8depr69@gmail.com"  # Enter your address
password = "porsche911gt3rs4.0"

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

def is_impostor(fren, notfren):
    if str(fren) != str(notfren):
        return True
    else:
        return False

def welcome(email, name):
    message = MIMEMultipart("alternative")
    message["Subject"] = "Welcome and thank you for joining, whatever your name is"
    message["From"] = sender_email
    message["To"] = email

    text = """\
    Hi,
    Firstly, I'd like to personally thank you for joining my shitty site, really means a lot.
    Secondly, FUCKING INTERACT WITH ME PLEASEEEEEEEEEEE.
    Post an intro or something
    http://8bitrebellion.pythonanywhere.com"""
    html = """\
    <html>
        <body>
            <p>Hi,<br>
            Secondly, FUCKING INTERACT WITH ME PLEASEEEEEEEEEEE.<br>
            Firstly, I'd like to personally thank you for joining my shitty site, really means a lot.<br>
            Post an intro or something<br>

            <a href="http://8bitrebellion.pythonanywhere.com">To the site</a>
            </p>
        </body>
    </html>
    """
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    message.attach(part1)
    message.attach(part2)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())
def deeplist(x):
    """fully copies trees of tuples to a tree of lists.
       deep_list( (1,2,(3,4)) ) returns [1,2,[3,4]]"""
    a = []
    for t in x:
        a.append(list(t))
    return a

def dated(tupe, idx):
    """Converts strs into datetime objects for moment.js"""
    tupe = deeplist(tupe)
    for i in range(0, len(tupe)): #converts to list and changes all dates to datetime, do the same with the get request
        #tupe[i][idx] = tupe[i][idx].replace(microsecond=0)
        try:
            tupe[i][idx] = datetime.strptime(tupe[i][idx], '%Y-%m-%d %H:%M:%S.%f')
        except:
            tupe[i][idx] = datetime.strptime("2019-11-09 00:06:04.164378", '%Y-%m-%d %H:%M:%S.%f')
    return tupe