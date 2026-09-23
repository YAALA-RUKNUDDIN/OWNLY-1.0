"""Firebase Cloud Messaging provider. Requires FCM_CREDENTIALS_PATH
pointing to a Firebase service-account JSON file."""
import json

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleAuthRequest

from app.core.errors import AppError
from app.integrations.push.base import PushProvider

FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"


class FCMProvider(PushProvider):
    name = "fcm"

    def __init__(self, credentials_path: str):
        try:
            self._creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=["https://www.googleapis.com/auth/firebase.messaging"]
            )
            with open(credentials_path) as f:
                self._project_id = json.load(f).get("project_id", "")
        except Exception as e:
            raise AppError(f"Failed to initialize FCM: {e}")

    def send(self, fcm_tokens: list[str], title: str, body: str, data: dict | None = None) -> list[str]:
        if not fcm_tokens:
            return []
        self._creds.refresh(GoogleAuthRequest())
        headers = {"Authorization": f"Bearer {self._creds.token}", "Content-Type": "application/json"}
        invalid: list[str] = []
        for token in fcm_tokens:
            message = {
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": body},
                    "data": {k: str(v) for k, v in (data or {}).items()},
                    "android": {"priority": "high"},
                }
            }
            resp = requests.post(
                FCM_SEND_URL.format(project_id=self._project_id), json=message, headers=headers, timeout=10
            )
            if resp.status_code in (400, 404) and "UNREGISTERED" in resp.text:
                invalid.append(token)
        return invalid