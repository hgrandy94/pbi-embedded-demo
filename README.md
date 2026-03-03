# Power BI Embedded Demo

A Python Flask web application that demonstrates embedding Power BI reports using the **App Owns Data** (embed for your customers) pattern.

Built with:

- **Flask** – lightweight web framework
- **Click** – CLI argument parsing (no secrets in files)
- **MSAL** – Microsoft Authentication Library for Azure AD / Microsoft Entra ID
- **Power BI JavaScript SDK** – client-side report embedding
- **uv** – fast Python package manager

## Prerequisites

| Requirement | Details |
|---|---|
| Python 3.14+ | <https://www.python.org/downloads/> |
| uv | <https://docs.astral.sh/uv/> |
| Azure AD app registration | [Register your app](https://learn.microsoft.com/en-us/power-bi/developer/embedded/register-app) |
| Power BI workspace & report | [Create a workspace](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-sample-for-customers?tabs=python) |

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/hgrandy94/pbi-embedded-demo.git
cd pbi-embedded-demo

# 2. Install dependencies with uv
uv sync

# 3. Run the application – pass all secrets as CLI arguments
uv run python main.py \
  --tenant-id "YOUR_TENANT_ID" \
  --client-id "YOUR_CLIENT_ID" \
  --client-secret "YOUR_CLIENT_SECRET" \
  --workspace-id "YOUR_WORKSPACE_ID" \
  --report-id "YOUR_REPORT_ID"
```

Open <http://localhost:5000> in your browser and log in with the demo credentials (default: `admin` / `admin`).

> **Tip:** Run `uv run python main.py --help` to see every available option.

## CLI Options

All configuration is passed via command-line arguments — nothing is stored in files.

| Option | Required | Default | Description |
|---|---|---|---|
| `--tenant-id` | Yes | – | Azure AD / Microsoft Entra tenant ID |
| `--client-id` | Yes | – | Application (client) ID of the registered app |
| `--client-secret` | No | `""` | Client secret (required for ServicePrincipal mode) |
| `--workspace-id` | Yes | – | Power BI workspace ID containing the report |
| `--report-id` | Yes | – | ID of the Power BI report to embed |
| `--auth-mode` | No | `ServicePrincipal` | `ServicePrincipal` or `MasterUser` |
| `--pbi-user` | No | `""` | Master user email (MasterUser mode only) |
| `--pbi-pass` | No | `""` | Master user password (MasterUser mode only) |
| `--demo-username` | No | `admin` | Web app login username |
| `--demo-password` | No | `admin` | Web app login password |
| `--secret-key` | No | *(random)* | Flask session signing key |
| `--scope-base` | No | `https://analysis.windows.net/powerbi/api/.default` | OAuth scope |
| `--authority-url` | No | `https://login.microsoftonline.com/organizations` | Entra authority |
| `--port` | No | `5000` | Port for the Flask server |
| `--debug / --no-debug` | No | `--debug` | Flask debug mode |

## Project Structure

```
pbi-embedded-demo/
├── main.py                          # Entry point (click CLI)
├── pyproject.toml                   # Project metadata & dependencies
├── app/
│   ├── __init__.py                  # Flask app factory
│   ├── config.py                    # Default configuration reference
│   ├── auth.py                      # Login / logout routes
│   ├── views.py                     # Home & Reports routes + embed API
│   ├── utils.py                     # Config validation
│   ├── models/
│   │   ├── embed_config.py          # EmbedConfig model
│   │   ├── embed_token.py           # EmbedToken model
│   │   ├── embed_token_request_body.py
│   │   └── report_config.py         # ReportConfig model
│   ├── services/
│   │   ├── aad_service.py           # Azure AD token acquisition (MSAL)
│   │   └── pbi_embed_service.py     # Power BI REST API interactions
│   ├── templates/
│   │   ├── base.html                # Base layout with navbar
│   │   ├── login.html               # Login page
│   │   ├── home.html                # Home / landing page
│   │   └── reports.html             # Embedded report page
│   └── static/
│       ├── css/style.css            # Custom styles
│       └── js/embedding.js          # Power BI JS embedding logic
└── README.md
```

## How It Works

1. The user logs into the Flask web app (simple session-based auth).
2. On the **Reports** page, the browser calls `/getembedinfo`.
3. The Flask backend authenticates with Microsoft Entra ID using MSAL (service principal or master user).
4. An embed token is requested from the Power BI REST API.
5. The token + embed URL are returned to the browser.
6. The **Power BI JavaScript SDK** renders the report in an iframe.

## References

- [Power BI Developer Samples (Python)](https://github.com/microsoft/PowerBI-Developer-Samples/tree/master/Python/Embed%20for%20your%20customers)
- [Tutorial: Embed for your customers](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-sample-for-customers?tabs=python)
- [Power BI JavaScript SDK](https://aka.ms/pbijs)
- [Power BI REST API](https://learn.microsoft.com/en-us/rest/api/power-bi/)

## Security Note

> **Important:** All secrets are passed as command-line arguments and never stored in repository files. For production use, feed arguments from a vault service (e.g. Azure Key Vault, CI/CD secrets). The demo login is intentionally simple — replace it with a proper identity provider for real deployments.
