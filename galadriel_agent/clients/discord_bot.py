import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import discord
from discord.ext import commands
from rich.text import Text
from smolagents.agents import LogLevel

from galadriel_agent.clients.client import Client

@dataclass
class Message:
    """Data class to store message information"""

    content: str
    channel_id: int
    author: str
    message_id: int
    timestamp: datetime

    def to_dict(self) -> Dict:
        """Convert Message object to dictionary"""
        return {
            "content": self.content,
            "channel_id": self.channel_id,
            "author": self.author,
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
        }


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_command(self, ctx):
        """A simple ping command to test the bot"""
        await ctx.send("Pong! 🏓")

    @commands.command(name="hello")
    async def hello_command(self, ctx):
        """Greet the user"""
        await ctx.send(f"Hello {ctx.author.name}! 👋")


class DiscordClient(commands.Bot, Client):
    def __init__(self, guild_id: str, logger):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True

        super().__init__(command_prefix="!", intents=intents)
        self.message_queue = None
        self.guild_id = guild_id
        self.logger = logger

    async def on_ready(self):
        self.logger.log(Text(f"Bot connected as {self.user.name}"), level=LogLevel.INFO)

    async def setup_hook(self):
        # Register commands
        await self.add_cog(CommandsCog(self))

        # Sync with specific guild
        guild = discord.Object(id=int(self.guild_id))
        try:
            await self.tree.sync(guild=guild)
            # self.logger.log(Text(f"Connected to guild {self.guild_id}"), level=LogLevel.INFO)
        except discord.HTTPException:
            # self.logger.log(Text(f"Failed to sync commands to guild {self.guild_id}: {e}"), level=LogLevel.ERROR)
            pass

    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.user:
            return

        # Create Message object and add to queue
        msg = Message(
            content=message.content,
            channel_id=message.channel.id,
            author=message.author.name,
            message_id=message.id,
            timestamp=message.created_at,
        )
        await self.message_queue.put(msg.to_dict())
        # self.logger.log(Text(f"Added message to queue: {msg}"), level=LogLevel.INFO)

    async def start(self, queue: asyncio.Queue) -> Message:
        self.message_queue = queue
        await super().start(os.getenv("DISCORD_TOKEN"))

    async def post_output(self, request, response: Dict, proof: str):
        channel = self.get_channel(response["channel_id"])
        if channel:
            await channel.send(response["agent_response"])
