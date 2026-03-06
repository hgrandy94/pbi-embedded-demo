"""Azure AD / Microsoft Entra authentication service using MSAL."""

import msal
from flask import current_app as app


class AadService:
    """Acquires an access token for the Power BI REST API."""

    @staticmethod
    def get_access_token() -> str:
        """Generate and return an access token for Power BI.

        Supports both *ServicePrincipal* and *MasterUser* authentication modes
        as defined in the application configuration.

        Returns:
            str: A valid bearer access token.

        Raises:
            Exception: When the token cannot be acquired.
        """

        response = None

        try:
            auth_mode = app.config["AUTHENTICATION_MODE"].lower()

            if auth_mode == "masteruser":
                # Public client – username / password flow
                client_app = msal.PublicClientApplication(
                    app.config["CLIENT_ID"],
                    authority=app.config["AUTHORITY_URL"],
                )
                accounts = client_app.get_accounts(
                    username=app.config["POWER_BI_USER"]
                )

                if accounts:
                    response = client_app.acquire_token_silent(
                        app.config["SCOPE_BASE"], account=accounts[0]
                    )

                if not response:
                    response = client_app.acquire_token_by_username_password(
                        app.config["POWER_BI_USER"],
                        app.config["POWER_BI_PASS"],
                        scopes=app.config["SCOPE_BASE"],
                    )

            elif auth_mode == "serviceprincipal":
                # Confidential client – client credentials flow (recommended)
                authority = app.config["AUTHORITY_URL"].replace(
                    "organizations", app.config["TENANT_ID"]
                )
                client_app = msal.ConfidentialClientApplication(
                    app.config["CLIENT_ID"],
                    client_credential=app.config["CLIENT_SECRET"],
                    authority=authority,
                )
                response = client_app.acquire_token_for_client(
                    scopes=app.config["SCOPE_BASE"]
                )

            try:
                return response["access_token"]
            except KeyError:
                raise Exception(response["error_description"])

        except Exception as ex:
            raise Exception("Error retrieving Access token\n" + str(ex))
