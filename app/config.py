"""Default configuration values.

All actual values are injected at runtime via CLI arguments in ``main.py``.
This module only documents the expected keys and their defaults so that
other parts of the codebase can reference ``app.config[...]`` safely.
"""

# fmt: off
DEFAULTS: dict[str, object] = {
    "SECRET_KEY":           "change-me-in-production",
    "DEMO_USERNAME":        "admin",
    "DEMO_PASSWORD":        "admin",
    "AUTHENTICATION_MODE":  "ServicePrincipal",
    "TENANT_ID":            "",
    "CLIENT_ID":            "",
    "CLIENT_SECRET":        "",
    "WORKSPACE_ID":         "",
    "REPORT_ID":            "",
    "POWER_BI_USER":        "",
    "POWER_BI_PASS":        "",
    "SCOPE_BASE":           ["https://analysis.windows.net/powerbi/api/.default"],
    "AUTHORITY_URL":        "https://login.microsoftonline.com/organizations",
}
# fmt: on
