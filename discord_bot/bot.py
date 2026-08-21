"""A small Discord bot that replays previously logged human messages."""

from __future__ import annotations

import logging
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path

import discord
from dotenv import load_dotenv


COOLDOWN_SECONDS = 0.1
TRIGGER_NAME = "zigmars"

MESSAGE_LOG_PATH = Path(__file__).with_name("message_log.jsonl")


def replay_key(content: str) -> str:
    """Normalize text so repeated/case-only variants share one replay slot."""
    return " ".join(content.casefold().split())


def load_token() -> str:
    """Load and validate the bot token from the local .env file."""
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is missing. Copy .env.example to .env and add your bot token."
        )
    return token


class ZigmarsBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        # Required to inspect message text and detect the "zigmars" trigger.
        intents.message_content = True
        super().__init__(intents=intents)
        # Dict keys deduplicate the replay pool; values preserve the text we send.
        self.logged_messages = self.load_logged_messages()
        self.last_response_by_channel: defaultdict[int, float] = defaultdict(
            lambda: float("-inf")
        )

    @staticmethod
    def load_logged_messages() -> dict[str, str]:
        """Load the replay pool from the local append-only JSONL log."""
        if not MESSAGE_LOG_PATH.exists():
            return {}

        messages: dict[str, str] = {}
        try:
            with MESSAGE_LOG_PATH.open("r", encoding="utf-8") as log_file:
                for line in log_file:
                    try:
                        content = json.loads(line).get("content", "")
                    except json.JSONDecodeError:
                        continue
                    if isinstance(content, str) and content.strip():
                        messages[replay_key(content)] = content.strip()
        except OSError:
            logging.exception("Could not read %s", MESSAGE_LOG_PATH)
        return messages

    def log_message(self, message: discord.Message) -> None:
        """Save a human message so it can be replayed later."""
        content = message.content.strip()
        if not content:
            return

        record = {
            "content": content,
            "author": str(message.author),
            "channel_id": message.channel.id,
            "timestamp": message.created_at.isoformat(),
        }
        try:
            with MESSAGE_LOG_PATH.open("a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.logged_messages[replay_key(content)] = content
        except OSError:
            logging.exception("Could not write to %s", MESSAGE_LOG_PATH)

    async def on_ready(self) -> None:
        logging.info("Logged in as %s (ID: %s)", self.user, self.user.id)

    async def message_replies_to_bot(self, message: discord.Message) -> bool:
        """Return whether a message replies to one of this bot's messages."""
        reference = message.reference
        if reference is None or reference.message_id is None:
            return False

        referenced = reference.resolved
        if referenced is None:
            try:
                referenced = await message.channel.fetch_message(reference.message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return False

        return isinstance(referenced, discord.Message) and referenced.author == self.user

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        mentions_name = TRIGGER_NAME in message.content.casefold()
        replies_to_bot = await self.message_replies_to_bot(message)
        trigger_fired = mentions_name or replies_to_bot

        if trigger_fired:
            now = time.monotonic()
            channel_id = message.channel.id
            elapsed = now - self.last_response_by_channel[channel_id]
            if elapsed < COOLDOWN_SECONDS:
                logging.info(
                    "Trigger ignored in channel %s (cooldown: %.1fs remaining)",
                    channel_id,
                    COOLDOWN_SECONDS - elapsed,
                )
            elif self.logged_messages:
                # Choose uniformly from unique normalized messages. Repeating
                # "hi" 100 times therefore does not make "hi" 100x likelier.
                reply = random.choice(list(self.logged_messages.values()))
                self.last_response_by_channel[channel_id] = now
                logging.info(
                    "Replay trigger in channel %s from %s; sending: %r",
                    channel_id,
                    message.author,
                    reply,
                )
                await message.channel.send(reply)
            else:
                logging.info("Trigger fired, but the replay log is empty")

        self.log_message(message)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = ZigmarsBot()
    bot.run(load_token(), log_handler=None)


if __name__ == "__main__":
    main()
