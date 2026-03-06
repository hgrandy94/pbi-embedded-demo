import json
import pathlib

import click

from app import create_app


@click.command("pbi-demo")
@click.option("--secret-key", default="change-me-in-production", help="Flask secret key for session signing.")
@click.option(
    "--users-config",
    type=click.Path(exists=True, dir_okay=False),
    default="demo_users.json",
    show_default=True,
    help="Path to JSON file defining demo users and their report/RLS access.",
)
@click.option(
    "--auth-mode",
    type=click.Choice(["ServicePrincipal", "MasterUser"], case_sensitive=False),
    default="ServicePrincipal",
    show_default=True,
    help="Power BI authentication mode.",
)
@click.option("--tenant-id", required=True, help="Azure AD / Microsoft Entra tenant ID.")
@click.option("--client-id", required=True, help="Application (client) ID of the registered app.")
@click.option("--client-secret", default="", help="Client secret (required for ServicePrincipal mode).")
@click.option("--workspace-id", required=True, help="Power BI workspace ID containing the report.")
@click.option("--report-id", default="", help="Optional default report ID (overrides per-user config).")
@click.option("--pbi-user", default="", help="Master user email (MasterUser mode only).")
@click.option("--pbi-pass", default="", help="Master user password (MasterUser mode only).")
@click.option(
    "--scope-base",
    default="https://analysis.windows.net/powerbi/api/.default",
    show_default=True,
    help="OAuth scope for Power BI API.",
)
@click.option(
    "--authority-url",
    default="https://login.microsoftonline.com/organizations",
    show_default=True,
    help="Microsoft Entra authority URL.",
)
@click.option("--port", default=5000, show_default=True, help="Port to run the Flask server on.")
@click.option("--debug/--no-debug", default=True, show_default=True, help="Run Flask in debug mode.")
def main(
    secret_key: str,
    users_config: str,
    auth_mode: str,
    tenant_id: str,
    client_id: str,
    client_secret: str,
    workspace_id: str,
    report_id: str,
    pbi_user: str,
    pbi_pass: str,
    scope_base: str,
    authority_url: str,
    port: int,
    debug: bool,
) -> None:
    """Power BI Embedded Demo – Flask web application."""

    # Load the demo-users JSON file
    users_path = pathlib.Path(users_config)
    with users_path.open() as f:
        users_data = json.load(f)

    config = {
        "SECRET_KEY": secret_key,
        "DEMO_USERS": users_data.get("users", {}),
        "AUTHENTICATION_MODE": auth_mode,
        "TENANT_ID": tenant_id,
        "CLIENT_ID": client_id,
        "CLIENT_SECRET": client_secret,
        "WORKSPACE_ID": workspace_id,
        "REPORT_ID": report_id,
        "POWER_BI_USER": pbi_user,
        "POWER_BI_PASS": pbi_pass,
        "SCOPE_BASE": [s.strip() for s in scope_base.split(",")],
        "AUTHORITY_URL": authority_url,
    }

    app = create_app(config)
    app.run(debug=debug, port=port)


if __name__ == "__main__":
    main()
