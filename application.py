# login, index, register functions ported.
# use flaskdebug_toolabr to print shit
# on 8/8/19, I got banned from yet another discord server for "being an ass"
# I guess I was
# open_post, edit, profile, new_post sql ported on 10/8/19
# still haven't fixed tuples/lists clash
# on 9/8/19, I was banned from yet another discord server for calling the owner edgy
# the owner said I had a low effort name and pfp
# I guess I do
# I got banned from windows (another server) for various reasons

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
from flask_moment import Moment
from flask_redis import Redis
from imgurpython import *
import re
import uuid
import sqlite3
import os

# configure application
app = Flask(__name__)

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = '8086'
#app.config['REDIS_URL'] = "redis://:wE3s9IaalB8z8xR15wMqi2LfNkWPIUOV@redis-11944.c16.us-east-1-2.ec2.cloud.redislabs.com:11944"
app.debug = True
Session(app)
Misaka(app)
moment = Moment(app)

#Imgur config
client = ImgurClient("51e7efef3c2b98e", "a297978f3cb883660cc729ead76f80a2634ceaa2")

conn = sqlite3.connect("/home/8bitRebellion/tvent/tvent3.6/flask-blog/workspace/blog/app.db")
analyzer = SentimentIntensityAnalyzer()
global curr_id

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if request.form['qtag']:
            db = conn.cursor()
            exe = "SELECT * FROM posts WHERE tag={}".format(sanitize(str(request.form.get("tag"))))
            app.logger.info(exe)
            posts = db.execute(exe).fetchall()
            try:
                curr_user = db.execute(("""SELECT username FROM users WHERE id=?""", [session["user_id"]])).fetchall()[0][0]
                notifs = db.execute("""SELECT * FROM notifs WHERE user_id=? AND read=?""", [session["user_id"], 0]).fetchall()
                app.logger.info(str(notifs))
                unlonely = 1 if notifs else 0
            except:
                curr_user = "anon"
                unlonely = 0
            conn.commit()
            return render_template("index.html", posts=posts, user=curr_user, unlonely=unlonely)                  # The link bypasses directly to the actual page

    elif request.method == "GET":
        db = conn.cursor()
        all_posts = db.execute("""SELECT * FROM posts WHERE ishidden != '1' OR ishidden IS NULL""").fetchall()
        app.logger.info(all_posts)
        #all_posts = db.execute("""SELECT * FROM posts""").fetchall()
        app.logger.info(all_posts)
        # data = db.execute("""SELECT * FROM entries WHERE id = :id""", id=session["user_id"])
        #notifs = db.execute("""SELECT * FROM notifs WHERE user_id=? AND read=?""", [session["user_id"], 0]).fetchall()
        #unlonely = 1 if len(notifs[0]) != 0 else 0
        if "user_id" in session:
            exe = """SELECT username FROM users WHERE id = ?"""
            curr_user = db.execute(exe, [session["user_id"]]).fetchall()[0][0]
            notifs = db.execute("""SELECT * FROM notifs WHERE user_id=? AND read=?""", [session["user_id"], 0]).fetchall()
            app.logger.info(str(notifs))
            unlonely = 1 if notifs else 0
        else:
            curr_user = 'anon'
            unlonely = 0

        if request.args.get('sort') == "new":
            return render_template("index.html", posts=list(reversed(list(all_posts))), user=curr_user, unlonely=unlonely)            #TODO FIX THIS
        elif request.args.get('sort') == "old":
            return render_template("index.html", posts=all_posts, user=curr_user, unlonely=unlonely)
        else:
            return render_template("index.html", posts=list(reversed(list(all_posts))), user=curr_user, unlonely=unlonely)




