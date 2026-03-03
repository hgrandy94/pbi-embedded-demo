"""Main view routes – home page and Power BI reports."""

import json

from flask import Blueprint, render_template
from flask_login import login_required

from app.services.pbi_embed_service import PbiEmbedService
from app.utils import Utils
from flask import current_app

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
@login_required
def home():
    """Landing / home page shown after login."""
    return render_template("home.html")


@views_bp.route("/reports")
@login_required
def reports():
    """Page that embeds the Power BI report."""
    return render_template("reports.html")


@views_bp.route("/getembedinfo", methods=["GET"])
@login_required
def get_embed_info():
    """API endpoint – returns embed token and config as JSON."""

    config_result = Utils.check_config(current_app)
    if config_result is not None:
        return json.dumps({"errorMsg": config_result}), 500

    try:
        embed_info = PbiEmbedService().get_embed_params_for_single_report(
            current_app.config["WORKSPACE_ID"],
            current_app.config["REPORT_ID"],
        )
        return embed_info
    except Exception as ex:
        return json.dumps({"errorMsg": str(ex)}), 500
