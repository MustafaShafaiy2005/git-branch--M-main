from getpass import getpass

from website import create_app, db
from website.models import User
from werkzeug.security import check_password_hash

app = create_app()

with app.app_context():
    email = input("Enter your existing account email: ").strip().lower()
    user = User.query.filter_by(email=email).first()

    if user is None:
        print("Account not found. No changes were made.")
    else:
        password = getpass("Enter your account password: ")

        if not check_password_hash(user.password, password):
            print("Incorrect password. No changes were made.")
        else:
            user.is_admin = True
            db.session.commit()
            print("Administrator role assigned successfully.")
