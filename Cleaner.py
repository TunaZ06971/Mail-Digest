import json
from pathlib import Path
from bs4 import BeautifulSoup


def parse_html_to_json(html_path: Path) -> list[dict]:
    """
    解析 HTML 文件，提取邮件信息为 JSON 格式
    
    Args:
        html_path: HTML 文件路径
        
    Returns:
        邮件列表，每封邮件包含 subject, sender, time, preview, link
    """
    if not html_path.exists():
        raise FileNotFoundError(f"HTML file not found: {html_path}")
    
    html_content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html_content, "html.parser")
    
    emails = []
    
    # 找到所有邮件卡片
    cards = soup.find_all("div", class_="card")
    
    for card in cards:
        try:
            # 提取标题和链接
            title_elem = card.find("div", class_="title")
            link_elem = title_elem.find("a") if title_elem else None
            subject = link_elem.get_text(strip=True) if link_elem else "(no subject)"
            link = link_elem.get("href", "#") if link_elem else "#"
            
            # 提取发件人
            from_elem = card.find("div", class_="from")
            sender = from_elem.get_text(strip=True) if from_elem else ""
            
            # 提取时间
            time_elem = card.find("span", class_="time")
            time = time_elem.get_text(strip=True) if time_elem else ""
            
            # 提取预览内容
            preview_elem = card.find("div", class_="preview")
            preview = preview_elem.get_text(strip=True) if preview_elem else ""

            # 提取正文内容（如果有）
            body_elem = card.find("div", class_="body")
            body_text = body_elem.get_text(" ", strip=True) if body_elem else ""
            
            # 提取状态
            badge_elem = card.find("span", class_="badge")
            status = badge_elem.get_text(strip=True) if badge_elem else "READ"
            
            emails.append({
                "subject": subject,
                "sender": sender,
                "time": time,
                "preview": preview,
                "body_text": body_text,
                "link": link,
                "status": status
            })
        except Exception as e:
            print(f"[WARNING] Failed to parse email card: {e}")
            continue
    
    return emails


def clean_emails_from_raw_data(raw_emails: list[dict]) -> list[dict]:
    """
    从原始 Graph API 数据中提取并清洗邮件信息
    
    Args:
        raw_emails: Graph API 返回的原始邮件数据
        
    Returns:
        清洗后的邮件列表
    """
    cleaned = []
    
    for email in raw_emails:
        try:
            subject = email.get("subject") or "(no subject)"
            sender_info = email.get("from", {}).get("emailAddress", {})
            sender = sender_info.get("name") or sender_info.get("address") or "Unknown"
            time = email.get("receivedDateTime", "")
            preview = email.get("bodyPreview", "")
            link = email.get("webLink", "#")
            is_read = email.get("isRead", False)
            status = "READ" if is_read else "UNREAD"
            body = email.get("body", {})
            body_content = body.get("content", "") if isinstance(body, dict) else ""
            body_type = (body.get("contentType") or "").lower() if isinstance(body, dict) else ""
            body_text = ""
            body_html = ""
            if body_type == "html":
                body_html = body_content
                body_text = BeautifulSoup(body_content, "html.parser").get_text("\n", strip=True)
            elif body_content:
                body_text = body_content
            
            cleaned.append({
                "subject": subject,
                "sender": sender,
                "time": time,
                "preview": preview,
                "body_text": body_text,
                "body_html": body_html,
                "link": link,
                "status": status
            })
        except Exception as e:
            print(f"[WARNING] Failed to clean email: {e}")
            continue
    
    return cleaned


def save_to_json(emails: list[dict], output_path: Path) -> None:
    """
    保存邮件数据到 JSON 文件
    
    Args:
        emails: 邮件列表
        output_path: 输出文件路径
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(emails, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def main():
    """
    主函数：解析最新的 HTML 文件并保存为 JSON
    """
    import datetime as dt
    
    today = dt.datetime.now().strftime("%Y%m%d")
    html_path = Path("output") / f"digest_{today}.html"
    json_path = Path("output") / f"emails_{today}.json"
    
    if not html_path.exists():
        print(f"[ERROR] HTML file not found: {html_path}")
        print("Please run Engine.py first to generate the HTML file.")
        return
    
    print(f"[INFO] Parsing HTML: {html_path}")
    emails = parse_html_to_json(html_path)
    
    print(f"[INFO] Extracted {len(emails)} emails")
    save_to_json(emails, json_path)
    
    print(f"[SUCCESS] Saved to: {json_path.resolve()}")


if __name__ == "__main__":
    main()
