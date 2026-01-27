import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from openai import OpenAI
from dotenv import load_dotenv


# ---------- Config ----------
load_dotenv()

# 从环境变量读取敏感配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
HKT_TZ = timezone(timedelta(hours=8))

if not DEEPSEEK_API_KEY:
    print("[ERROR] Missing DEEPSEEK_API_KEY in .env", file=sys.stderr)
    print("[HINT] Please copy .env.example to .env and fill in your credentials.")
    sys.exit(1)


def build_summary_input(email: dict, max_chars: int = 4000) -> str:
    body_text = email.get("body_text", "") or ""
    preview = email.get("preview", "") or ""
    content = body_text.strip() or preview.strip()
    if len(content) > max_chars:
        content = content[:max_chars].rstrip() + "..."
    return content


def parse_summary_response(content: str) -> tuple[str, str]:
    """
    解析模型返回的 JSON 摘要内容

    Returns:
        summary_zh, summary_en
    """
    try:
        parsed = json.loads(content)
        return parsed.get("summary_zh", "").strip(), parsed.get("summary_en", "").strip()
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
                return parsed.get("summary_zh", "").strip(), parsed.get("summary_en", "").strip()
            except json.JSONDecodeError:
                pass
    return content.strip(), ""


def summarize_email(client: OpenAI, email: dict) -> dict:
    """
    使用 DeepSeek API 为单封邮件生成摘要
    
    Args:
        client: OpenAI 客户端
        email: 邮件数据字典
        
    Returns:
        AI 生成的摘要文本
    """
    subject = email.get("subject", "(no subject)")
    sender = email.get("sender", "Unknown")
    content = build_summary_input(email)
    
    # 构建 prompt
    prompt = f"""你是一个邮件助手。请用中文和英文各用一句话概括以下邮件的核心内容：

标题：{subject}
发件人：{sender}
内容：{content}

要求：
1. 中文摘要不超过50字
2. 英文摘要不超过30个单词
3. 只返回 JSON 格式，不要添加额外说明
4. JSON 格式如下：
{{"summary_zh":"...","summary_en":"..."}}
"""
    
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        content = response.choices[0].message.content.strip()
        summary_zh, summary_en = parse_summary_response(content)
        return {"summary_zh": summary_zh, "summary_en": summary_en}
    
    except Exception as e:
        print(f"[ERROR] Failed to summarize email '{subject}': {e}")
        return {"summary_zh": "摘要生成失败", "summary_en": "Summary failed"}


def batch_summarize(emails: list[dict]) -> list[dict]:
    """
    批量为邮件生成摘要
    
    Args:
        emails: 邮件列表
        
    Returns:
        包含摘要的邮件列表
    """
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )
    
    total = len(emails)
    print(f"\n[INFO] Starting to summarize {total} emails...")
    
    for i, email in enumerate(emails, 1):
        print(f"[{i}/{total}] Summarizing: {email.get('subject', '(no subject)')[:50]}...")
        summary = summarize_email(client, email)
        email["summary_zh"] = summary.get("summary_zh", "")
        email["summary_en"] = summary.get("summary_en", "")
    
    print(f"\n[SUCCESS] Completed {total} email summaries")
    return emails




def main():
    """
    主函数：读取 JSON，调用 AI 生成摘要，输出 Markdown/HTML
    """
    today = datetime.now(HKT_TZ).strftime("%Y%m%d")
    json_path = Path("output") / f"emails_{today}.json"
    
    if not json_path.exists():
        print(f"[ERROR] JSON file not found: {json_path}")
        print("Please run Cleaner.py first to generate the JSON file.")
        return
    
    # 读取邮件数据
    print(f"[INFO] Loading emails from: {json_path}")
    emails = json.loads(json_path.read_text(encoding="utf-8"))
    
    if not emails:
        print("[WARNING] No emails found in JSON file.")
        return
    
    # 批量生成摘要
    emails_with_summary = batch_summarize(emails)
    
    # 生成摘要文件
    print(f"\n[INFO] Generating summary files...")
    from Generate import generate_summaries
    summary_path, html_summary_path = generate_summaries(emails_with_summary)
    
    print(f"[SUCCESS] Summary saved to: {summary_path.resolve()}")
    print(f"[SUCCESS] HTML summary saved to: {html_summary_path.resolve()}")


if __name__ == "__main__":
    main()
