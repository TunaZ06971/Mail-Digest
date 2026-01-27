import re

from Fetch import GRAPH_BASE, graph_get


CID_SRC_RE = re.compile(r"cid:([^'\" >]+)", re.IGNORECASE)


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def html_from_body(body: dict) -> str:
    if not body:
        return ""
    content = body.get("content", "")
    content_type = (body.get("contentType") or "").lower()
    if content_type == "text":
        return html_escape(content).replace("\n", "<br>")
    return content


def replace_cid_sources(html: str, cid_map: dict[str, str]) -> str:
    if not html or not cid_map:
        return html

    def _repl(match: re.Match) -> str:
        cid = match.group(1).strip("<>")
        data_uri = cid_map.get(cid)
        return data_uri if data_uri else match.group(0)

    return CID_SRC_RE.sub(_repl, html)


def fetch_inline_attachments(access_token: str, message_id: str) -> dict[str, str]:
    url = f"{GRAPH_BASE}/me/messages/{message_id}/attachments"
    params = {
        "$select": "id,name,contentType,size,isInline,contentId,contentBytes",
        "$filter": "isInline eq true",
    }
    data = graph_get(access_token, url, params=params)
    inline_map: dict[str, str] = {}
    for attachment in data.get("value", []):
        if attachment.get("@odata.type") != "#microsoft.graph.fileAttachment":
            continue
        if not attachment.get("isInline"):
            continue
        content_id = attachment.get("contentId")
        content_bytes = attachment.get("contentBytes")
        if not content_id or not content_bytes:
            continue
        cid = content_id.strip("<>")
        content_type = attachment.get("contentType") or "application/octet-stream"
        inline_map[cid] = f"data:{content_type};base64,{content_bytes}"
    return inline_map


def enrich_messages_with_bodies(access_token: str, messages: list[dict]) -> list[dict]:
    total = len(messages)
    for i, message in enumerate(messages, 1):
        msg_id = message.get("id")
        body_html = html_from_body(message.get("body", {}))
        if msg_id and message.get("hasAttachments", False):
            try:
                inline_map = fetch_inline_attachments(access_token, msg_id)
                body_html = replace_cid_sources(body_html, inline_map)
            except Exception as e:
                print(f"[WARNING] Failed to fetch inline attachments for {msg_id}: {e}")
        message["body_html"] = body_html
        print(f"[DEBUG] Enriched message {i}/{total}")
    return messages