@app.route("/post", methods=["GET", "POST"])
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
        post_data = dated(post_data, 1)

        exe = """SELECT * FROM comments WHERE post_id = {}""".format(sanitize(postId))
        #app.logger.info("comments: {}".format(exe))
        comments = db.execute(exe).fetchall()
        #comments = dated(comments, 4)
        comments = deeplist(comments)
        for i in range(0, len(comments)):                                       #converts to list and changes all dates to datetime, do the same with the get request
            comments[i][4] = datetime.strptime(comments[i][4][0:-7], '%Y-%m-%d %H:%M:%S')
        sent=float(post_data[0][6])

        conn.commit()

        return render_template("open.html", post=post_data, comments=comments, curr_username = username, sent=float(post_data[0][6])) # Last argument for curruser functions such as delete and edit

    elif request.method == "POST":
        db = conn.cursor()
        app.logger.info(request.form)
        if request.form['button'] == 'postComment':         # if the users presses the comment button

            if "user_id" not in session:
                user_id = 0
                username = "anon"
            else:
                user_id = session["user_id"]
                comment_id = str(uuid.uuid4())
                exe = """SELECT * FROM users WHERE id={}""".format(sanitize(session["user_id"]))
                user_data = db.execute(exe).fetchall()
                username = user_data[0][1]
            comment_id = str(uuid.uuid4())
            cock = [comment_id,
                    user_id,
                    username,
                    request.form.get("comment"),
                    postId,
                    datetime.utcnow()]
            db.execute("""INSERT INTO comments (comment_id, user_id, username, body, post_id, time)
                    VALUES (?, ?, ?, ?, ?, ?)""", cock)

            cock = [post_data[0][0],
                    "comment",
                    post_data[0][5],
                    "Someone replyed to a post of yours",
                    postId,
                    0]
            db.execute("INSERT INTO notifs (user_id, type, username, body, link, read) VALUES (?, ?, ?, ?, ?, ?)", cock)

            exe = """SELECT comment_id, user_id, username, body, time, post_id, sentiment FROM comments WHERE post_id = {}""".format(sanitize(postId))
            comments = db.execute(exe).fetchall()
            comments = deeplist(comments)
            for i in range(0, len(comments)):                                       #converts to list and changes all dates to datetime, do the same with the get request
                comments[i][4] = datetime.strptime(comments[i][4], '%Y-%m-%d %H:%M:%S.%f')
            #comments = dated(comments, 4)                                       # fix dates
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
    db = conn.cursor()
    if request.method == "GET":
        param = request.args.get("type")
        text = db.execute("SELECT * FROM posts WHERE id=?", [param]).fetchall()[0][3]
        conn.commit()
        return render_template("editPost.html", text=text)
    elif request.method == "POST":
        db = conn.cursor()
        net = db.execute("SELECT user_id FROM POSTS WHERE id=?", [param]).fetchall()
        app.logger.info("{}, {}".format(int(sanitize_t(net[0])), session["user_id"]))
        if int(sanitize_t(net[0])) != session["user_id"]:
            return apology("You fell victim to one of the classic blunders!", 14)
        exe = """UPDATE posts SET body={} WHERE id={}""".format(sanitize(request.form.get("entry")), sanitize(param))
        db.execute(exe)
        conn.commit()
        return redirect(url_for("index"))


