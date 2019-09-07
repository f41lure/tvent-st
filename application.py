# login, index, register functions ported.
# use flaskdebug_toolabr to print shit
# on 8/8/19, I got banned from yet another discord server for "being an ass"
# I guess I was
# open_post, edit, profile, new_post sql ported on 10/8/19
# still haven't fixed tuples/lists clash
# on 9/8/19, I was banned from yet another discord server for calling the owner edgy
# the owner said I had a low effort name and pfp
# I guess I do

from flask import *
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from helpers import *
from pathlib import Path
from cryptography.fernet import Fernet
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from flask_debug import Debug
from flask_debugtoolbar import DebugToolbarExtension
from flask_misaka import Misaka
import re
import uuid
import sqlite3

# configure application
app = Flask(__name__)

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = '8086'
app.debug = True
Session(app)
Misaka(app)

conn = sqlite3.connect("/home/8bitRebellion/tvent/tvent3.6/flask-blog/workspace/blog/app.db")
analyzer = SentimentIntensityAnalyzer()
global curr_id

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if request.form['qtag']:
            db = conn.cursor()
            app.logger.info(request.form)
            exe = "SELECT * FROM posts WHERE tag={}".format(sanitize(str(request.form.get("tag"))))
            app.logger.info(exe)
            posts = db.execute(exe).fetchall()
            try:
                curr_user = db.execute(("""SELECT username FROM users WHERE id=?""", [session["user_id"]])).fetchall()[0][0]
            except:
                pass
            conn.commit()
            return render_template("index.html", posts=posts, user=curr_user)                  # The link bypasses directly to the actual page

    elif request.method == "GET":
        db = conn.cursor()
        all_posts = db.execute("""SELECT * FROM posts WHERE ishidden = '1'""").fetchall()
        app.logger.info(all_posts)
        all_posts = db.execute("""SELECT * FROM posts""").fetchall()
        app.logger.info(all_posts)
        # data = db.execute("""SELECT * FROM entries WHERE id = :id""", id=session["user_id"])
        if request.args.get('sort') == "new":
            all_posts = db.execute("""SELECT * FROM posts""").fetchall()
            if "user_id" in session:
                exe = """SELECT username FROM users WHERE id = ?"""
                curr_user = db.execute(exe, [session["user_id"]]).fetchall()[0][0]
            else:
                curr_user = 'anon'
            app.logger.info(curr_user)
            return render_template("index.html", posts=list(reversed(list(all_posts))), user=curr_user)            #TODO FIX THIS
        elif request.args.get('sort') == "old":
            all_posts = db.execute("""SELECT * FROM posts""").fetchall()
            if "user_id" in session:
                exe = """SELECT username FROM users WHERE id=?"""
                curr_user = db.execute(exe, [session["user_id"]]).fetchone()[0][0]
                # ^ get username to pass as url parameter for profile() in case user
                # accesses their profile
            else:
                curr_user = 'anon'
            app.logger.info(curr_user)
            return render_template("index.html", posts=all_posts, user=curr_user)
        else:
            all_posts = db.execute("""SELECT * FROM posts""").fetchall()
            if "user_id" in session:
                exe = """SELECT username FROM users WHERE id = ?"""
                curr_user = db.execute(exe, [session["user_id"]]).fetchall()[0][0]
                # ^ get username to pass as url parameter for profile() in case user
                # accesses their profile
            else:
                curr_user = 'anon'
            app.logger.info(curr_user)
            return render_template("index.html", posts=all_posts, user=curr_user)




