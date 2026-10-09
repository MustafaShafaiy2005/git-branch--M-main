
import os
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import inspect, text


db = SQLAlchemy()

DB_NAME = "database.db"


def create_app():
    app = Flask(__name__)

    # Load the secret key from the environment.
    # Never commit the secret key to GitHub.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

    if not app.config["SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY is missing. Set it in your environment or .env file."
        )

    # Use the existing SQLite database in the instance folder.
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    database_path = instance_path / DB_NAME

    # Correct SQLite URI for Windows.
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "sqlite:///" + database_path.resolve().as_posix()
    )

    db.init_app(app)

    from .views import views
    from .auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/")

    from .models import (
        User,
        Note,
        Question,
        MockTest,
        TestAttempt,
        TestAnswer,
    )

    with app.app_context():
        # Create missing tables without deleting existing data.
        db.create_all()

        # Add a database column only when it is missing.
        def add_column_if_missing(table_name, column_name, column_sql):
            """
            Add a column only when it does not already exist.
            Existing rows and tables are preserved.
            """
            inspector = inspect(db.engine)

            existing_columns = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }

            if column_name not in existing_columns:
                with db.engine.begin() as connection:
                    connection.execute(
                        text(
                            f'ALTER TABLE "{table_name}" '
                            f'ADD COLUMN "{column_name}" {column_sql}'
                        )
                    )

                print(
                    f"Migration added: {table_name}.{column_name}"
                )

        # Migrate User table.
        add_column_if_missing(
            "user",
            "is_admin",
            "BOOLEAN NOT NULL DEFAULT 0",
        )

        # Migrate Question table.
        add_column_if_missing(
            "question",
            "question_type",
            "VARCHAR(30) NOT NULL DEFAULT 'question_bank'",
        )

        add_column_if_missing(
            "question",
            "image_path",
            "VARCHAR(255)",
        )

        add_column_if_missing(
            "question",
            "mock_test_id",
            "INTEGER",
        )

        # SAT Module 1 or Module 2.
        # Existing questions remain unassigned (NULL).
        add_column_if_missing(
            "question",
            "module_number",
            "INTEGER",
        )

        # Adaptive route for Module 2 questions.
        # Expected values: 'higher' or 'lower'.
        add_column_if_missing(
            "question",
            "module2_route",
            "VARCHAR(20)",
        )

        # Migrate TestAttempt table.
        add_column_if_missing(
            "test_attempt",
            "mock_test_id",
            "INTEGER",
        )

        # Persistent module timer start timestamp.
        add_column_if_missing(
            "test_attempt",
            "module_started_at",
            "DATETIME",
        )

        # Persistent break start timestamp.
        add_column_if_missing(
            "test_attempt",
            "break_started_at",
            "DATETIME",
        )

        # Whether the student is currently on a break.
        add_column_if_missing(
            "test_attempt",
            "is_on_break",
            "BOOLEAN NOT NULL DEFAULT 0",
        )

        # Migrate TestAnswer table.
        add_column_if_missing(
            "test_answer",
            "flagged_for_review",
            "BOOLEAN NOT NULL DEFAULT 0",
        )

        # Verify all required migrations.
        inspector = inspect(db.engine)

        required_columns = {
            "user": {
                "is_admin",
            },
            "question": {
                "question_type",
                "image_path",
                "mock_test_id",
                "module_number",
                "module2_route",
            },
            "test_attempt": {
                "mock_test_id",
                "module_started_at",
                "break_started_at",
                "is_on_break",
            },
            "test_answer": {
                "flagged_for_review",
            },
        }

        for table_name, expected_columns in required_columns.items():
            actual_columns = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }

            missing_columns = expected_columns - actual_columns

            if missing_columns:
                raise RuntimeError(
                    f"Missing columns in {table_name}: "
                    f"{sorted(missing_columns)}"
                )

        print("Database location:", database_path.resolve())
        print("User migration verified.")
        print("Question migration verified.")
        print("TestAttempt migration verified.")
        print("TestAnswer migration verified.")

    # Configure Flask-Login.
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app


def create_database(app):
    with app.app_context():
        db.create_all()
        print("Database tables checked/created!")