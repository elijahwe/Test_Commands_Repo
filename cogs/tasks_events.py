import discord
from discord.ext import commands, tasks
import requests as r

import cogs.shared

#SPINITRON_TOKEN_HD1 = os.getenv("SPINITRON_TOKEN_HD1")
SPINITRON_TOKEN_HD1 = 'IdFuj4fqOYRhcApoDvW3lGCM'
#SPINITRON_TOKEN_HD2 = os.getenv("SPINITRON_TOKEN_HD2")
SPINITRON_TOKEN_HD2 = 'KoUZtWZ0gFQVp0Ws0bGzaZxV'

headers_hd1 = {"Authorization": f"Bearer {SPINITRON_TOKEN_HD1}"}
headers_hd2 = {"Authorization": f"Bearer {SPINITRON_TOKEN_HD2}"}

current_listening_text: str = "WKNC"


class Tasks_Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @tasks.loop(seconds=60)
    async def changeStatus(self):
        global current_listening_text
        current_set = r.get("https://spinitron.com/api/playlists?count=1", headers=headers_hd1).json()["items"][0]
        listening_text: str
        if (str(current_set["persona_id"]) == cogs.shared.DJ_AV_HD1_NUM):
            listening_text = r.get("https://spinitron.com/api/shows?count=1", headers=headers_hd1).json()["items"][0]["category"]
        else:
            listening_text = r.get("https://spinitron.com/api/shows?count=1", headers=headers_hd1).json()["items"][0]["title"]

        if (current_listening_text != str(listening_text)):
            print("Updating status")
            current_listening_text = str(listening_text)
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=current_listening_text))
    
    @commands.Cog.listener()
    async def on_ready(self):
        """What the discord bot does upon connection to the server"""
        print(f"{self.bot.user.name} has connected to Discord!")
        self.changeStatus.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if 'roko\'s' in message.content:
            async with message.channel.typing():
                await message.reply("Your behavior has been noted")
        if 'pebus' in message.content:
            async with message.channel.typing():
                await message.channel.send("who said that")


async def setup(bot):
    await bot.add_cog(Tasks_Events(bot))