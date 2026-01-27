from pathlib import Path
from datetime import datetime, timezone, timedelta


HKT_TZ = timezone(timedelta(hours=8))


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def format_time(time_str: str) -> str:
    try:
        dt_obj = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return dt_obj.astimezone(HKT_TZ).strftime("%Y-%m-%d %H:%M HKT")
    except Exception:
        return time_str


def generate_markdown_summary(emails: list[dict], output_path: Path) -> None:
    now = datetime.now(HKT_TZ).strftime("%Y-%m-%d %H:%M HKT")
    total = len(emails)

    lines = [
        "# 邮件摘要",
        "",
        f"**生成时间**：{now}  ",
        f"**邮件总数**：{total} 封  ",
        "",
        "---",
        "",
    ]

    for i, email in enumerate(emails, 1):
        subject = email.get("subject", "(no subject)")
        sender = email.get("sender", "Unknown")
        time = format_time(email.get("time", ""))
        summary_zh = email.get("summary_zh", "无摘要")
        summary_en = email.get("summary_en", "No summary")
        link = email.get("link", "#")
        status = email.get("status", "READ")

        lines.extend([
            f"## {i}. {subject}",
            "",
            f"**AI 摘要（中文）**：{summary_zh}  ",
            f"**AI Summary (EN)**：{summary_en}  ",
            f"**发件人**：{sender}  ",
            f"**时间**：{time}  ",
            f"**状态**：{status}  ",
            f"**查看邮件**：[点击这里]({link})  ",
            "",
            "---",
            "",
        ])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def generate_html_summary(emails: list[dict], output_path: Path) -> None:
    now = datetime.now(HKT_TZ).strftime("%Y-%m-%d %H:%M HKT")
    total = len(emails)

    rows = []
    for i, email in enumerate(emails, 1):
        subject = html_escape(email.get("subject", "(no subject)"))
        sender = html_escape(email.get("sender", "Unknown"))
        time = html_escape(format_time(email.get("time", "")))
        summary_zh = html_escape(email.get("summary_zh", "无摘要"))
        summary_en = html_escape(email.get("summary_en", "No summary"))
        link = email.get("link", "#")
        status = html_escape(email.get("status", "READ"))

        rows.append(f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid #eee;">
            <div style="font-size:15px;font-weight:600;color:#111;">{i}. {subject}</div>
            <div style="margin-top:4px;font-size:12px;color:#666;">{sender} · {time} · {status}</div>
            <div style="margin-top:8px;font-size:14px;color:#111;">{summary_zh}</div>
            <div style="margin-top:4px;font-size:13px;color:#555;">{summary_en}</div>
            <div style="margin-top:8px;font-size:12px;">
              <a href="{link}" style="color:#0b57d0;text-decoration:none;">查看邮件</a>
            </div>
          </td>
        </tr>
        """)

    rows_html = "\n".join(rows)

    html = f"""<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>邮件摘要</title>
</head>
<body style="margin:0;padding:0;background:#f4f6fb;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6fb;padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" cellpadding="0" cellspacing="0" width="680" style="width:100%;max-width:680px;background:#ffffff;border-radius:12px;overflow:hidden;font-family:Arial, Helvetica, sans-serif;">
          <tr>
            <td style="padding:18px 16px;border-bottom:1px solid #eee;">
              <div style="font-size:20px;font-weight:700;color:#111;">邮件摘要</div>
              <div style="margin-top:6px;font-size:12px;color:#666;">生成时间：{now} · 邮件总数：{total} 封</div>
            </td>
          </tr>
          {rows_html}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


def generate_summaries(emails: list[dict], out_dir: Path | None = None) -> tuple[Path, Path]:
    if out_dir is None:
        out_dir = Path("Output")
    out_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(HKT_TZ).strftime("%Y%m%d")
    md_path = out_dir / f"summary_{today}.md"
    html_path = out_dir / f"summary_{today}.html"

    generate_markdown_summary(emails, md_path)
    generate_html_summary(emails, html_path)

    return md_path, html_path
