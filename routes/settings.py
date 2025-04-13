from flask import Blueprint, render_template, session
from utils import login_required

bp = Blueprint("settings", __name__)

@bp.route("/settings")
@login_required
def settings_page():
    return render_template("settings.html", username=session["username"])