@app.route("/new/<sort>", methods=["GET", "POST"])
def new_entry(sort):
    """Create a new post"""
    if request.method == "POST":

        db = conn.cursor()
        if "user_id" in session:
            exe = """SELECT * FROM users WHERE id = {}""".format(sanitize(session["user_id"]))
            user_data = db.execute(exe).fetchall()
            #app.logger.info("User data: {}".format(user_data))
            username = user_data[0][1]
            user_id = session["user_id"]
        else:
            user_id = 1
            username = "anon"

        if str(sort) == "text":
            text = request.form.get("entry")
            sentiment = float(list(analyzer.polarity_scores(request.form.get("entry")).values())[-1])
            print(sentiment)
            post_id = str(uuid.uuid4())                                                             # Creates a unique id
            name = str(request.form.get("name"))
            #app.logger.info('isanon' in dict(request.form).get('opt'))
            a_files = request.files.getlist('file')
            app.logger.info(a_files)
            try:                                                            # First try block to handle no added files
                a_files = request.files.getlist('file')
                files = []                                                  # Init list to hold html for files

                if a_files:                                                 # If files have been added
                    for file in a_files:
                        filename = file.filename
                        file.save(filename)
                        image = client.upload_from_path(filename)
                        post_id = str(uuid.uuid4())
                        imghtml = str("<img src='" + str(image["link"]) + "' id='indeximg' alt='libtards I stg'>")
                        files.append(imghtml)
                        os.remove(file.filename)

                    if "!i!" in text:                                       # If user has used correct formatting to add files
                        for file in files:
                            text = text.replace("!i!", file, 1)
                    else:                                                   # else just shoehorn them to the end
                        for file in files:
                            text = str(text) + " \n" + file

            except:
                pass

            try:
                if ('isanon' in dict(request.form).get('opt')) == True and ('ishidden' in dict(request.form).get('opt2')) == True:
                    cock = [post_id,
                            user_id,
                            username,
                            name,
                            text,
                            datetime.utcnow(),
                            sentiment,
                            str(request.form.get("tag")),
                            '1',
                            '1']
                    db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)
                elif ('isanon' in dict(request.form).get('opt')) == True:
                    cock = [post_id,
                            user_id,
                            username,
                            name,
                            text,
                            datetime.utcnow(),
                            sentiment,
                            str(request.form.get("tag")),
                            '1']
                    db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)


                elif ('ishidden' in dict(request.form).get('opt2')) == True:
                    cock = [post_id,
                            user_id,
                            username,
                            name,
                            text,
                            datetime.utcnow(),
                            sentiment,
                            str(request.form.get("tag")),
                            '1']
                    db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, ishidden)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)

            except:
                cock = [post_id,
                        user_id,
                        username,
                        name,
                        text,
                        datetime.utcnow(),
                        sentiment,
                        str(request.form.get("tag")),
                        0,
                        0]
                db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)

            conn.commit()
            return redirect(url_for("index"))

        elif str(sort) == "img":
            pass
            file = request.files['file']
            app.logger.info(file)
            if file:
                filename = file.filename
                file.save(filename)
                image = client.upload_from_path(filename)
                post_id = str(uuid.uuid4())
                text = str("<img src='" + str(image["link"]) + "' id='indeximg' alt='libtards I stg'>")
                name = str(request.form.get("name"))

                cock = [post_id,
                        user_id,
                        username,
                        name,
                        text,
                        datetime.utcnow(),
                        0.0,
                        request.form.get("tag"),
                        0,
                        0]
                db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)
                os.remove(file.filename)
            else:
                pass
            conn.commit()
            return redirect(url_for("index"))
    else:
        if str(sort) == "text":
            return render_template("new_entry.html")
        elif str(sort) == "img":
            return render_template("imgpost.html")


@app.route("/profile/<user>", methods=["GET", "POST"])
@login_required
def profile(user):
    if request.method == "GET":
        db = conn.cursor()
        prof_username = str(user)
        # ^ username of profile being accessed

        exe = """SELECT username FROM users WHERE id={}""".format(sanitize(session["user_id"]))
        your_username = db.execute(exe).fetchall()[0][0]
        # ^ username of the user logged in rn in order to give permissions for editing profile

        exe = """SELECT * FROM posts WHERE user = {}""".format(sanitize(prof_username))
        app.logger.info(exe)
        posts = db.execute(exe).fetchall()

        # get user data
        exe = """SELECT * FROM users WHERE username = {}""".format(sanitize(prof_username))
        bioEx = db.execute(exe).fetchall()
        app.logger.info(bioEx)
        bioEx = dated(bioEx, 5)
        try:
            bioEx = dated(bioEx, 6)
        except:
            pass
        data = bioEx
        bio = str(bioEx[0][4])
        print(your_username, prof_username)
        return render_template("profile.html", posts=posts, bio=bio, data=data, username=prof_username, curr_username=your_username)
    elif request.method == "POST":
        # return redirect(url_for("edit"))
        pass


@app.route("/prefs", methods=["GET", "POST"])
@login_required
def prefs():
    db = conn.cursor()
    if request.method == "GET":
        info = db.execute("""SELECT * FROM users WHERE id=?""", [session["user_id"]]).fetchall()
        return render_template("prefs.html", info=info)
    elif request.method == "POST":
        if request.form["delete"]:
            db.execute("""DELETE FROM users WHERE id=?""", [session["user_id"]])
            return redirect(url_for('index'))

        elif request.form["cpassword"]:
            opassword = pwd_context.hash(request.form.get("opassword"))
            npassword = pwd_context.hash(request.form.get("npassword"))

            if db.execute("SELECT hash FROM users WHERE id=?", [session["user_id"]]).fetchall()[0][0] == opassword:
                db.execute("UPDATE users SET hash=? WHERE id=?", [npassword])
                conn.commit()
                return redirect(url_for("prefs"))
            else:
                return apology("Enter your old password libtard", 80085)




