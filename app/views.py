"""Main view routes – home page, reports, and Power BI embed endpoints."""

import json

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

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


@views_bp.route("/about")
@login_required
def about():
    """About & Help page."""
    return render_template("about.html")


# ── API: List accessible reports ─────────────────────────────────────

@views_bp.route("/api/reports", methods=["GET"])
@login_required
def list_reports():
    """Return the list of reports the current user is allowed to see."""

    config_result = Utils.check_config(current_app)
    if config_result is not None:
        return Response(
            json.dumps({"errorMsg": config_result}),
            status=500,
            mimetype="application/json",
        )

    try:
        service = PbiEmbedService()
        workspace_reports = service.list_reports_in_workspace(
            current_app.config["WORKSPACE_ID"]
        )

        # Filter reports based on the current user’s allowed set
        user = current_user  # DemoUser instance
        if user.allowed_reports == "*":
            visible = workspace_reports
        else:
            allowed_ids = set(user.allowed_reports)
            visible = [r for r in workspace_reports if r["id"] in allowed_ids]

        return Response(
            json.dumps({"reports": visible}),
            status=200,
            mimetype="application/json",
        )
    except Exception as ex:
        return Response(
            json.dumps({"errorMsg": str(ex)}),
            status=500,
            mimetype="application/json",
        )


# ── API: Get embed info for a specific report ─────────────────────

@views_bp.route("/getembedinfo", methods=["GET"])
@login_required
def get_embed_info():
    """API endpoint – returns embed token and config as JSON.

    Accepts an optional `report_id` query parameter. Falls back to the
    global --report-id CLI value, then to the first accessible report.
    """

    config_result = Utils.check_config(current_app)
    if config_result is not None:
        return Response(
            json.dumps({"errorMsg": config_result}),
            status=500,
            mimetype="application/json",
        )

    try:
        # Determine which report to embed
        report_id = request.args.get("report_id", "").strip()
        if not report_id:
            report_id = current_app.config.get("REPORT_ID", "")

        if not report_id:
            return Response(
                json.dumps({"errorMsg": "No report_id specified."}),
                status=400,
                mimetype="application/json",
            )

        # Authorisation: verify the user may access this report
        user = current_user
        if not user.can_view_report(report_id):
            return Response(
                json.dumps({"errorMsg": "You do not have access to this report."}),
                status=403,
                mimetype="application/json",
            )

        # Build optional RLS identity from the user’s config
        rls_identity = user.rls if user.rls else None

        embed_info = PbiEmbedService().get_embed_params_for_single_report(
            current_app.config["WORKSPACE_ID"],
            report_id,
            rls_identity=rls_identity,
        )
        return Response(embed_info, status=200, mimetype="application/json")
    except Exception as ex:
        return Response(
            json.dumps({"errorMsg": str(ex)}),
            status=500,
            mimetype="application/json",
        )
