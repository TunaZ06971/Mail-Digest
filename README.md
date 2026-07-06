# Mail Digest

Mail Digest is a Python pipeline built in late 2025 to reduce daily Outlook inbox overload. It fetches recent Outlook messages through Microsoft Graph, cleans and enriches the email content, summarizes each message with the DeepSeek API, generates Markdown/HTML digest files, and sends the final HTML summary to a Google email address.

## Features

- Authenticates to Microsoft Graph with MSAL device-code login.
- Reads recent Outlook messages from the last 24 hours.
- Expands full email bodies and inline image attachments when available.
- Cleans Graph API responses into a lightweight JSON structure.
- Uses DeepSeek through the OpenAI-compatible SDK to produce bilingual summaries.
- Generates local Markdown and HTML digest artifacts.
- Sends the final digest email through Microsoft Graph `sendMail`.

## Data Pipeline

```text
Outlook mailbox
    |
    | 1. Fetch.py
    v
Microsoft Graph API
    |
    | 2. Enrich.py
    v
Raw messages with full bodies and inline images
    |
    | 3. Cleaner.py
    v
Cleaned JSON email records
    |
    | 4. AI_Summarizer.py
    v
DeepSeek bilingual summaries
    |
    | 5. Generate.py / Display.py
    v
Markdown and HTML digest files
    |
    | 6. Send.py
    v
Google email recipient
```

## Repository Structure

| File | Purpose |
| --- | --- |
| `Engine.py` | Main orchestration entry point for the full pipeline. |
| `Fetch.py` | Microsoft Graph authentication and email retrieval. |
| `Enrich.py` | Fetches full bodies and inline attachments for messages. |
| `Cleaner.py` | Converts raw Graph message payloads into clean JSON records. |
| `AI_Summarizer.py` | Calls DeepSeek and parses bilingual summary output. |
| `Generate.py` | Generates final Markdown and HTML summary files. |
| `Display.py` | Generates an intermediate HTML digest of raw emails. |
| `Send.py` | Sends the final HTML digest email through Microsoft Graph. |
| `requirements.txt` | Python dependencies. |
| `.env.example` | Template for local environment variables. |

Generated runtime files are intentionally ignored by Git:

- `.env`
- `.token_cache.bin`
- `output/`
- `Output/`
- `Stage_1/`
- `__pycache__/`

These files can contain API credentials, OAuth tokens, personal email content, or generated digest outputs.

## Prerequisites

- Python 3.11 or newer
- A Microsoft Azure app registration for Microsoft Graph
- A DeepSeek API key
- A Google email address to receive the digest

## Microsoft Graph Setup

1. Go to the Azure portal and create an app registration.
2. Copy the application client ID into `AZURE_CLIENT_ID`.
3. Configure the app as a public client so device-code authentication can be used.
4. Add delegated Microsoft Graph permissions:
   - `User.Read`
   - `Mail.Read`
   - `Mail.Send`
5. Grant consent if your tenant requires admin approval.
6. Use `common` for `AZURE_TENANT_ID` if you want the app to support device login across Microsoft accounts, or use your tenant ID for a single tenant.

The first run will print a device-code login message. Open the displayed Microsoft login URL, enter the code, and approve the requested permissions. A local `.token_cache.bin` file will be created after successful login.

## DeepSeek Setup

1. Create a DeepSeek API key.
2. Put the key in `DEEPSEEK_API_KEY`.
3. Keep `DEEPSEEK_MODEL=deepseek-chat` unless you want to use another compatible model.

The project uses the OpenAI Python SDK with DeepSeek's OpenAI-compatible base URL.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your local credentials:

```bash
AZURE_CLIENT_ID=your_azure_app_client_id
AZURE_TENANT_ID=common
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_MODEL=deepseek-chat
SUMMARY_TO=your_google_email@example.com
```

## Usage

Run the full pipeline:

```bash
python Engine.py
```

The script will:

1. Authenticate with Microsoft Graph.
2. Fetch Outlook emails from the previous 24 hours.
3. Enrich messages with full body content and inline images.
4. Save cleaned email data locally.
5. Generate DeepSeek summaries in Chinese and English.
6. Write digest files to local output directories.
7. Send the HTML digest to `SUMMARY_TO`.

## Output Files

The pipeline creates local runtime artifacts:

| Directory | Content |
| --- | --- |
| `Stage_1/` | Intermediate raw HTML digest. |
| `output/` | Cleaned JSON records and some generated summaries. |
| `Output/` | Final Markdown and HTML summary files. |

These outputs are not committed because they may include private email content.

## Security Notes

- Do not commit `.env`.
- Do not commit `.token_cache.bin`.
- Do not commit generated email JSON/HTML/Markdown outputs.
- Rotate any API key or OAuth token that may have been shared outside your machine.
- Before publishing, run a local scan for common secret patterns.

Example scan:

```bash
rg -n -uu --hidden --glob '!/.git/**' --glob '!.env' \
  'api[_-]?key|secret|token|password|sk-[A-Za-z0-9_-]{20,}'
```

## Development Notes

The project is intentionally script-based rather than packaged as a service. `Engine.py` is the normal entry point, while individual modules can be run during debugging when you want to inspect one step of the pipeline.
