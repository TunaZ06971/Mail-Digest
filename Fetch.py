import os
import sys
import datetime as dt
from pathlib import Path

import msal
import requests
from dotenv import load_dotenv

# ---------- Config ----------
load_dotenv()

# 从环境变量读取敏感配置
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
TENANT_ID = os.getenv("AZURE_TENANT_ID", "common")

if not CLIENT_ID:
    print("[ERROR] Missing AZURE_CLIENT_ID in .env", file=sys.stderr)
    print("[HINT] Please copy .env.example to .env and fill in your credentials.")
    sys.exit(1)

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"

SCOPES = [
    "https://graph.microsoft.com/User.Read",
    "https://graph.microsoft.com/Mail.Read",
    "https://graph.microsoft.com/Mail.Send",
]

CACHE_PATH = Path(".token_cache.bin")
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if CACHE_PATH.exists():
        cache.deserialize(CACHE_PATH.read_text())
    return cache


def save_cache(cache: msal.SerializableTokenCache) -> None:
    if cache.has_state_changed:
        CACHE_PATH.write_text(cache.serialize())


def acquire_token_device_code(app: msal.PublicClientApplication, scopes: list[str]) -> dict:
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes, account=accounts[0])
        if result and "access_token" in result:
            return result

    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise RuntimeError(f"Failed to create device flow: {flow}")

    print("\n=== Device Login Required ===")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    return result


def get_access_token() -> tuple[str, dict]:
    cache = load_cache()
    app = msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        token_cache=cache,
    )

    token_result = acquire_token_device_code(app, SCOPES)
    save_cache(cache)

    if "access_token" not in token_result:
        raise RuntimeError(f"Failed to get token: {token_result}")

    return token_result["access_token"], token_result


def print_token_debug(token_result: dict) -> None:
    print(f"\n[DEBUG] Token scopes: {token_result.get('scope', 'N/A')}")
    print(f"[DEBUG] Token expires in: {token_result.get('expires_in', 'N/A')} seconds")


def graph_get(access_token: str, url: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code >= 400:
        print(f"\n[ERROR] Graph API error {r.status_code}")
        print(f"[ERROR] URL: {url}")
        print(f"[ERROR] Response: {r.text}")
        raise RuntimeError(f"Graph API error {r.status_code}: {r.text}")
    return r.json()


def graph_get_all(access_token: str, url: str, params: dict | None = None) -> list[dict]:
    items: list[dict] = []
    next_url = url
    next_params = params

    while next_url:
        data = graph_get(access_token, next_url, next_params)
        items.extend(data.get("value", []))
        next_url = data.get("@odata.nextLink")
        next_params = None

    return items


def get_user_info(access_token: str) -> dict:
    return graph_get(access_token, f"{GRAPH_BASE}/me")


def fetch_recent_messages(access_token: str, hours: int = 24) -> list[dict]:
    cutoff_time = dt.datetime.utcnow() - dt.timedelta(hours=hours)
    cutoff_str = cutoff_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = f"{GRAPH_BASE}/me/messages"
    params = {
        "$filter": f"receivedDateTime ge {cutoff_str} and isDraft eq false",
        "$orderby": "receivedDateTime DESC",
        "$top": "50",
        "$select": "id,subject,from,receivedDateTime,bodyPreview,body,webLink,isRead,hasAttachments",
    }
    try:
        print(f"[DEBUG] Fetching emails since: {cutoff_str} (past {hours} hours)")
        return graph_get_all(access_token, url, params=params)
    except Exception:
        print("[DEBUG] /me/messages failed, trying /me/mailFolders/inbox/messages...")
        url = f"{GRAPH_BASE}/me/mailFolders/inbox/messages"
        params = {
            "$filter": f"receivedDateTime ge {cutoff_str}",
            "$orderby": "receivedDateTime DESC",
            "$top": "50",
            "$select": "id,subject,from,receivedDateTime,bodyPreview,body,webLink,isRead,hasAttachments",
        }
        return graph_get_all(access_token, url, params=params)
