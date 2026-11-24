"""Login and logout routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db import get_user_by_username
from app.utils.security import (
    current_username,
    login_required,
    login_user,
    logout_user,
    verify_password,
)

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_username():
        return redirect(url_for("main.dashboard"))

    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = get_user_by_username(username) if username else None
        if user is None or not verify_password(user["password_hash"], password):
            # Generic message — do not reveal which field failed
            error = "Invalid username or password."
        else:
            login_user(user["id"], user["username"])
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("main.dashboard"))

    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("auth.login"))
