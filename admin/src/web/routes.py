from flask import Blueprint
from flask import render_template

bp = Blueprint("main", __name__)

@bp.route("/")
def home():
    return render_template("home.html")
