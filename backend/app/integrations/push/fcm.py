"""Firebase Cloud Messaging provider.

Supports both:
1. FCM_CREDENTIALS_JSON (raw service account JSON string, ideal for 12-factor / container envs)
2. FCM_CREDENTIALS_PATH (path to service account JSON file on disk)
"""
import json
import logging
import os
from typing import Any

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from app.core.errors import AppError
from app.integrations.push.base import PushProvider

logger = logging.getLogger("ownly.push.fcm")

FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
FCM_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


class FCMProvider(PushProvider):
    name = "fcm"

    def __init__(
        self,
        credentials_path: str | None = None,
        credentials_json: str | None = None,
        credentials: Any = None,
        project_id: str | None = None,
    ):
        self._creds = credentials
        self._project_id = project_id or ""

        if self._creds is None:
            raw_json = (credentials_json or "").strip()
            path = (credentials_path or "").strip()

            try:
                if raw_json:
                    info = json.loads(raw_json)
                    self._creds = service_account.Credentials.from_service_account_info(
                        info, scopes=FCM_SCOPES
                    )
                    self._project_id = self._project_id or info.get("project_id", "")
                elif path and os.path.exists(path):
                    self._creds = service_account.Credentials.from_service_account_file(
                        path, scopes=FCM_SCOPES
                    )
                    with open(path, "r", encoding="utf-8") as f:
                        file_info = json.load(f)
                        self._project_id = self._project_id or file_info.get("project_id", "")
                else:
                    raise AppError("Neither valid FCM_CREDENTIALS_JSON nor existing FCM_CREDENTIALS_PATH provided.")
            except Exception as e:
                raise AppError(f"Failed to initialize FCM credentials: {e}")

        if not self._project_id:
            logger.warning("FCM project_id could not be detected from credentials; message dispatch may fail.")

    def _get_valid_token(self) -> str:
        """Returns a valid OAuth2 bearer token, refreshing only when expired or invalid."""
        if not self._creds.valid:
            self._creds.refresh(GoogleAuthRequest())
        return self._creds.token

    def send(
        self,
        fcm_tokens: list[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> list[str]:
        if not fcm_tokens:
            return []

        try:
            bearer_token = self._get_valid_token()
        except Exception as e:
            logger.error(f"Failed to obtain OAuth2 token for FCM: {e}")
            return []

        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }
        url = FCM_SEND_URL.format(project_id=self._project_id)
        invalid_tokens: list[str] = []

        string_data = {k: str(v) for k, v in (data or {}).items()}

        for token in fcm_tokens:
            payload = {
                "message": {
                    "token": token,
                    "notification": {
                        "title": title,
                        "body": body,
                    },
                    "data": string_data,
                    "android": {
                        "priority": "high",
                        "notification": {
                            "channel_id": "ownly_alerts",
                            "sound": "default",
                        },
                    },
                    "apns": {
                        "headers": {
                            "apns-priority": "10",
                        },
                        "payload": {
                            "aps": {
                                "sound": "default",
                                "badge": 1,
                            },
                        },
                    },
                }
            }

            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code in (400, 404):
                    resp_text = resp.text.upper()
                    if "UNREGISTERED" in resp_text or "INVALID_ARGUMENT" in resp_text:
                        invalid_tokens.append(token)
                elif resp.status_code != 200:
                    logger.warning(f"FCM send failed ({resp.status_code}): {resp.text}")
            except Exception as e:
                logger.error(f"Network error sending FCM push to token {token[:10]}...: {e}")

        return invalid_tokens