@app.route("/notifs", methods=["GET", "POST"])
@login_required
def notifs():
    """Manage a user's notifications"""
    db = conn.cursor()
    if request.method == "GET":
        user = str(request.args.get("user"))
        notifs = db.execute("SELECT * FROM notifs WHERE username=? AND read=0", [user]).fetchall()
        return render_template("notifs.html", notifs=notifs)
    elif request.method == "POST":
        pass



@app.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    """Them fags be chatting"""
    db = conn.cursor()
    global channel
    if request.method == "GET":
        exe = "SELECT * FROM chats WHERE to=? AND from=?"
        to = str(request.args.get("user"))
        from_ = session["user_id"]
        q = db.execute(exe, [request.args.get("user"), session["user_id"]]).fetchall()
        if not q:
            channel = str(uuid.uuid4())
            exe = "INSERT INTO chats (channel, to, from) VALUES (?)"
            db.execute(exe, [channel, request.args.get("user"), session["user_id"]])
        else:
            channel = str(q[0][0])
        return render_template("chat.html", channel=channel, to=to, from_=from_)




@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    """Allow a user to edit their bio"""
    if request.method == "GET":
        db = conn.cursor()
        exe = """SELECT bio, pfp FROM users WHERE id = {}""".format(sanitize(session["user_id"]))
        curr_bioEx = db.execute(exe).fetchall()                                                #Get users current bio
        curr_bio = str(curr_bioEx[0][0])
        pfp = str(curr_bioEx[0][1])

        conn.commit()
        return render_template("profile_edit.html", curr_bio=curr_bio, pfp=pfp)
    elif request.method == "POST":
        db = conn.cursor()
        new_bio = str(request.form.get("bio"))
        try:
            file = request.files['file']
            if file:
                filename = file.filename
                file.save(filename)
                image = client.upload_from_path(filename)

            db.execute("UPDATE users SET bio=?, pfp=? WHERE id=?", [new_bio, image["link"], session["user_id"]])
        except:
            db.execute("UPDATE users SET bio=? WHERE id=?", [new_bio, session["user_id"]])

        conn.commit()
        return redirect(url_for("index"))

@app.route("/bulk", methods=["GET", "POST"])
@admin_only
def bulk():
    db = conn.cursor()
    if request.method == "GET":
        posts = db.execute("SELECT * FROM posts").fetchall()
        return render_template("bulk.html", posts=posts)
    if request.method == "POST":
        app.logger.info(dict(request.form).get('opt'))
        for post in dict(request.form).get('opt'):
            db.execute("DELETE FROM posts WHERE id=?", [post])
            conn.commit()
        return redirect(url_for("admin"))


@app.route("/sql", methods=["GET", "POST"])
@admin_only
def sql():
    db = conn.cursor()
    if request.method == "GET":
        return render_template("sql.html")
    else:
        q = db.execute(request.form.get("sql"))
        if "SELECT" in request.form.get("sql"):
            message = db.execute(request.form.get("sql")).fetchall()
        else:
            message = db.execute(sanitize(sql))
        return render_template("results.html", message=message)


@app.route("/admin", methods=["GET", "POST"])
@admin_only
def admin():
    if request.method == "GET":
        return render_template("admin.html")

@app.route("/ban", methods=["GET", "POST"])
@login_required
@admin_only
def ban():
    """Ban a user"""
    db = conn.cursor()
    if request.method == "POST":
        user = request.form.get("user")
        db.execute("UPDATE users SET isbanned={} WHERE username={}".format(1, sanitize(user)))
        conn.commit()
        return redirect(url_for("index"))
    else:
        return render_template("ban.html")