@app.route("/open_file", methods=["GET", "POST"])
def open_file():
    global postId
    global post_data
    global comments
    global sent
    global username
    if request.method == "GET":
        db = conn.cursor()
        try:
            exe = """SELECT * FROM users WHERE id = {}""".format(sanitize(session["user_id"]))
            user_data = db.execute(exe).fetchall()
            username = user_data[0][1]
        except:
            username = 'anon'

        postId = str(request.args.get('type'))           # dishes up the post using the URL parameter
        exe = """SELECT * FROM posts WHERE id = {}""".format(sanitize(postId))
        post_data = db.execute(exe).fetchall()

        exe = """SELECT * FROM comments WHERE post_id = {}""".format(sanitize(postId))
        #app.logger.info("comments: {}".format(exe))
        comments = db.execute(exe).fetchall()

        sent=float(post_data[0][6])

        conn.commit()
        return render_template("open.html", post=post_data, comments=comments, curr_username = username, sent=float(post_data[0][6])) # Last argument for curruser functions such as delete and edit

    elif request.method == "POST":
        db = conn.cursor()
        app.logger.info(request.form)
        if request.form['button'] == 'postComment':                                             # if the users presses the comment button
            comment_id = str(uuid.uuid4())
            exe = """SELECT * FROM users WHERE id={}""".format(sanitize(session["user_id"]))

            user_data = db.execute(exe).fetchall()
            exe = """INSERT INTO comments (comment_id, user_id, username, body, post_id, time)
                    VALUES ({}, {}, {}, {}, {}, {})""".format(sanitize(comment_id),\
                    sanitize(session["user_id"]),\
                    sanitize(user_data[0][1]),\
                    sanitize(request.form.get("comment")),\
                    sanitize(postId),\
                    sanitize(datetime.utcnow()))
            app.logger.info(exe)
            db.execute(exe)

            exe = """SELECT * FROM comments WHERE post_id = {}""".format(sanitize(postId))
            comments = db.execute(exe).fetchall()
            app.logger.info(comments)
            conn.commit()
            return render_template("open.html", post=post_data, comments=comments, sent=sent, curr_username=username)
        elif request.form['button'] == 'delete':
            db.execute("""DELETE FROM posts WHERE id={}""".format(sanitize(postId)))
            conn.commit()
            return redirect(url_for('index'))
        else:
            pass


@app.route("/editPost", methods=["GET", "POST"])
@login_required
def editPost():
    """Allow user to edit a previous post"""
    global param
    if request.method == "GET":
        param = request.args.get("type")
        return render_template("editPost.html")
    elif request.method == "POST":
        db = conn.cursor()
        exe = """UPDATE posts SET body={} WHERE id={}""".format(sanitize(request.form.get("entry")), sanitize(param))
        db.execute(exe)
        conn.commit()
        return redirect(url_for("index"))


