"""Main view routes – home page, reports, and Power BI embed endpoints."""

import csv
import io
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


# ── API: Discover dataset tables ─────────────────────────────────────

@views_bp.route("/api/dataset-tables", methods=["GET"])
@login_required
def dataset_tables():
    """Return the names of non-hidden tables in the dataset backing a report.

    Uses the DAX ``INFO.TABLES()`` function via the Execute Queries API.
    Query param: ``report_id`` (required).
    """

    config_result = Utils.check_config(current_app)
    if config_result is not None:
        return Response(
            json.dumps({"errorMsg": config_result}),
            status=500,
            mimetype="application/json",
        )

    report_id = request.args.get("report_id", "").strip()
    if not report_id:
        return Response(
            json.dumps({"errorMsg": "report_id is required."}),
            status=400,
            mimetype="application/json",
        )

    user = current_user
    if not user.can_view_report(report_id):
        return Response(
            json.dumps({"errorMsg": "You do not have access to this report."}),
            status=403,
            mimetype="application/json",
        )

    try:
        service = PbiEmbedService()
        workspace_id = current_app.config["WORKSPACE_ID"]
        dataset_id = service.get_dataset_id_for_report(workspace_id, report_id)

        rls_username = None
        if user.rls:
            rls_username = user.rls.get("username")

        dax = (
            "EVALUATE SELECTCOLUMNS("
            "FILTER(INFO.TABLES(), [IsHidden] = FALSE()), "
            "\"Name\", [Name])"
        )
        result = service.execute_dax_query(
            workspace_id, dataset_id, dax, rls_username=rls_username,
        )

        tables = []
        for row in result.get("results", [{}])[0].get("tables", [{}])[0].get("rows", []):
            name = row.get("[Name]", "")
            if name:
                tables.append(name)

        return Response(
            json.dumps({"tables": sorted(tables), "datasetId": dataset_id}),
            status=200,
            mimetype="application/json",
        )
    except Exception as ex:
        return Response(
            json.dumps({"errorMsg": str(ex)}),
            status=500,
            mimetype="application/json",
        )


# ── API: Export data via DAX query ───────────────────────────────────

@views_bp.route("/api/export-data", methods=["POST"])
@login_required
def export_data():
    """Execute a DAX query and return the result as a CSV download.

    Expects JSON body: ``{"report_id": "…", "dax_query": "…"}``.
    RLS is applied automatically via ``impersonatedUserName`` when the
    current user has an RLS identity configured.
    """

    config_result = Utils.check_config(current_app)
    if config_result is not None:
        return Response(
            json.dumps({"errorMsg": config_result}),
            status=500,
            mimetype="application/json",
        )

    body = request.get_json(silent=True) or {}
    report_id = (body.get("report_id") or "").strip()
    dax_query = (body.get("dax_query") or "").strip()

    if not report_id:
        return Response(
            json.dumps({"errorMsg": "report_id is required."}),
            status=400,
            mimetype="application/json",
        )
    if not dax_query:
        return Response(
            json.dumps({"errorMsg": "dax_query is required."}),
            status=400,
            mimetype="application/json",
        )

    user = current_user
    if not user.can_view_report(report_id):
        return Response(
            json.dumps({"errorMsg": "You do not have access to this report."}),
            status=403,
            mimetype="application/json",
        )

    try:
        service = PbiEmbedService()
        workspace_id = current_app.config["WORKSPACE_ID"]
        dataset_id = service.get_dataset_id_for_report(workspace_id, report_id)

        rls_username = None
        if user.rls:
            rls_username = user.rls.get("username")

        result = service.execute_dax_query(
            workspace_id, dataset_id, dax_query, rls_username=rls_username,
        )

        # Extract rows from the Execute Queries response
        rows = (
            result.get("results", [{}])[0]
            .get("tables", [{}])[0]
            .get("rows", [])
        )

        if not rows:
            return Response(
                json.dumps({"errorMsg": "Query returned no data."}),
                status=200,
                mimetype="application/json",
            )

        # Build CSV — strip the "Table[Column]" notation to just "Column"
        raw_columns = list(rows[0].keys())
        clean_columns = []
        for col in raw_columns:
            # "Table[Column]" → "Column", or "[Column]" → "Column"
            if "[" in col and col.endswith("]"):
                clean_columns.append(col[col.index("[") + 1 : -1])
            else:
                clean_columns.append(col)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(clean_columns)
        for row in rows:
            writer.writerow([row.get(col, "") for col in raw_columns])

        csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM for Excel compat

        return Response(
            csv_bytes,
            status=200,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"},
        )
    except Exception as ex:
        return Response(
            json.dumps({"errorMsg": str(ex)}),
            status=500,
            mimetype="application/json",
        )