@app.route("/kill", methods=["GET", "POST"])
@login_required
@admin_only
def kill():
    """Delete an account"""
    db = conn.cursor()
    if request.method == "POST":
        user = request.form.get("user")
        db.execute("DELETE FROM users WHERE username={}".format(sanitize(user)))
        conn.commit()
        return redirect(url_for("index"))
    else:
        return render_template("delete.html")

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
            return apology("enter the username you absolute cement-head", 200)

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("enter the password retard", 200)

        str = "SELECT * FROM users WHERE username = {}".format(sanitize(request.form.get("username")))
        # query database for username
        rows = db.execute(str).fetchall()
        app.logger.info(rows)
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0][2]):
            return apology("wrong username or password probs", 80085)
        if rows[0][8] == 1:
            return apology("fuck off you're banned bitch", 69420)


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
    db = conn.cursor()
    str = """UPDATE users SET seen={} WHERE id={}""".format(sanitize(datetime.utcnow()), sanitize(session['user_id']))
    db.execute(str)
    conn.commit()
    session.clear()

    # redirect user to login form
    return redirect(url_for("index"))



@app.route("/register", methods=["GET", "POST"])
def register():
    db = conn.cursor()
    if request.method == "POST":
        if not request.form.get("email") or not request.form.get("username") or not request.form.get("password") or request.form.get("password") != request.form.get("confirmation"):
            return apology("retry", 400)
        if len(db.execute("SELECT * FROM users WHERE username = ? LIMIT '1'", [request.form.get("username")]).fetchall()) > 0:
            return apology("username taken bitch", 696969)
        try:
            welcome(request.form.get("email"), "hoe")
        except:
            return apology("Enter an actual email address ya hoe", 69)

        str = "INSERT INTO users (username, hash, email, created, perms, isbanned) VALUES({}, {}, {}, {}, {}, {})".format(\
                             sanitize(request.form.get("username")), \
                             sanitize(pwd_context.hash(request.form.get("password"))), \
                             sanitize(request.form.get("email")),
                             sanitize(datetime.utcnow()),
                             sanitize("peasant"),
                             sanitize("0"))
        # insert the new user into users, storing the hash of the user's password
        result = db.execute(str).fetchall()
        conn.commit()
        str = """SELECT id FROM users WHERE username={}""".format(sanitize(request.form.get("username")))
        result = db.execute(str).fetchall()[0]
        # remember which user has logged in
        session["user_id"] = sanitize_t(result)
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


@app.route("/history", methods=["GET"])
@login_required
def history():
    if request.method == "GET":
        return render_template("history.html")

################################################################################
###W      W      W   IIIIIIIIIIIII    K   KKKK    IIIIIIIIIIIIIII              #
### W     W     W          I          K  K              I                      #
###  W    W    W           I          K K               I                      #
###   W   W   W            I          KK                I                      #
###    W  W  W             I          K K               I                      #
###     W W W              I          K  K              I                      #
###      WWW         IIIIIIIIIIIII    K   KKKK    IIIIIIIIIIIIIII              #
################################################################################

@app.route("/wiki/<folder>", methods=["GET", "POST"])
@login_required
@admin_only
def wiki(folder):
    db = conn.cursor()
    global folder2
    if request.method == "GET":
        folder2 = folder

        selfinfo = db.execute("SELECT * FROM wiki WHERE selfid=?", [str(folder)]).fetchall()
        childinfo = db.execute("SELECT * FROM wiki WHERE parentid=?", [str(folder)]).fetchall()

        if selfinfo[0][3] == "folder":
            #config1 = db.execute("SELECT * FROM wiki WHERE type=? AND parentid=?", ["config", str(folder)]).fetchall()
            #if not config1:
                #config = db.execute("SELECT body FROM wiki WHERE name=?", ["default"]).fetchall()[0][5]
            #else:
                #config = config1[0][5]

            return render_template("wiki.html", childinfo=childinfo, selfinfo=selfinfo)
        elif selfinfo[0][3] == "file":
            return render_template("wfile.html", selfinfo=selfinfo)


    else:
        if request.form.get("add"):
            if request.form["type"] == "folder":
                cock = [str(uuid.uuid4()),
                        folder2,
                        request.form.get("name"),
                        "folder",
                        datetime.utcnow(),
                        ""]
                db.execute("INSERT INTO wiki (selfid, parentid, name, type, time, body) VALUES (?, ?, ?, ?, ?, ?)", cock)
                conn.commit()
                return redirect(url_for("wiki", folder=folder2))
            elif request.form["type"] == "file":
                cock = [str(uuid.uuid4()),
                        folder2,
                        request.form.get("name"),
                        "file",
                        datetime.utcnow(),
                        ""]
                db.execute("INSERT INTO wiki (selfid, parentid, name, type, time, body) VALUES (?, ?, ?, ?, ?, ?)", cock)
                conn.commit()
                return redirect(url_for("wiki", folder=folder2))
        elif request.form.get("edit"):
            #bypass to the route via link in html
            pass
        elif request.form.get("delete"):
            db.execute("DELETE FROM wiki WHERE selfid=? OR parentid=?", [request.form["delete"], request.form["delete"]])
            conn.commit()
            return redirect(url_for("wiki", folder="self"))