@app.route("/new_entry", methods=["GET", "POST"])
@login_required
def new_entry():
    """Create a new entry."""
    if request.method == "POST":

        db = conn.cursor()
        exe = """SELECT * FROM users WHERE id = {}""".format(sanitize(session["user_id"]))
        user_data = db.execute(exe).fetchall()
        #app.logger.info("User data: {}".format(user_data))
        username = user_data[0][1]

        text = request.form.get("entry")
        sentiment = float(list(analyzer.polarity_scores(request.form.get("entry")).values())[-1])
        print(sentiment)
        post_id = str(uuid.uuid4())                                                             # Creates a unique id
        name = str(request.form.get("name"))
        app.logger.info(flatten(request.form))
        #app.logger.info('isanon' in dict(request.form).get('opt'))
        try:
            if ('isanon' in dict(request.form).get('opt')) == True:
                exe = """INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon)
                        VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {})""".format(sanitize(post_id),
                        sanitize(session["user_id"]),
                        sanitize(username),
                        sanitize(name),
                        sanitize(text),
                        sanitize(datetime.utcnow()),
                        sanitize(sentiment),
                        sanitize(str(request.form.get("tag"))),
                        sanitize('1'))
            elif ('ishidden' in dict(request.form).get('opt')) == True:
                exe = """INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, ishidden)
                        VALUES ({}, {}, {}, {}, {}, {}, {}, {}, {})""".format(sanitize(post_id),
                        sanitize(session["user_id"]),
                        sanitize(username),
                        sanitize(name),
                        sanitize(text),
                        sanitize(datetime.utcnow()),
                        sanitize(sentiment),
                        sanitize(str(request.form.get("tag"))),
                        sanitize('1'))
        except:
            exe = """INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag)
                    VALUES ({}, {}, {}, {}, {}, {}, {}, {})""".format(sanitize(post_id),
                    sanitize(session["user_id"]),
                    sanitize(username),
                    sanitize(name),
                    sanitize(text),
                    sanitize(datetime.utcnow()),
                    sanitize(sentiment),
                    sanitize(str(request.form.get("tag"))))
        app.logger.info(exe)
        db.execute(exe)

        conn.commit()
        return redirect(url_for("index"))

    else:
        return render_template("new_entry.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "GET":
        db = conn.cursor()
        prof_username = str(request.args.get('type'))
        # ^ username of profile being accessed

        exe = """SELECT username FROM users WHERE id={}""".format(sanitize(session["user_id"]))
        your_username = db.execute(exe).fetchall()[0][0]
        # ^ username of the user logged in rn in order to give permissions for editing profile

        exe = """SELECT title, body FROM posts WHERE user = {}""".format(sanitize(prof_username))
        app.logger.info(exe)
        posts = db.execute(exe).fetchall()

        # get user data
        exe = """SELECT * FROM users WHERE username = {}""".format(sanitize(prof_username))
        bioEx = db.execute(exe).fetchall()
        app.logger.info(bioEx)
        data = bioEx
        bio = str(bioEx[0][4])
        print(your_username, prof_username)
        return render_template("profile.html", posts=posts, bio=bio, data=data, username=prof_username, curr_username=your_username)
    elif request.method == "POST":
        # return redirect(url_for("edit"))
        pass



@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    """Allow a user to edit their bio"""
    if request.method == "GET":
        db = conn.cursor()
        exe = """SELECT bio FROM users WHERE id = {}""".format(sanitize(session["user_id"]))
        curr_bioEx = db.execute(exe).fetchall()                                                #Get users current bio
        curr_bio = str(curr_bioEx[0][0])

        conn.commit()
        return render_template("profile_edit.html", curr_bio=curr_bio)
    elif request.method == "POST":
        db = conn.cursor()
        new_bio = str(request.form.get("bio"))
        exe = "UPDATE users SET bio={} WHERE id={}".format(sanitize(new_bio), sanitize(session["user_id"]))
        db.execute(exe)                                                 #Updates bio

        conn.commit()
        return redirect(url_for("index"))

@app.route("/ban", methods=["GET", "POST"])
@login_required
@admin_only
def ban():
    """BAN A USER"""
    db = conn.cursor()
    if request.method == "POST":
        user = request.form.get("user")
        db.execute("UPDATE users SET isbanned={} WHERE username={}".format(1, sanitize(user)))
        conn.commit()
        return redirect(url_for("index"))
    else:
        return render_template("ban.html")

@app.route("/message", methods=["GET", "POST"])
@login_required
def message():
    global par_from
    global par_to
    global channel_id
    db = conn.cursor()
    if request.method == "GET":
        par_from = request.args.get("from")
        par_to = request.args.get("to")
        data = db.execute("""SELECT * FROM messages WHERE channel<>'' AND (from_={} AND to_={}) OR (from_={} AND to_={})""".format(par_from, par_to, par_from, par_to)).fetchall()              # needs to be fixed as the if part will always run
        if not data:
            channel_id = str(uuid.uuid4())
            #db.execute("""INSERT INTO messages (channel) VALUES (:channelId)""", channelId=channel_id)
            return render_template("message.html")
        else:
            channel_id = data[0]["channel"]
            messages = db.execute("""SELECT * FROM messages WHERE channel=?""", [channel_id])
            return render_template("message.html", messages=messages)
    elif request.method == "POST":
        message = request.form.get("body")
        db.execute("""INSERT INTO messages (messageID, to_, from_, body, channel, time) \
                    VALUES(:id, :to, :from_, :body, :channel, :time)""", \
                    id=str(uuid.uuid4()), \
                    to=par_to, \
                    from_=par_from, \
                    body=message, \
                    channel=channel_id, \
                    time=datetime.utcnow())
        return redirect(url_for("index"))


@app.route("/users", methods=["GET", "POST"])
@login_required
def users():
    if request.method == "GET":
        db = conn.cursor()
        users = db.execute("""SELECT * FROM users""").fetchall()
        exe = """SELECT perms FROM users WHERE id={}""".format(session["user_id"])
        perm = db.execute(exe).fetchall()[0][0]
        return render_template("users.html", users=users, perm=perm)
    elif request.method == "POST":
        pass


@app.route("/email", methods=["GET", "POST"])
@login_required
def email():
    if request.method == "POST":
        result = db.execute("INSERT INTO users (email) \
                             VALUES(:email)", \
                             email = request.form.get("email)"))
        return redirect(url_for("index"))
    else:
        return render_template("email.html")


@app.route('/delete', methods = ["GET", "POST"])
@login_required
def delete():
    # if request.method == "POST":
    #     user_data = db.execute("""SELECT * FROM users WHERE id = :id""", id=session["user_id"])
    #     username = user_data[0]["username"]

    #     file = str(request.args.get('type'))
    #     save_path = str(username)
    #     completeName = os.path.join(save_path, file + ".txt")

    #     os.remove(completeName)
    #     db.execute("""DELETE FROM entries WHERE entry={}""".format(file))
    #     return redirect(url_for("index"))
    # else:
    #     return render_template("delete.html", file=file)
    if request.method == "POST":
        user_data = db.execute("""SELECT * FROM users WHERE id = :id""", id=session["user_id"])
        username = user_data[0]["username"]

        file = str(request.form.get('f'))
        save_path = str(username)
        completeName = os.path.join(save_path, file)
        s = Path(completeName)
        if not s.is_file():
            return apology("No such file to delete.")

        os.remove(completeName)
        # db.execute("""DELETE FROM entries WHERE entry IN (SELECT entry FROM entries WHERE entry = {})""".format(str(file)))
        return redirect(url_for("index"))
    else:
        return render_template("delete.html")


@app.route('/deletem', methods = ["GET", "POST"])
@login_required
def deletem():
    if request.method == "POST":
        user_data = db.execute("""SELECT * FROM users WHERE id = :id""", id=session["user_id"])
        username = user_data[0]["username"]

        file = str(request.args.get('type'))
        save_path = str(username)
        completeName = os.path.join(save_path, file + ".txt")

        os.remove(completeName)
        db.execute("""DELETE FROM entries WHERE entry={}""".format(file))
        return redirect(url_for("index"))
    else:
        return render_template("deletem.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    """Log user in."""

    # forget any user_id
    session.clear()
    db = conn.cursor()
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology(200, "must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology(200, "must provide password")

        str = "SELECT * FROM users WHERE username = {}".format(sanitize(request.form.get("username")))
        # query database for username
        rows = db.execute(str).fetchall()
        app.logger.info(rows)
        if rows[0][8] == 1:
            return apology("fuck off you're banned bitch", 69420)
        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0][2]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0][0]
        session["username"] = rows[0][1]
        session["perms"] = rows[0][7]

        curr_id = session["user_id"]
        str = """UPDATE users SET seen={} WHERE id={}""".format(sanitize(datetime.utcnow()), sanitize(session['user_id']))
        db.execute(str)
        # redirect user to home page
        conn.commit()
        app.logger.info("ATTENTION, {}, perms {}".format(session['username'], session['perms']))
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")



@app.route("/logout")
def logout():
    """Log user out."""
    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("index"))



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        if not request.form.get("email") or not request.form.get("username") or not request.form.get("password") or request.form.get("password") != request.form.get("confirmation"):
            return apology("retry", 400)

        db = conn.cursor()
        str = "INSERT INTO users (username, hash, email, created, perms) VALUES({}, {}, {}, {}, {})".format(\
                             sanitize(request.form.get("username")), \
                             sanitize(pwd_context.hash(request.form.get("password"))), \
                             sanitize(request.form.get("email")),
                             sanitize(datetime.utcnow()),
                             sanitize("peasant"))
        # insert the new user into users, storing the hash of the user's password
        result = db.execute(str).fetchall()
        conn.commit()
        str = """SELECT id FROM users WHERE username={}""".format(sanitize(request.form.get("username")))
        result = db.execute(str).fetchall()[0]
        # remember which user has logged in
        session["user_id"] = sanitize_t(result)
        file = open("/home/8bitRebellion/tvent/tvent3.6/flask-blog/workspace/blog/log.txt", "w+")

        file.close()
        # redirect user to home page
        return redirect(url_for("index"))

    elif request.method == "GET":
        return render_template("register.html")


@app.route("/about", methods=["GET", "POST"])
@login_required
def about():
    if request.method == "GET":
        return render_template("about.html")
    elif request.method == "POST":
        return redirect(url_for("index"))

################################################################################
###       A            PPPPPPPPPP        IIIIIIIIIIIII                         #
###      A A           P         P             I                               #
###     A   A          P         P             I                               #
###    A     A         PPPPPPPPPP              I                               #
###   AAAAAAAAA        P                       I                               #
###  A         A       P                       I                               #
### A           A      P                       I                               #
###A             A     P                 IIIIIIIIIIIII                         #
################################################################################


@app.route('/api/v1/info/<user>', methods=['GET'])
def API_get_user(user):
    db = conn.cursor()
    exe = "SELECT id, username, created, seen, bio FROM users WHERE username=?"
    q = db.execute(exe, [user]).fetchall()
    if len(user) == 0:
        abort(404)
    return jsonify(q)

@app.route('/api/v1/posts/<user>', methods=['GET'])
def API_get_posts(user):
    db = conn.cursor()
    exe = "SELECT * FROM posts WHERE user=?"
    q = db.execute(exe, [user]).fetchall()
    if len(user) == 0:
        abort(404)
    return jsonify(q)


# Extra shit

