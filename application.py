# Add prefs
# Add domains for posts
# Check stats+admin routes and complete html

from flask import *
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from helpers import *
from pathlib import Path
from cryptography.fernet import Fernet
from datetime import *
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

# further app config
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = '8086'
app.debug = True
Session(app)
Misaka(app)
moment = Moment(app)

# globals
client = ImgurClient("51e7efef3c2b98e", "a297978f3cb883660cc729ead76f80a2634ceaa2")
conn = sqlite3.connect("/home/8bitRebellion/tvent/tvent3.6/flask-blog/workspace/blog/app.db")
analyzer = SentimentIntensityAnalyzer()
global curr_id

@app.route("/", methods=["GET", "POST"])
def index():
    db = conn.cursor()
    global banner
    try:
        banner = db.execute("SELECT value FROM stats WHERE thing='banner'").fetchall()[0][0]
    except:
        banner = ''
    if request.method == "POST":
        if request.form['qtag']:
            exe = "SELECT * FROM posts WHERE tag={}".format(sanitize(str(request.form.get("tag"))))

            try:
                exe = """SELECT * FROM users WHERE id = ?"""
                user_info = db.execute(exe, [session["user_id"]]).fetchall()
                if user_info[0][7] == "peasant":                                                                        # Show public posts only if user is a pleb
                    posts = db.execute("""SELECT * FROM posts WHERE domain=? AND tag=? AND (ishidden != '1' OR ishidden IS NULL)""", ["public", request.form.get("tag")]).fetchall()             # ALSO FIX THIS
                elif user_info[0][7] == "admin":
                    posts = db.execute("""SELECT * FROM posts WHERE tag=?""", [request.form.get("tag")]).fetchall()

                curr_user = db.execute("""SELECT username FROM users WHERE id=?""", [session["user_id"]]).fetchall()[0][0]
                notifs = db.execute("""SELECT * FROM notifs WHERE user_id=? AND read=?""", [session["user_id"], 0]).fetchall()

                unlonely = 1 if notifs else 0


            except:
                posts = db.execute("""SELECT * FROM posts WHERE domain=? AND tag=? AND (ishidden != '1' OR ishidden IS NULL)""", ["public", request.form.get("tag")]).fetchall()
                curr_user = "anon"
                unlonely = 0


            conn.commit()
            return render_template("index.html", posts=posts, user=curr_user,                   # The link bypasses directly to the actual page
            unlonely=unlonely, banner=banner)

    elif request.method == "GET":
        app.logger.info(request.headers['X-Real-IP'])
        if "user_id" in session:
            exe = """SELECT * FROM users WHERE id = ?"""
            user_info = db.execute(exe, [session["user_id"]]).fetchall()
            curr_user = user_info[0][1]
            notifs = db.execute("""SELECT * FROM notifs WHERE user_id=? AND read=?""", [session["user_id"], 0]).fetchall()
            unlonely = 1 if notifs else 0

            last_ip = str(request.headers['X-Real-IP'])
            db.execute("UPDATE users SET ip=? WHERE id=?", [last_ip, session["user_id"]])

            if user_info[0][7] == "peasant":                                                                        # Show public posts only if user is a pleb
                all_posts = db.execute("""SELECT * FROM posts WHERE domain=? AND ishidden != '1' OR ishidden IS NULL""", ["public"]).fetchall()             # ALSO FIX THIS
            elif user_info[0][7] == "admin":
                all_posts = db.execute("""SELECT * FROM posts""").fetchall()

        else:
            all_posts = db.execute("""SELECT * FROM posts WHERE domain=? AND ishidden != '1' OR ishidden IS NULL""", ["public"]).fetchall()           # ACTUALLY FIX THIS
            curr_user = 'anon'
            unlonely = 0

        conn.commit()

        if request.args.get('sort') == "new":
            return render_template("index.html",
            posts=list(reversed(list(all_posts))), user=curr_user,
            unlonely=unlonely, banner=banner)            #TODO FIX THIS
        elif request.args.get('sort') == "old":
            return render_template("index.html", posts=all_posts,
            user=curr_user, unlonely=unlonely, banner=banner)
        else:
            return render_template("index.html",
            posts=list(reversed(list(all_posts))), user=curr_user,
            unlonely=unlonely, banner=banner)

