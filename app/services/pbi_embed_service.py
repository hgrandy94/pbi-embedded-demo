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

    def get_embed_params_for_single_report(
        self, workspace_id: str, report_id: str, additional_dataset_id: str | None = None
    ) -> str:
        """Get embed params for a report in a workspace.

        Args:
            workspace_id: Workspace Id.
            report_id: Report Id.
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
        )
        dataset_ids = [api_response["datasetId"]]

        if additional_dataset_id is not None:
            dataset_ids.append(additional_dataset_id)

        embed_token = self._get_embed_token_for_single_report_single_workspace(
            report_id, dataset_ids, workspace_id
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
    ) -> EmbedToken:
        """Generate an embed token via the Power BI GenerateToken API."""

        request_body = EmbedTokenRequestBody()

        for dataset_id in dataset_ids:
            request_body.datasets.append({"id": dataset_id})

        request_body.reports.append({"id": report_id})

        if target_workspace_id is not None:
            request_body.targetWorkspaces.append({"id": target_workspace_id})

        embed_token_api = "https://api.powerbi.com/v1.0/myorg/GenerateToken"
        api_response = requests.post(
            embed_token_api,
            data=json.dumps(request_body.__dict__),
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
