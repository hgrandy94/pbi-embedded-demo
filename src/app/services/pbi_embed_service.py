"""Power BI embed service – generates embed tokens and configuration."""

import json

import requests
from flask import abort, current_app as app

from app.models.embed_config import EmbedConfig
from app.models.embed_token import EmbedToken
from app.models.embed_token_request_body import EmbedTokenRequestBody
from app.models.report_config import ReportConfig
from app.services.aad_service import AadService


class PbiEmbedService:
    """Interacts with the Power BI REST API to retrieve embed artefacts."""

    # ── List all reports in a workspace ─────────────────────────────────

    def list_reports_in_workspace(self, workspace_id: str) -> list[dict]:
        """Return a list of report metadata dicts from the workspace.

        Each dict has keys: id, name, embedUrl, datasetId.
        """
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports"
        api_response = requests.get(url, headers=self._get_request_header())

        if api_response.status_code != 200:
            abort(
                api_response.status_code,
                description=(
                    f"Error while listing reports\n"
                    f"{api_response.reason}:\t{api_response.text}\n"
                    f"RequestId:\t{api_response.headers.get('RequestId')}"
                ),
            )

        data = api_response.json()
        reports = []
        for r in data.get("value", []):
            reports.append({
                "id": r["id"],
                "name": r["name"],
                "embedUrl": r["embedUrl"],
                "datasetId": r.get("datasetId", ""),
            })
        return reports

    # ── Embed params for a single report (with optional RLS) ───────────

    def get_embed_params_for_single_report(
        self,
        workspace_id: str,
        report_id: str,
        rls_identity: dict | None = None,
        additional_dataset_id: str | None = None,
    ) -> str:
        """Get embed params for a report in a workspace.

        Args:
            workspace_id: Workspace Id.
            report_id: Report Id.
            rls_identity: Optional dict with ``username`` and ``roles`` for RLS.
            additional_dataset_id: Optional extra dataset for dynamic binding.

        Returns:
            JSON string with embed configuration.
        """

        report_url = (
            f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/reports/{report_id}"
        )
        api_response = requests.get(report_url, headers=self._get_request_header())

        if api_response.status_code != 200:
            abort(
                api_response.status_code,
                description=(
                    f"Error while retrieving Embed URL\n"
                    f"{api_response.reason}:\t{api_response.text}\n"
                    f"RequestId:\t{api_response.headers.get('RequestId')}"
                ),
            )

        api_response = json.loads(api_response.text)
        report = ReportConfig(
            api_response["id"],
            api_response["name"],
            api_response["embedUrl"],
            api_response.get("datasetId"),
        )
        dataset_ids = [api_response["datasetId"]]

        if additional_dataset_id is not None:
            dataset_ids.append(additional_dataset_id)

        embed_token = self._get_embed_token_for_single_report_single_workspace(
            report_id, dataset_ids, workspace_id, rls_identity=rls_identity,
        )

        embed_config = EmbedConfig(
            embed_token.tokenId,
            embed_token.token,
            embed_token.tokenExpiry,
            [report.__dict__],
        )
        return json.dumps(embed_config.__dict__)

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_embed_token_for_single_report_single_workspace(
        self,
        report_id: str,
        dataset_ids: list[str],
        target_workspace_id: str | None = None,
        *,
        rls_identity: dict | None = None,
    ) -> EmbedToken:
        """Generate an embed token via the Power BI GenerateToken API.

        Args:
            report_id: The report to generate a token for.
            dataset_ids: Dataset(s) backing the report.
            target_workspace_id: Workspace containing the report.
            rls_identity: Optional RLS effective identity dict with
                ``username`` (str) and ``roles`` (list[str]).
        """

        request_body = EmbedTokenRequestBody()

        for dataset_id in dataset_ids:
            request_body.datasets.append({"id": dataset_id})

        request_body.reports.append({"id": report_id})

        if target_workspace_id is not None:
            request_body.targetWorkspaces.append({"id": target_workspace_id})

        # ── Row-Level Security (EffectiveIdentity) ─────────────────────
        if rls_identity:
            identity = {
                "username": rls_identity["username"],
                "roles": rls_identity.get("roles", []),
                "datasets": [ds["id"] for ds in request_body.datasets],
            }
            request_body.identities.append(identity)

        embed_token_api = "https://api.powerbi.com/v1.0/myorg/GenerateToken"

        # Exclude empty identities list so non-RLS reports work
        body = request_body.__dict__.copy()
        if not body.get("identities"):
            del body["identities"]

        api_response = requests.post(
            embed_token_api,
            data=json.dumps(body),
            headers=self._get_request_header(),
        )

        if api_response.status_code != 200:
            abort(
                api_response.status_code,
                description=(
                    f"Error while retrieving Embed token\n"
                    f"{api_response.reason}:\t{api_response.text}\n"
                    f"RequestId:\t{api_response.headers.get('RequestId')}"
                ),
            )

        api_response = json.loads(api_response.text)
        return EmbedToken(
            api_response["tokenId"],
            api_response["token"],
            api_response["expiration"],
        )

    @staticmethod
    def _get_request_header() -> dict[str, str]:
        """Build an authorised request header for the Power BI REST API."""
        return {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + AadService.get_access_token(),
        }
