"""Authentication blueprint – simple session-based login for the demo."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, login_required, login_user, logout_user
from flask import current_app

from app import login_manager

auth_bp = Blueprint("auth", __name__)


# ── Minimal in-memory user model for the demo ─────────────────────────────
class DemoUser(UserMixin):
    """A trivial user object backed by config credentials."""

    def __init__(self, user_id: str):
        self.id = user_id


# Keep a simple cache so Flask-Login can reload the user from the session
_users: dict[str, DemoUser] = {}


@login_manager.user_loader
def load_user(user_id: str) -> DemoUser | None:
    return _users.get(user_id)


# ── Routes ─────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Show login form and authenticate the user."""

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        expected_user = current_app.config.get("DEMO_USERNAME", "admin")
        expected_pass = current_app.config.get("DEMO_PASSWORD", "admin")

        if username == expected_user and password == expected_pass:
            user = DemoUser(username)
            _users[username] = user
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("views.home"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user and redirect to login."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
