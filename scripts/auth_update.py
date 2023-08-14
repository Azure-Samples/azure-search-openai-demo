import os

import urllib3
from azure.identity import AzureDeveloperCliCredential


def update_redirect_uris(credential, app_id, uri):
    urllib3.request(
        "PATCH",
        f"https://graph.microsoft.com/v1.0/applications/{app_id}",
        headers={
            "Authorization": "Bearer "
            + credential.get_token("https://graph.microsoft.com/.default").token,
        },
        json={
            "web": {
                "redirectUris": [
                    "http://localhost:5000/.auth/login/aad/callback",
                    f"{uri}/.auth/login/aad/callback",
                ]
            }
        },
    )


if __name__ == "__main__":
    if os.getenv("AZURE_USE_AUTHENTICATION", "false") != "true":
        print("AZURE_USE_AUTHENTICATION is false, not updating authentication")
        exit(0)

    print("AZURE_USE_AUTHENTICATION is true, updating authentication...")
    credential = AzureDeveloperCliCredential()

    app_id = os.getenv("AZURE_AUTH_APP_ID")
    uri = os.getenv("BACKEND_URI")
    print(f"Updating application registration {app_id} with redirect URI for {uri}")
    update_redirect_uris(credential, app_id, uri)
