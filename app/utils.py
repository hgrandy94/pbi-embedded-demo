"""Configuration validation utility."""

from flask import Flask


class Utils:
    """Helper methods for validating application configuration."""

    @staticmethod
    def check_config(app: Flask) -> str | None:
        """Return an error message if any required config value is missing.

        Args:
            app: The Flask application instance.

        Returns:
            An error string when config is incomplete, otherwise ``None``.
        """

        auth_mode = app.config.get("AUTHENTICATION_MODE", "")

        if auth_mode == "":
            return "Please specify one of the two authentication modes"

        if auth_mode.lower() == "serviceprincipal" and not app.config.get("TENANT_ID"):
            return "Tenant ID is not provided in the configuration"

        if not app.config.get("WORKSPACE_ID"):
            return "Workspace ID is not provided in the configuration"

        if not app.config.get("CLIENT_ID"):
            return "Client ID is not provided in the configuration"

        if auth_mode.lower() == "masteruser":
            if not app.config.get("POWER_BI_USER"):
                return "Master account username is not provided in the configuration"
            if not app.config.get("POWER_BI_PASS"):
                return "Master account password is not provided in the configuration"

        if auth_mode.lower() == "serviceprincipal":
            if not app.config.get("CLIENT_SECRET"):
                return "Client secret is not provided in the configuration"

        if not app.config.get("SCOPE_BASE"):
            return "Scope base is not provided in the configuration"

        if not app.config.get("AUTHORITY_URL"):
            return "Authority URL is not provided in the configuration"

        return None
