import datetime as dt
from pathlib import Path


HKT_TZ = dt.timezone(dt.timedelta(hours=8))


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def format_time_hkt(time_str: str) -> str:
    try:
        dt_utc = dt.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt_utc.astimezone(HKT_TZ).strftime("%Y-%m-%d %H:%M HKT")
    except Exception:
        return time_str


def build_html(messages: list[dict], hours: int = 24) -> str:
    now = dt.datetime.now(HKT_TZ).strftime("%Y-%m-%d %H:%M HKT")
    total = len(messages)
    unread = sum(1 for m in messages if not m.get("isRead", False))

    rows = []
    for m in messages:
        subject = html_escape(m.get("subject") or "(no subject)")
        sender = m.get("from", {}).get("emailAddress", {}).get("name") or ""
        sender = html_escape(sender)
        received = format_time_hkt(m.get("receivedDateTime", ""))
        preview = html_escape(m.get("bodyPreview") or "")
        link = m.get("webLink") or "#"
        is_read = m.get("isRead", False)
        badge = "UNREAD" if not is_read else "READ"
        body_html = m.get("body_html") or ""
        body_section = ""
        if body_html:
            body_section = f"""
          <details class="full">
            <summary>Full content</summary>
            <div class="body">{body_html}</div>
          </details>
            """

        rows.append(f"""
        <div class="card">
          <div class="meta">
            <span class="badge">{badge}</span>
            <span class="time">{received}</span>
          </div>
          <div class="title"><a href="{link}" target="_blank" rel="noreferrer">{subject}</a></div>
          <div class="from">{sender}</div>
          <div class="preview">{preview}</div>
          {body_section}
        </div>
        """)

    cards = "\n".join(rows)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Mail Digest</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; margin: 24px; }}
    .header {{ margin-bottom: 16px; }}
    .kpi {{ color: #444; }}
    .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 12px 14px; margin: 10px 0; }}
    .meta {{ display: flex; gap: 10px; align-items: center; margin-bottom: 6px; }}
    .badge {{ font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid #aaa; }}
    .time {{ color: #666; font-size: 12px; }}
    .title a {{ text-decoration: none; color: #0b57d0; font-weight: 600; }}
    .from {{ color: #333; font-size: 13px; margin-top: 2px; }}
    .preview {{ color: #555; font-size: 13px; margin-top: 6px; white-space: pre-wrap; }}
    details.full {{ margin-top: 8px; }}
    details.full > summary {{ cursor: pointer; color: #0b57d0; font-size: 13px; }}
    .body {{ border-left: 3px solid #eee; margin-top: 8px; padding-left: 10px; background: #fafafa; }}
    .body img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
  <div class="header">
    <h2>Mail Digest (Past {hours} Hours)</h2>
    <div class="kpi">Generated: {now} | Total: {total} | Unread: {unread}</div>
  </div>
  {cards}
</body>
</html>
"""


def write_digest_html(messages: list[dict], hours: int = 24, out_dir: Path | None = None) -> Path:
    if out_dir is None:
        out_dir = Path("Stage_1")
    out_dir.mkdir(parents=True, exist_ok=True)

    today = dt.datetime.now(HKT_TZ).strftime("%Y%m%d")
    html_path = out_dir / f"digest_{today}.html"
    html_path.write_text(build_html(messages, hours=hours), encoding="utf-8")
    return html_path