@app.route("/editWiki", methods=["GET", "POST"])
@admin_only
@login_required
def editWiki():
    global wizofid
    db = conn.cursor()
    if request.method == "GET":
        wizofid = request.args.get("type")
        body = db.execute("SELECT body FROM wiki WHERE selfid=?", [wizofid]).fetchall()[0][0]
        return render_template("editWiki.html", body=body)
    else:
        bod = request.form.get("entry")
        db.execute("""UPDATE wiki SET body=? WHERE selfid=?""", [bod, wizofid])
        conn.commit()
        return redirect(url_for("wiki", folder="self"))



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


# Users
@app.route('/api/v1/<user>/info', methods=['GET'])
def API_get_user(user):
    db = conn.cursor()
    exe = "SELECT id, username, created, seen, bio FROM users WHERE username=?"
    q = db.execute(exe, [user]).fetchall()
    if len(user) == 0:
        abort(404)
    return jsonify(q)

@app.route('/api/v1/<user>/posts', methods=['GET'])
def API_get_posts(user):
    db = conn.cursor()
    exe = "SELECT * FROM posts WHERE user=?"
    q = db.execute(exe, [user]).fetchall()
    if len(user) == 0:
        abort(404)
    return jsonify(q)

# Posts
@app.route('/api/v1/<post>/info', methods=['GET'])
def API_get_pinfo(user):
    db = conn.cursor()
    exe = "SELECT * FROM posts WHERE post=?"
    q = db.execute(exe, [post]).fetchall()
    if len(post) == 0:
        abort(404)
    return jsonify(q)

@app.route('/api/v1/<post>/comments', methods=['GET'])
def API_get_pcomments(user):
    db = conn.cursor()
    exe = "SELECT * FROM comments WHERE post_id=?"
    q = db.execute(exe, [post]).fetchall()
    if len(post) == 0:
        abort(404)
    return jsonify(q)

# Comments
@app.route('/api/v1/<comment>/info', methods=['GET'])
def API_get_cinfo(user):
    db = conn.cursor()
    exe = "SELECT * FROM comments WHERE comment_id=?"
    q = db.execute(exe, [comment]).fetchall()
    if len(comment) == 0:
        abort(404)
    return jsonify(q)

@app.route('/api/chat/messages/<channel>', methods=['GET'])
def API_get_messages(channel):
    db = conn.cursor()
    exe = "SELECT * FROM chats WHERE channel=?"
    q = db.execute(exe, [channel]).fetchall()
    app.logger.info(db.execute("SELECT * FROM chats").fetchall())
    if not q:
        app.logger.info("lower")
        channel = str(uuid.uuid4())
        exe = "INSERT INTO chats (channel) VALUES (?)"
        db.execute(exe, [channel])
    conn.commit()

    return jsonify(q)

@app.route('/api/chat/messages/add', methods=["POST"])
def API_chat_add():
    #channel, to, from, body
    db = conn.cursor()
    try:
        channel = request.args.get("channel")
        to = request.args.get("to")
        from_ = request.args.get("from")
        body = request.args.get("body")
        exe = "INSERT INTO chats (channel, to, from, body) VALUES (?, ?, ?, ?)"

        db.execute(exe, [channel, to, from_, body])
        conn.commit()
    except:
        abort(404)


