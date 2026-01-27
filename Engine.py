import os
import json
import datetime as dt
from pathlib import Path

from dotenv import load_dotenv

import Fetch
import Enrich
import Display
import Generate
import Send
from Cleaner import clean_emails_from_raw_data
from AI_Summarizer import batch_summarize


# ---------- Config ----------
load_dotenv()

HKT_TZ = dt.timezone(dt.timedelta(hours=8))
RAW_OUTPUT_DIR = Path("output")
STAGE_DIR = Path("Stage_1")
SUMMARY_DIR = Path("Output")

# 从环境变量读取收件人配置
SUMMARY_TO = os.getenv("SUMMARY_TO", "your_email@example.com")


def main() -> None:
    access_token, token_result = Fetch.get_access_token()
    Fetch.print_token_debug(token_result)

    try:
        print("\n[DEBUG] Testing /me endpoint...")
        me_data = Fetch.get_user_info(access_token)
        print(f"[DEBUG] User info: {me_data.get('userPrincipalName')}, {me_data.get('mail')}")
    except Exception as e:
        print(f"[ERROR] Failed to get user info: {e}")
        raise

    msgs = Fetch.fetch_recent_messages(access_token, hours=24)

    if not msgs:
        print("\n[WARNING] No emails found in the past 24 hours.")
        return

    print("\n[INFO] Fetching full bodies and inline images...")
    msgs = Enrich.enrich_messages_with_bodies(access_token, msgs)

    today = dt.datetime.now(HKT_TZ).strftime("%Y%m%d")

    html_path = Display.write_digest_html(msgs, hours=24, out_dir=STAGE_DIR)
    print(f"\n✅ HTML saved: {html_path.resolve()}")

    json_path = RAW_OUTPUT_DIR / f"emails_{today}.json"

    try:
        cleaned_emails = clean_emails_from_raw_data(msgs)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(cleaned_emails, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"✅ JSON saved: {json_path.resolve()}")
    except Exception as e:
        print(f"[WARNING] Failed to save JSON: {e}")
        return

    try:
        print(f"\n[INFO] Starting AI summarization...")
        emails_with_summary = batch_summarize(cleaned_emails)
        summary_md_path, summary_html_path = Generate.generate_summaries(
            emails_with_summary, out_dir=SUMMARY_DIR
        )

        print(f"\n✅ All done! Files generated:")
        print(f"   - HTML: {html_path.resolve()}")
        print(f"   - JSON: {json_path.resolve()}")
        print(f"   - Summary (MD): {summary_md_path.resolve()}")
        print(f"   - Summary (HTML): {summary_html_path.resolve()}")

        try:
            subject_date = dt.datetime.now(HKT_TZ).strftime("%Y-%m-%d")
            email_subject = f"Mail_Digest {subject_date}"
            html_body = summary_html_path.read_text(encoding="utf-8")
            print(f"\n[INFO] Sending summary email to {SUMMARY_TO}...")
            Send.send_html_email(access_token, SUMMARY_TO, email_subject, html_body)
            print("[SUCCESS] Summary email sent.")
        except Exception as e:
            print(f"[WARNING] Failed to send summary email: {e}")

    except Exception as e:
        print(f"\n[ERROR] AI summarization failed: {e}")
        print(f"[INFO] HTML and JSON files are still available.")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
