import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
# from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import CSRFProtectForm, UserAddForm, LoginForm, MessageForm, UpdateUserForm
from models import db, connect_db, User, Message

# import pdb

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ['DATABASE_URL'].replace("postgres://", "postgresql://"))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
#toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


@app.before_request
def add_form_to_g():
    """ add CSRFProtectionForm to Flask global """
    g.CSRF_form = CSRFProtectForm()


def do_login(user):
    """Log in user."""
    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""
    if CURR_USER_KEY in session:
        session.pop(CURR_USER_KEY)


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    # IMPLEMENT THIS AND FIX BUG
    # DO NOT CHANGE METHOD ON ROUTE
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        do_logout()
        flash(f"User is logged out", "info")
        return redirect("/login")

    # redirect if either if's dont pass
    # ask is the line below necessary
    return redirect("/")


##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.ilike(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user)


@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    return render_template('users/following.html', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        followed_user = User.query.get_or_404(follow_id)
        g.user.following.append(followed_user)
        db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        followed_user = User.query.get(follow_id)
        g.user.following.remove(followed_user)
        db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/<int:user_id>/edit', methods=["GET", "POST"])
def profile(user_id):
    """Update profile for current user."""

    if not g.user and user_id == g.user.id:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = g.user
    form = UpdateUserForm(obj=user)

    if form.validate_on_submit():

        user_auth = User.authenticate(
            user.username,
            form.password.data)

        if user_auth:
            user.username = form.username.data
            user.email = form.email.data
            user.image_url = form.image_url.data
            user.header_image_url = form.header_image_url.data
            user.bio = form.bio.data

            db.session.commit()

            flash(f"Hello, {user.username}!", "success")
            return redirect(f"/users/{user.id}")

        else:
            flash("Invalid credentials.", 'danger')

    return render_template('users/edit.html', form=form, user=user)


@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        do_logout()

        db.session.delete(g.user)
        db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages')
def show_all_messages():
    """Show all messages."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = g.user
    messages = Message.query.order_by(Message.timestamp.desc()).limit(100).all()
    return render_template('discover.html', messages=messages, user=user)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        msg = Message.query.get_or_404(message_id)
        db.session.delete(msg)
        db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Adding and removing likes to messages


@app.post("/messages/<int:message_id>/add-like")
def add_like_to_message(message_id):
    """adds like to message on homepage"""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        liked_message = Message.query.get_or_404(message_id)

        g.user.liked_messages.append(liked_message)
        db.session.commit()

    return redirect('/')


@app.post("/messages/<int:message_id>/remove-like")
def removes_like_from_message(message_id):
    """removes a like from message redirects to homepage"""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        liked_message = Message.query.get_or_404(message_id)
        g.user.liked_messages.remove(liked_message)
        db.session.commit()

    return redirect('/')


#  adding & removing likes from profile page
@app.post("/messages/<int:message_id>/add-like-from-<int:user_id>")
def add_like_to_message_on_user_profile(message_id, user_id):
    """adds like to message on homepage"""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    if g.CSRF_form.validate_on_submit():
        liked_message = Message.query.get_or_404(message_id)

        g.user.liked_messages.append(liked_message)
        db.session.commit()

    return redirect(f'/users/{user_id}')


@app.post("/messages/<int:message_id>/remove-like-from-<int:user_id>")
def removes_like_from_message_on_user_profile(message_id, user_id):
    """removes a like from message redirects to homepage"""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")
    if g.CSRF_form.validate_on_submit():
        liked_message = Message.query.get_or_404(message_id)

        g.user.liked_messages.remove(liked_message)
        db.session.commit()

    return redirect(f'/users/{user_id}')


@app.get("/users/<int:user_id>/liked-messages")
def show_liked_messages(user_id):
    """displays the visited users liked messages on liked-messages.html page"""
    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    user_liked_messages = user.liked_messages

    return render_template("users/liked-messages.html", user_liked_messages=user_liked_messages)


# go to back where user came from after they like a message
# hidden input field to form, pass location to form *idea*

##############################################################################
# Homepage and error pages

@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """
    if g.user:

        ids = [f.id for f in g.user.following]
        ids.append(g.user.id)

        user = g.user
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(ids))
                    .order_by(Message.timestamp.desc())
                    .limit(100).all())

        #messages = Message.query.all()
        return render_template('home.html', messages=messages, user=user)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
