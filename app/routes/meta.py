from flask import Blueprint, render_template

meta_bp = Blueprint("meta", __name__)


@meta_bp.route("/meta-rankings")  # Or your desired URL
def meta_rankings():
    return render_template("meta_rankings.html")
