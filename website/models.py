
from . import db
from flask_login import UserMixin
from sqlalchemy.sql import func


# ==========================================
# Notes
# ==========================================

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    data = db.Column(db.String(10000))

    date = db.Column(
        db.DateTime(timezone=True),
        default=func.now()
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id')
    )


# ==========================================
# Users
# ==========================================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(256),
        nullable=False
    )

    first_name = db.Column(
        db.String(150),
        nullable=False
    )

    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    notes = db.relationship(
        'Note',
        backref='user',
        lazy=True
    )

    test_attempts = db.relationship(
        'TestAttempt',
        backref='user',
        lazy=True,
        cascade='all, delete-orphan'
    )


# ==========================================
# Individual Full-Length Mock Tests
# ==========================================

class MockTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=func.now()
    )

    questions = db.relationship(
        'Question',
        backref='mock_test',
        lazy=True
    )


# ==========================================
# SAT Questions
# ==========================================

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # question_bank or mock_test
    question_type = db.Column(
        db.String(30),
        nullable=False,
        default='question_bank',
        index=True
    )

    image_path = db.Column(
        db.String(255),
        nullable=True
    )

    mock_test_id = db.Column(
        db.Integer,
        db.ForeignKey('mock_test.id'),
        nullable=True,
        index=True
    )

    # Reading and Writing or Math
    section = db.Column(
        db.String(30),
        nullable=False
    )

    # SAT module assignment: 1 or 2
    # Existing questions can remain unassigned.
    module_number = db.Column(
        db.Integer,
        nullable=True
    )

    # Route assignment for Module 2 questions only.
    # Planned values: 'higher' or 'lower'.
    # Module 1 questions should leave this as None.
    module2_route = db.Column(
        db.String(20),
        nullable=True
    )

    domain = db.Column(
        db.String(100),
        nullable=False
    )

    skill = db.Column(
        db.String(150),
        nullable=False
    )

    difficulty = db.Column(
        db.String(20),
        nullable=False
    )

    passage = db.Column(
        db.Text,
        nullable=True
    )

    prompt = db.Column(
        db.Text,
        nullable=False
    )

    # Four answer choices stored as JSON text
    choices = db.Column(
        db.Text,
        nullable=False
    )

    correct_answer = db.Column(
        db.String(1),
        nullable=False
    )

    explanation = db.Column(
        db.Text,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )


# ==========================================
# SAT Test Attempts
# ==========================================

class TestAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        default='in_progress',
        nullable=False
    )

    started_at = db.Column(
        db.DateTime(timezone=True),
        default=func.now()
    )

    completed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    current_section = db.Column(
        db.String(30),
        default='reading_writing'
    )

    current_module = db.Column(
        db.Integer,
        default=1
    )

    # The route selected for this test attempt.
    module2_route = db.Column(
        db.String(20),
        nullable=True
    )

    # Start time for the active module
    module_started_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    # Start time for the scheduled break
    break_started_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    is_on_break = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    mock_test_id = db.Column(
        db.Integer,
        db.ForeignKey('mock_test.id'),
        nullable=True,
        index=True
    )

    answers = db.relationship(
        'TestAnswer',
        backref='attempt',
        lazy=True,
        cascade='all, delete-orphan'
    )


# ==========================================
# Answers to SAT Questions
# ==========================================

class TestAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey('test_attempt.id'),
        nullable=False
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey('question.id'),
        nullable=False
    )

    # A, B, C, D, or None if unanswered
    selected_answer = db.Column(
        db.String(1),
        nullable=True
    )

    is_correct = db.Column(
        db.Boolean,
        nullable=True
    )

    answered_at = db.Column(
        db.DateTime(timezone=True),
        default=func.now()
    )

    # Flag questions for later review
    flagged_for_review = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    question = db.relationship('Question')