######## #### ##       ########    ####  #######
##        ##  ##       ##           ##  ##     ##
##        ##  ##       ##           ##  ##     ##
######    ##  ##       ######       ##  ##     ##
##        ##  ##       ##           ##  ##     ##
##        ##  ##       ##           ##  ##     ##
##       #### ######## ########    ####  #######


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
                    str(username + " replyed to your post '" + post_data[0][2] + "'"),
                    postId,
                    0,
                    str(uuid.uuid4())]
            db.execute("INSERT INTO notifs (user_id, type, username, body, link, read, id) VALUES (?, ?, ?, ?, ?, ?, ?)", cock)

            exe = """SELECT comment_id, user_id, username, body, time, post_id, sentiment FROM comments WHERE post_id = {}""".format(sanitize(postId))
            comments = db.execute(exe).fetchall()
            comments = deeplist(comments)
            for i in range(0, len(comments)):                                       #converts to list and changes all dates to datetime, do the same with the get request
                comments[i][4] = datetime.strptime(comments[i][4], '%Y-%m-%d %H:%M:%S.%f')
            #comments = dated(comments, 4)                                       # fix dates

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
    global postid
    db = conn.cursor()
    if request.method == "GET":
        postid = request.args.get("type")
        text = db.execute("SELECT * FROM posts WHERE id=?", [postid]).fetchall()
        conn.commit()
        return render_template("editPost.html", text=text)
    elif request.method == "POST":
        db = conn.cursor()
        net = db.execute("SELECT user_id FROM POSTS WHERE id=?", [postid]).fetchall()
        if int(sanitize_t(net[0])) != session["user_id"]:
            return apology("Oh fuck off", 14)
        db.execute("""UPDATE posts SET body=?, title=? WHERE id=?""", [request.form.get("entry"), request.form.get("title"), postid])
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
            text = str(request.form.get("entry"))
            sentiment = float(list(analyzer.polarity_scores(request.form.get("entry")).values())[-1])
            print(sentiment)
            post_id = str(uuid.uuid4())                                                             # Creates a unique id
            name = str(request.form.get("name"))
            #app.logger.info('isanon' in dict(request.form).get('opt'))
            a_files = request.files.getlist('file')

            try:                                                            # First try block to handle no added files
                a_files = request.files.getlist('file')
                files = []                                                  # Init list to hold html for files

                if a_files:                                                 # If files have been added
                    for file in a_files:                                    # Upload each file to imgur
                        filename = file.filename
                        file.save(filename)
                        image = client.upload_from_path(filename)
                        post_id = str(uuid.uuid4())
                        imghtml = str("<img src='" + str(image["link"]) + "' id='indeximg' alt='libtards I stg'>")
                        files.append(imghtml)                               # add html for file to list
                        os.remove(file.filename)

                    if "!i!" in text:                                       # If user has used correct formatting to add files
                        for file in files:
                            text = text.replace("!i!", file, 1)
                    else:                                                   # else just shoehorn them to the end
                        for file in files:
                            text = str(text) + " \n" + file

            except:
                pass

            app.logger.info(request.form.getlist("opt"))
            app.logger.info(dict(request.form))

            try:
                if ('isanon' in dict(request.form).get('opt')) == True and ('ishidden' in dict(request.form).get('opt')) == True:
                    cock = [post_id,
                            user_id,
                            username,
                            name,
                            text,
                            datetime.utcnow(),
                            sentiment,
                            str(request.form.get("tag")),
                            '1',
                            '1',
                            'public']
                    db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden, domain)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)
                elif ('isanon' in dict(request.form).get('opt')) == True:
                    cock = [post_id,
                            user_id,
                            username,
                            name,
                            text,
                            datetime.utcnow(),
                            sentiment,
                            str(request.form.get("tag")),
                            '1',
                            '0',
                            'public']
                    db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden, domain)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)


                elif ('ishidden' in dict(request.form).get('opt')) == True:
                    cock = [post_id,
                            user_id,
                            username,
                            name,
                            text,
                            datetime.utcnow(),
                            sentiment,
                            str(request.form.get("tag")),
                            '1',
                            '0',
                            'public']
                    db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, ishidden, isanon, domain)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)

                elif ('isprivate' in dict(request.form).get('opt')) == True:
                    cock = [post_id,
                            user_id,
                            username,
                            name,
                            text,
                            datetime.utcnow(),
                            sentiment,
                            str(request.form.get("tag")),
                            '0',
                            '0',
                            'private']
                    db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden, domain)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)

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
                        0,
                        "public"]
                db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden, domain)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)

            conn.commit()
            return redirect(url_for("index"))

        elif str(sort) == "img":
            pass
            file = request.files['file']

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
                        0,
                        "public"]
                db.execute("""INSERT INTO posts (id, user_id, user, title, body, time, sentiment, tag, isanon, ishidden, domain)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", cock)
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


##     ##  ######  ######## ########           ######  #### ########  ########
##     ## ##    ## ##       ##     ##         ##    ##  ##  ##     ## ##
##     ## ##       ##       ##     ##         ##        ##  ##     ## ##
##     ##  ######  ######   ########  #######  ######   ##  ##     ## ######
##     ##       ## ##       ##   ##                 ##  ##  ##     ## ##
##     ## ##    ## ##       ##    ##          ##    ##  ##  ##     ## ##
 #######   ######  ######## ##     ##          ######  #### ########  ########

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

        # Get user posts and post count
        posts = db.execute("""SELECT * FROM posts WHERE user = ?""", [prof_username]).fetchall()
        count = len(posts)
        posts = db.execute("""SELECT * FROM posts WHERE user = ? AND domain = 'public'""", [prof_username]).fetchall()

        # get user data
        bioEx = db.execute("""SELECT * FROM users WHERE username = ?""", [prof_username]).fetchall()
        app.logger.info(bioEx)
        bioEx = dated(bioEx, 5)
        try:
            bioEx = dated(bioEx, 6)
        except:
            pass
        data = bioEx
        bio = str(bioEx[0][4])

        return render_template("profile.html", posts=posts, bio=bio, data=data,
        username=prof_username, curr_username=your_username, count=count)

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
        if request.form["button"] == "delete":
            db.execute("""DELETE FROM users WHERE id=?""", [session["user_id"]])
            session.clear()
            return redirect(url_for('register'))
            conn.commit()

        elif request.form["button"] == "cpassword":
            opassword = pwd_context.hash(request.form.get("opassword"))
            npassword = pwd_context.hash(request.form.get("npassword"))

            app.logger.info(db.execute("SELECT hash FROM users WHERE id=?", [session["user_id"]]).fetchall())
            app.logger.info(db.execute("SELECT hash FROM users WHERE id=?", [session["user_id"]]).fetchall()[0][0])
            if pwd_context.verify(opassword, db.execute("SELECT hash FROM users WHERE id=?", [session["user_id"]]).fetchall()[0][0]):
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
        notifs = db.execute("SELECT * FROM notifs WHERE username=? AND read=0", [session["username"]]).fetchall()
        return render_template("notifs.html", notifs=notifs)
    elif request.method == "POST":
        app.logger.info(dict(request.form).get('opt'))
        app.logger.info(request.form)
        for read in dict(request.form).get('opt'):
            db.execute("DELETE FROM notifs WHERE id=?", [read])
            conn.commit()
        return redirect(url_for("index"))



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

 ######  ##     ##    ###    ########
##    ## ##     ##   ## ##      ##
##       ##     ##  ##   ##     ##
##       ######### ##     ##    ##
##       ##     ## #########    ##
##    ## ##     ## ##     ##    ##
 ######  ##     ## ##     ##    ##

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


@app.route("/message", methods=["GET", "POST"])
@login_required
def message():
    global par_from
    global par_to
    global channel_id
    global from_id
    global to_id
    db = conn.cursor()
    if request.method == "GET":
        par_from = request.args.get("from")
        par_to = request.args.get("to")
        from_id = db.execute("SELECT id FROM users WHERE username=?", [par_from]).fetchall()[0][0]
        to_id = db.execute("SELECT id FROM users WHERE username=?", [par_to]).fetchall()[0][0]

        app.logger.info(str("from_id:" + str(from_id) + "user id:" + str(session["user_id"])))
        if session["user_id"] != from_id:
            return apology("fuck off", 8008135)

        data = db.execute("""SELECT * FROM messages WHERE channel<>'' AND ((from_=? AND to_=?) OR (from_=? AND to_=?))""", [par_from, par_to, par_from, par_to]).fetchall()              # needs to be fixed as the if part will always run
        if not data:
            channel_id = str(uuid.uuid4())

            db.execute("""INSERT INTO messages (channel) VALUES (?)""", [channel_id])
            conn.commit()

            return render_template("message.html")
        else:
            channel_id = data[0][2]
            messages = db.execute("""SELECT * FROM messages WHERE channel=?""", [channel_id]).fetchall()
            conn.commit()

            messages = dated(messages, 5)
            return render_template("message.html", messages=reversed(messages))
    elif request.method == "POST":
        message = str(request.form.get("body"))
        db.execute("""INSERT INTO messages (messageID, to_, from_, body, channel, time) \
                    VALUES(?, ?, ?, ?, ?, ?)""",
                    [str(uuid.uuid4()),
                    par_to,
                    par_from,
                    message,
                    channel_id,
                    datetime.utcnow()])

        dump = db.execute("""SELECT messages FROM users WHERE id=?""", [from_id]).fetchall()[0][0]
        dump = dump.split(",")
        dump.remove(from_id)
        dump = ','.join(dump)
        dump += str(',' + str(to_id))
        db.execute("""UPDATE users SET messages=? WHERE id=?""", [dump, from_id])

        conn.commit()
        return redirect(url_for("index"))



   ###    ########  ##     ## #### ##    ##
  ## ##   ##     ## ###   ###  ##  ###   ##
 ##   ##  ##     ## #### ####  ##  ####  ##
##     ## ##     ## ## ### ##  ##  ## ## ##
######### ##     ## ##     ##  ##  ##  ####
##     ## ##     ## ##     ##  ##  ##   ###
##     ## ########  ##     ## #### ##    ##


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
    db = conn.cursor()
    if request.method == "GET":
        return render_template("admin.html")
    if request.method == "POST":
        if request.form["setbanr"]:
            banner = request.form.get("banner")
            yah = db.execute("SELECT * FROM stats WHERE thing='banner'").fetchall()
            if len(yah) == 0:
                db.execute("INSERT INTO stats (thing, value) VALUES ('banner', ?)",
                [banner])
                conn.commit()
            else:
                db.execute("UPDATE stats SET value=? WHERE thing='banner'",
                [banner])
                conn.commit()
            return redirect(url_for("index"))
        elif request.form["hplus"]:
            needtoshit = request.form.get("house")
            yah = db.execute("SELECT * FROM stats WHERE thing='movedHouse'").fetchall()
            if len(yah) == 0:
                db.execute("INSERT INTO stats (thing, value) VALUES ('movedHouse', ?)",
                [needtoshit])
                conn.commit()
            else:
                db.execute("UPDATE stats SET value=? WHERE thing='movedHouse'",
                [needtoshit])
                conn.commit()
            return redirect(url_for("index"))
        elif request.form["splus"]:
            ppboom = request.form.get("school")
            yah = db.execute("SELECT * FROM stats WHERE thing='changedSchool'").fetchall()
            if len(yah) == 0:
                db.execute("INSERT INTO stats (thing, value) VALUES ('changedSchool', ?)",
                [ppboom])
                conn.commit()
            else:
                db.execute("UPDATE stats SET value=? WHERE thing='changedSchool'",
                [ppboom])
                conn.commit()
            return redirect(url_for("index"))



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



#### ##    ## ########  #######
 ##  ###   ## ##       ##     ##
 ##  ####  ## ##       ##     ##
 ##  ## ## ## ######   ##     ##
 ##  ##  #### ##       ##     ##
 ##  ##   ### ##       ##     ##
#### ##    ## ##        #######


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

@app.route("/stats", methods=["GET", "POST"])
def stats():
    thyAss = conn.cursor()
    if request.method == "GET":
        # post count
        posts = thyAss.execute("SELECT * FROM posts").fetchall()
        posts = len(posts)

        # wiki entries
        wiki = thyAss.execute("SELECT * FROM wiki").fetchall()
        wiki = len(wiki)

        # total subs
        comms = thyAss.execute("SELECT * FROM comments").fetchall()
        comms = len(comms)
        tot = comms + wiki + posts

        # user count
        users = thyAss.execute("SELECT * FROM users").fetchall()
        users = len(users)

        # project start date
        manifest = date(2018, 11, 5)
        today = datetime.now().date()
        delta = today - manifest
        passed = str(delta.days)

        # number of times I've changed house because of course my fam can't
        # stay in the same place
        hchange = thyAss.execute("SELECT value FROM stats WHERE thing=?",
        ['movedHouse']).fetchall()

        # number of times I've changed school because why the fuck not
        schange = thyAss.execute("SELECT value FROM stats WHERE thing=?",
        ['changedSchool']).fetchall()

        return render_template("stats.html", posts=posts, wiki=wiki, tot=tot,
        users=users, passed=passed, house=hchange, school=schange)

    else:
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

########     ###     ######  ####  ######
##     ##   ## ##   ##    ##  ##  ##    ##
##     ##  ##   ##  ##        ##  ##
########  ##     ##  ######   ##  ##
##     ## #########       ##  ##  ##
##     ## ##     ## ##    ##  ##  ##    ##
########  ##     ##  ######  ####  ######

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

        welcome(request.form.get("email"), "hoe")
        #except:
            #return apology("Enter an actual email address ya hoe", 69)

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



##      ## #### ##    ## ####
##  ##  ##  ##  ##   ##   ##
##  ##  ##  ##  ##  ##    ##
##  ##  ##  ##  #####     ##
##  ##  ##  ##  ##  ##    ##
##  ##  ##  ##  ##   ##   ##
 ###  ###  #### ##    ## ####

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



 ######  ##       #### ########   ######
##    ## ##        ##  ##     ## ##    ##
##       ##        ##  ##     ## ##
##       ##        ##  ########   ######
##       ##        ##  ##              ##
##    ## ##        ##  ##        ##    ##
 ######  ######## #### ##         ######

@app.route('/clips/<func>', methods=["GET", "POST"])
def clips(func):
    db = conn.cursor()
    if request.method == "GET":
        if str(func) == "yours":
            clips = db.execute("SELECT * FROM clips WHERE userid=?", [session["user_id"]]).fetchall()
            return render_template("clips.html", clips=clips)
    elif request.method == "POST":
        if request.form.get("add"):
            text = request.form.get("text")
            db.execute("INSERT INTO clips (id, userid, body) VALUES (?, ?, ?)", [str(uuid.uuid4()), session["user_id"], text])
            conn.commit()
            return redirect(url_for("clips", func="yours"))
        elif request.form.get("delete"):
            db.execute("DELETE FROM clips WHERE id=?", [request.form["delete"]])
            conn.commit()
            return redirect(url_for("clips", func="yours"))


   ###    ########  ####
  ## ##   ##     ##  ##
 ##   ##  ##     ##  ##
##     ## ########   ##
######### ##         ##
##     ## ##         ##
##     ## ##        ####


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

