import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/gmail.compose"
]

# Detect cloud deployment (Railway or Render)
IS_CLOUD = bool(
    os.environ.get("RAILWAY_ENVIRONMENT")
    or os.environ.get("RAILWAY_PROJECT_ID")
    or os.environ.get("RENDER")
)


def get_creds():
    creds = None

    # 1. Load from Environment Variable (for Railway / Render deployments)
    env_token = os.environ.get("GOOGLE_TOKEN_JSON")
    if env_token:
        creds = Credentials.from_authorized_user_info(json.loads(env_token), SCOPES)

    # 2. Fallback to local token.json file
    elif os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # 3. Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if IS_CLOUD:
                raise Exception(
                    "Missing GOOGLE_TOKEN_JSON env var or token is totally invalid. "
                    "Set the GOOGLE_TOKEN_JSON environment variable in Railway/Render dashboard."
                )

            # Local interactive OAuth flow
            # Re-create credentials.json from env var if available
            env_creds = os.environ.get("GOOGLE_CREDENTIALS_JSON")
            if env_creds and not os.path.exists("credentials.json"):
                with open("credentials.json", "w") as f:
                    f.write(env_creds)

            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the refreshed/new token locally if not in cloud
        if not IS_CLOUD:
            with open("token.json", "w") as token:
                token.write(creds.to_json())

    return creds


if __name__ == "__main__":
    print("Generating token.json...")
    get_creds()
    print("Token generated successfully!")
