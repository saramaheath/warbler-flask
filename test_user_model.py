"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from tokenize import String
from unittest import TestCase

from models import db, User, Message, Follows


# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):

    def setUp(self):
        # deletes all the user instances
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

        self.client = app.test_client()

    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        u1 = User.query.get(self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)

    def test_repr(self):
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        self.assertEqual(u1.email, "u1@email.com")
        self.assertEqual(u2.email, "u2@email.com")


    def test_user_is_following(self):
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        u1.following.append(u2)
        db.session.commit()

        self.assertEqual(User.is_following(u1,u2), 1)

    def test_user_is_not_following(self):
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        self.assertEqual(User.is_following(u1,u2), 0)

    def test_user_is_followed_by(self):
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        u1.following.append(u2)
        db.session.commit()

        self.assertEqual(User.is_followed_by(u2, u1), 1)

    def test_user_is_not_followed_by(self):
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        self.assertEqual(User.is_followed_by(u2, u1), 0)

    def test_user_signup(self):
        u1 = User.query.get(self.u1_id)

        self.assertIsNot(type(u1.username), String)
        self.assertIsNot(type(u1.password), String)

        self.assertIsNot(u1.username, "")
        self.assertIsNot(u1.password, "")

    def test_user_signup(self):
        u3 = User.signup("u3", None, "password", None)

        self.assertIsNone(u3.email)

    def test_user_authenticate(self):
        u1 = User.query.get(self.u1_id)

        self.assertEqual(User.authenticate('u1', 'password'), u1)
        self.assertFalse(User.authenticate('123', 'password'), u1)
        self.assertFalse(User.authenticate('u1', '4567'), u1)