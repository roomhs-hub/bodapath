from functools import wraps

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def _password_hash():
    # APP_PASSWORD는 평문으로 .env에 저장돼 있으므로 매 요청마다 해시로 비교한다.
    return generate_password_hash(current_app.config["APP_PASSWORD"])


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("items.list_items"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if check_password_hash(_password_hash(), password):
            session.permanent = True
            session["logged_in"] = True
            next_url = request.args.get("next") or url_for("items.list_items")
            return redirect(next_url)
        flash("비밀번호가 올바르지 않습니다.")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
