import requests

from Fetch import GRAPH_BASE


def graph_post(access_token: str, url: str, payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    if r.status_code >= 400:
        print(f"\n[ERROR] Graph API error {r.status_code}")
        print(f"[ERROR] URL: {url}")
        print(f"[ERROR] Response: {r.text}")
        raise RuntimeError(f"Graph API error {r.status_code}: {r.text}")
    return r.json() if r.text else {}


def send_html_email(access_token: str, to_address: str, subject: str, html_body: str) -> None:
    url = f"{GRAPH_BASE}/me/sendMail"
    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": html_body,
            },
            "toRecipients": [
                {"emailAddress": {"address": to_address}},
            ],
        },
        "saveToSentItems": True,
    }
    graph_post(access_token, url, payload)
