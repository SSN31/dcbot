# Zigmars Discord Bot

A minimal `discord.py` v2 replay bot. It stores human messages in a local JSONL file and posts one previously logged message when:

- someone mentions `zigmars` anywhere in their message (case-insensitive), or
- someone replies to one of the bot's messages.

Responses are selected randomly from unique messages and rate-limited to once every 0.1 seconds per channel. This bot does not generate AI responses.

## Requirements

- Python 3.10 or newer
- A Discord application with a bot user

## Setup

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create or select an application and add a Bot user.
2. On the Bot page, enable the **Message Content Intent** under Privileged Gateway Intents.
3. Use OAuth2 → URL Generator to invite the bot with the `bot` scope and the `Send Messages` permission.
4. Create a virtual environment and install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and set `DISCORD_TOKEN` to the bot token.

   ```powershell
   Copy-Item .env.example .env
   ```

   Keep `.env` private and never commit it. The application ID is not required by this code; it is only used when configuring or inviting the bot.

## Run locally

From this directory:

```powershell
python bot.py
```

The console logs startup, detected triggers, sent replays, and cooldowns. Edit `TRIGGER_NAME` or `COOLDOWN_SECONDS` in `bot.py` to customize behavior.

## Message log

Messages are appended to `message_log.jsonl` beside `bot.py`. The file is created automatically when the bot receives messages and is loaded again on restart. It contains message text, author, channel ID, and timestamp. Do not commit it if the messages are private.

For replay selection, repeated messages are deduplicated after case-folding and whitespace normalization. For example, `hi`, `HI`, and ` hi ` share one equally likely replay slot instead of becoming three separate entries.
