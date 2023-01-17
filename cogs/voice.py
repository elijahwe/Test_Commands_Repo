import youtube_dl
from discord import app_commands
import discord
from discord.ext import commands
import discord.ui
import asyncio

import cogs.shared


HD1_CHANNEL_ID = 1045495007978721372
HD2_CHANNEL_ID = 1045495028241412106
HD1_VC_ID = 1046916768825884772
HD2_VC_ID = 1046916801017151488
DEVSERVER_ID = 925178872373321789

HD1_WEBSTREAM_URL = "http://173.193.205.96:7430/stream"
HD2_WEBSTREAM_URL = "http://173.193.205.96:7447/stream"


youtube_dl.utils.bug_reports_message = lambda: ''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ffmpeg_options = {
    'options': '-vn',
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class YTDLSource(discord.PCMVolumeTransformer):
        def __init__(self, source, *, data, volume=0.5):
            super().__init__(source, volume)

            self.data = data

            self.title = data.get('title')
            self.url = data.get('url')

        @classmethod
        async def from_url(cls, url, *, loop=None, stream=False):
            loop = loop or asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

            if 'entries' in data:
                # take first item from a playlist
                data = data['entries'][0]

            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if len(self.bot.voice_clients) > 0:
            if self.bot.voice_clients[0].channel.id == before.channel.id and len(before.channel.members) == 1:
                if before.channel.id == HD1_VC_ID:
                    hd1_textchannel = self.bot.get_channel(HD1_CHANNEL_ID)
                    async with hd1_textchannel.typing():
                        await hd1_textchannel.send("All users have left the voice channel, disconnecting")
                        await self.bot.voice_clients[0].disconnect()
                if before.channel.id == self.HD2_VC_ID:
                    hd2_textchannel = self.bot.get_channel(HD2_CHANNEL_ID)
                    async with hd2_textchannel.typing():
                        await hd2_textchannel.send("All users have left the voice channel, disconnecting")
                        await self.bot.voice_clients[0].disconnect()

    @commands.hybrid_command(name="join", brief="Join a voice channel")
    async def join(self, ctx: commands.Context, *, voicechannel: discord.VoiceChannel = None):
        channel: discord.VoiceChannel = None

        if voicechannel:
            channel = voicechannel
        elif ctx.channel.id == HD1_CHANNEL_ID:
            channel = self.bot.get_channel(HD1_VC_ID)
        elif ctx.channel.id == HD2_CHANNEL_ID:
            channel = self.bot.get_channel(HD2_VC_ID)
        elif ctx.author.voice:
            channel = ctx.author.voice.channel
        else:
            await ctx.send("Please include which channel you'd like me to join or send this command in a dedicated channel")
            return

        if (channel):

            if ctx.voice_client is not None:
                await ctx.voice_client.disconnect()

            state = await channel.connect()

            if state:
                if channel.id == HD1_VC_ID:
                    async with ctx.typing():
                        player = await self.YTDLSource.from_url(HD1_WEBSTREAM_URL, loop=self.bot.loop, stream=True)
                        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                        transbug = None
                        emojis = self.bot.get_guild(DEVSERVER_ID).emojis
                        for emoji in emojis:
                            if emoji.name == "transbug":
                                transbug = emoji
                        await ctx.send(f'Playing HD-1 in VC, come join! {transbug if transbug else ""}')
                elif channel.id == HD2_VC_ID:
                    async with ctx.typing():
                        player = await self.YTDLSource.from_url(HD2_WEBSTREAM_URL, loop=self.bot.loop, stream=True)
                        ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
                        transbug = None
                        emojis = self.bot.get_guild(DEVSERVER_ID).emojis
                        for emoji in emojis:
                            if emoji.name == "transbug":
                                transbug = emoji
                        await ctx.send(f'Playing HD-2 in VC, come join! {transbug if transbug else ""}')

    @commands.hybrid_command(name="leave", brief="Leave the current voice channel")
    @commands.has_permissions(administrator = True)
    @app_commands.default_permissions(administrator=True)
    async def stop(self, ctx: commands.Context):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnecting from voice")

    @commands.command(name="stream", brief="Stream to voice from a url")
    async def stream(self, ctx: commands.Context, *, url: str):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await self.YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

    @stream.before_invoke
    async def ensure_voice(self, ctx: commands.Context):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


async def setup(bot):
    await bot.add_cog(Voice(bot))