from collections import Counter
from datetime import datetime, timedelta
from dateutil import parser, tz
import discord
from discord import Embed
from discord_argparse import ArgumentConverter
from discord_argparse.argparse import OptionalArgument
from discord.ext import commands
import discord.ui
import discogs_client
from enum import Enum
import random
import re
import requests as r
import os
import urllib.parse

import cogs.shared

LOCAL_TIMEZONE = os.getenv("LOCAL_TIMEZONE")
#DISCOGS_TOKEN = os.getenv("DISCOGS_TOKEN")
DISCOGS_TOKEN = 'SMRGoeMDFazclBymteBYsaCmJyZmEtZQNBwhkFAg' #maddie account
#SPINITRON_TOKEN_HD1 = os.getenv("SPINITRON_TOKEN_HD1")
SPINITRON_TOKEN_HD1 = 'IdFuj4fqOYRhcApoDvW3lGCM'
#SPINITRON_TOKEN_HD2 = os.getenv("SPINITRON_TOKEN_HD2")
SPINITRON_TOKEN_HD2 = 'KoUZtWZ0gFQVp0Ws0bGzaZxV'
#HD1_CHANNEL_ID = os.getenv("HD1_CHANNEL_ID")
HD1_CHANNEL_ID = 1045495007978721372
#HD2_CHANNEL_ID = os.getenv("HD2_CHANNEL_ID")
HD2_CHANNEL_ID = 1045495028241412106
#DEVSERVER_ID = os.getenv("DEVSERVER_ID")
DEVSERVER_ID = 925178872373321789

discogs = discogs_client.Client("WKNC-Bot/0.1", user_token=DISCOGS_TOKEN)
headers_hd1 = {"Authorization": f"Bearer {SPINITRON_TOKEN_HD1}"}
headers_hd2 = {"Authorization": f"Bearer {SPINITRON_TOKEN_HD2}"}


class ShowID(Enum):
    CHAINSAW = 177577
    DAYTIME = 177706
    UNDERGROUND = 177709
    AFTERHOURS = 107806
    LOCAL_LUNCH = 35580
    LOCAL_RAP_LUNCH = 13325
    ALL = ""


def my_parser(date: str, space: bool = True, ampm: bool = True) -> str:
    """Takes a UTC date string and returns the 12-hour representation
    Args:
        date (str): UTC date string in the format '1970-01-01T00:00:00+0000'
    Returns:
        str: A string in the format '12 a.m'
    """
    spacechar = ""
    if space:
        spacechar = " "
    dt = parser.parse(date)
    dt = dt.replace(tzinfo=tz.UTC).astimezone(tz.gettz(LOCAL_TIMEZONE)).hour
    ampm_str = ""
    if (ampm):
        if (dt < 12):
            ampm_str = "am"
        else:
            ampm_str = "pm"
    return "{}{}{}".format(dt % 12 or 12, spacechar, ampm_str)

def is_av(show: dict, channel: int = 1) -> bool:
    """Takes a link to a DJ's spinitron page and returns true if the DJ has been designated
        as "Automated"
    Args:
        show (dict): A dict representing a single 'show' as taken from the Spinitron API
        channel (int): An int representing a WKNC channel: 1 for HD-1, 2 for HD-2
    Returns:
        bool: True, if the DJ ID has been designated as "Automated"
    """
    if channel == 1:
        return cogs.shared.DJ_AV_HD1_NUM in show["_links"]["personas"][0]["href"]
    if channel == 2:
        return cogs.shared.DJ_AV_HD2_NUM in show["_links"]["personas"][0]["href"]

    return False

def is_in_past(date: str) -> bool:
    """Returns true if the provided UTC datestring has occured in the past
    Args:
        date (str): UTC date string in the format '1970-01-01T00:00:00+0000'
    Returns:
        bool: True, if the date is in the past. Otherwise false
    """
    date = parser.parse(date)
    return datetime.utcnow().replace(tzinfo=tz.UTC) > date.replace(tzinfo=tz.UTC)

def is_today(date: str) -> bool:
    """Returns true if the Provided UTC datestring has or will occur today
    Args:
        date (str): UTC date string in the format '1970-01-01T00:00:00+0000'
    Returns:
        bool: True, if the date is before or at UTC midnight
    """
    indate = parser.parse(date)
    nextmidnight = (
        datetime.now(tz.gettz(LOCAL_TIMEZONE))
        .replace(hour=23, minute=59, second=59, microsecond=59)
        .astimezone(tz.UTC)
    )
    lastmidnight = (
        datetime.now(tz.gettz(LOCAL_TIMEZONE))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(tz.UTC)
    )
    return indate < nextmidnight and lastmidnight <= indate

def is_yesterday(date: str) -> bool:
    """Returns true if the Provided UTC datestring occured yesterday
    Args:
        date (str): UTC date string in the format '1970-01-01T00:00:00+0000'
    Returns:
        bool: True, if the date is before or at UTC midnight
    """
    indate = parser.parse(date) + timedelta(days = 1)
    nextmidnight = (
        datetime.now(tz.gettz(LOCAL_TIMEZONE))
        .replace(hour=23, minute=59, second=59, microsecond=59)
        .astimezone(tz.UTC)
    )
    lastmidnight = (
        datetime.now(tz.gettz(LOCAL_TIMEZONE))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .astimezone(tz.UTC)
    )
    return indate < nextmidnight and lastmidnight <= indate

def next_show(upcoming_shows: list, channel: int = 1) -> dict:
    """Takes a list of shows (ascending) and returns the next scheduled show that is not automated
    Args:
        upcoming_shows (list): A list of dicts, each representing a show
        channel (int): An int representing a WKNC channel: 1 for HD-1, 2 for HD-2
    Returns:
        dict: The next show
    """
    return next(
        (show for show in upcoming_shows if not is_av(show, channel) and not is_in_past(show["start"])),
        None,
    )

def to_enum(argument: str) -> str:
    return argument.upper().replace(" ", "_")

def to_lower(argument: str) -> str:
    return argument.lower()

def get_dj_name(spinitron_id: str, headers) -> str:
    dj_name = r.get(
        "https://spinitron.com/api/personas/{}".format(spinitron_id.replace(" ", "%20")),
        headers=headers,
    ).json()["name"]

    return dj_name

def get_album_art(last_spin):
    img_art: str = None
    if last_spin["image"]:
        img_art = last_spin["image"]
    else:
        d_search = discogs.search(
            "{} - {}".format(last_spin["artist"], last_spin["song"]), type="release"
        )
        if len(d_search) > 0:
            img_art = d_search[0].thumb
    return img_art


summary_param_converter = ArgumentConverter(
    show=OptionalArgument(
        to_enum, doc="The show to summarize, defaults to all spins", default="ALL"
    ),
    days=OptionalArgument(
        int, doc="Look at all spins starting # days ago, defaults to 7", default=7
    ),
    top=OptionalArgument(int, doc="The top # spins, defaults to 10", default=10),
    by=OptionalArgument(to_lower, doc="By song or artist, defaults to song", default="song"),
)


class Broadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="listeners", brief="The current number of webstream listeners")
    async def listeners(self, ctx: commands.Context):
        async with ctx.typing():
            if (ctx.channel.id == HD1_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('listeners1'))
            elif (ctx.channel.id == HD2_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('listeners2'))
            else:
                await ctx.send("Please either send this command in a dedicated channel or use the listeners1 or listeners2 commands")

    @commands.hybrid_command(name="listeners1", brief="The current number of listeners for the HD-1 webstream")
    async def listeners_hd1(self, ctx: commands.Context):
        async with ctx.typing():
            listenercount: int = r.get("http://173.193.205.96:2199/rpc/wknchd1/streaminfo.get").json()["data"][0]["listeners"]
            await ctx.send(f"There {'are' if listenercount != 1 else 'is'} currently {listenercount} listener{'s' if listenercount != 1 else ''} on the HD-1 webstream!")

    @commands.hybrid_command(name="listeners2", brief="The current number of listeners for the HD-2 webstream")
    async def listeners_hd2(self, ctx: commands.Context):
        async with ctx.typing():
            listenercount = r.get("http://173.193.205.96:2199/rpc/wknchd2/streaminfo.get").json()["data"][0]["listeners"]
            await ctx.send(f"There {'are' if listenercount != 1 else 'is'} currently {listenercount} listener{'s' if listenercount != 1 else ''} on the HD-2 webstream!")


    @commands.hybrid_command(name="np", brief="The currently playing song")
    async def now_playing(self, ctx: commands.Context):
        async with ctx.typing():
            if (ctx.channel.id == HD1_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('np1'))
            elif (ctx.channel.id == HD2_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('np2'))
            else:
                await ctx.send("Please either send this command in a dedicated channel or use the np1 or np2 commands")

    @commands.hybrid_command(name="np1", brief="The song currently playing on HD-1")
    async def now_playing_hd1(self, ctx: commands.Context):
        async with ctx.typing():
            embed = await self.now_playing_query(headers_hd1, cogs.shared.SPINITRON_URL_CHANNEL_HD1)
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="np2", brief="The song currently playing on HD-2")
    async def now_playing_hd2(self, ctx: commands.Context):
        async with ctx.typing():
            embed = await self.now_playing_query(headers_hd2, cogs.shared.SPINITRON_URL_CHANNEL_HD2)
            await ctx.send(embed=embed)

    async def now_playing_query(self, headers, channel):
        last_spin = r.get("https://spinitron.com/api/spins?count=1", headers=headers).json()["items"][0]
        spinitron_id = r.get(
            "https://spinitron.com/api/playlists/{}".format(last_spin["playlist_id"]),
            headers=headers,
        ).json()["persona_id"]

        img_art = get_album_art(last_spin)

        embed = Embed(
            title=last_spin["song"], description=last_spin["artist"], color=cogs.shared.EMBED_COLOR#, url = "https://spinitron.com"
        ).set_author(
            name=get_dj_name(str(spinitron_id), headers), url=f"https://spinitron.com/{channel}/dj/{spinitron_id}"
        )
        if img_art:
            embed.set_image(url=img_art)
        return embed


    @commands.hybrid_command(name="lp", brief="The last played song")
    async def last_played(self, ctx: commands.Context):
        async with ctx.typing():
            if (ctx.channel.id == HD1_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('lp1'))
            elif (ctx.channel.id == HD2_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('lp2'))
            else:
                await ctx.send("Please either send this command in a dedicated channel or use the lp1 or lp2 commands")

    @commands.hybrid_command(name="lp1", brief="The last played song on HD-1")
    async def last_played_hd1(self, ctx: commands.Context):
        async with ctx.typing():
            embed = await self.last_played_query(headers_hd1, cogs.shared.SPINITRON_URL_CHANNEL_HD1)
            await ctx.send("The previous song on HD-1 was:", embed=embed)

    @commands.hybrid_command(name="lp2", brief="The last played song on HD-2")
    async def last_played_hd2(self, ctx: commands.Context):
        async with ctx.typing():
            embed = await self.last_played_query(headers_hd2, cogs.shared.SPINITRON_URL_CHANNEL_HD2)
            await ctx.send("The previous song on HD-2 was:", embed=embed)

    async def last_played_query(self, headers, channel):
        last_spin = r.get("https://spinitron.com/api/spins?count=2", headers=headers).json()["items"][1]
        spinitron_id = r.get(
            "https://spinitron.com/api/playlists/{}".format(last_spin["playlist_id"]),
            headers=headers,
        ).json()["persona_id"]

        img_art = get_album_art(last_spin)

        embed = Embed(
            title=last_spin["song"], description=last_spin["artist"], color=cogs.shared.EMBED_COLOR
        ).set_author(
            name=get_dj_name(str(spinitron_id), headers), url=f"https://spinitron.com/{channel}/dj/{spinitron_id}"
        )
        if img_art:
            embed.set_image(url=img_art)

        return embed


    @commands.hybrid_command(name="lps", brief="List of the last played songs")
    async def last_played_songs(self, ctx: commands.Context):
        async with ctx.typing():
            if (ctx.channel.id == HD1_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('lps1'))
            elif (ctx.channel.id == HD2_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('lps2'))
            else:
                await ctx.send("Please either send this command in a dedicated channel or use the lps1 or lps2 commands")

    @commands.hybrid_command(name="lps1", brief="List of the last played songs on HD-1")
    async def last_played_songs_hd1(self, ctx: commands.Context):
        async with ctx.typing():
            message = await ctx.send(":thinking: thinking...")
            embed = self.last_played_songs_query(headers_hd1, cogs.shared.SPINITRON_URL_CHANNEL_HD1, 1)
            await message.edit(content=f"The last played songs on HD-1:", embed=embed, view=self.LPS_Button(outer_instance=self, headers=headers_hd1, channel=cogs.shared.SPINITRON_URL_CHANNEL_HD1, message=message))

    @commands.hybrid_command(name="lps2", brief="List of the last played songs on HD-2")
    async def last_played_songs_hd2(self, ctx: commands.Context):
        async with ctx.typing():
            message = await ctx.send(":thinking: thinking...")
            embed = self.last_played_songs_query(headers_hd2, cogs.shared.SPINITRON_URL_CHANNEL_HD2, 1)
            await message.edit(content=f"The last played songs on HD-2:", embed=embed, view=self.LPS_Button(outer_instance=self, headers=headers_hd2, channel=cogs.shared.SPINITRON_URL_CHANNEL_HD2, message=message))

    class LPS_Button(discord.ui.View):
        def __init__(self, outer_instance, headers, channel, message):
            super().__init__()
            self.outer_instance = outer_instance
            self.headers = headers
            self.channel = channel
            self.page = 1
            self.timeout=cogs.shared.BUTTON_TIMEOUT
            self.message = message

        async def on_timeout(self) -> None:
            for button in self.children:
                button.disabled = True
            await self.message.edit(view=self)
            #await interaction.edit_original_response(view=self)

        @discord.ui.button(label='<', disabled = True)
        async def down_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page > 1:
                self.page -= 1
                if (self.page <= 1):
                    button.disabled = True

            thinkingEmbed = Embed(description = ":thinking: thinking...")
            await interaction.response.defer()
            await interaction.edit_original_response(view=self, embed=thinkingEmbed)
            embed = self.last_played_songs_query(headers=self.headers, channel=self.channel, page=self.page)
            await interaction.edit_original_response(view=self, embed=embed)

        @discord.ui.button(label='>')
        async def up_page(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.page += 1
            if (self.page > 1):
                self.children[0].disabled = False


            if (self.page > cogs.shared.LPS_RAND_THRESH and random.randint(1,cogs.shared.LPS_RAND_POOL) == 1):
                try:
                    thinkMessage = random.choice(self.bot.get_guild(DEVSERVER_ID).emojis)
                except:
                    thinkMessage = ":thinking: thinking..."
            else:
                thinkMessage = ":thinking: thinking..."
            thinkingEmbed = Embed(description = thinkMessage)
            await interaction.response.defer()
            await interaction.edit_original_response(view=self, embed=thinkingEmbed)
            embed = self.outer_instance.last_played_songs_query(headers=self.headers, channel=self.channel, page=self.page)
            await interaction.edit_original_response(view=self, embed=embed)

    def last_played_songs_query(self, headers, channel, page):
        last_spins = r.get(f"https://spinitron.com/api/spins?count=10&page={page}", headers=headers).json()["items"]

        last_played_list = []
        count = 0
        for i in last_spins:
            spinitron_id = r.get(
                "https://spinitron.com/api/playlists/{}".format(i["playlist_id"]),
                headers=headers,
            ).json()["persona_id"]
            djname = get_dj_name(str(spinitron_id), headers)
            djlink = f"https://spinitron.com/{channel}/dj/{spinitron_id}"
            nowtext = ""
            if (count == 0 and page == 1):
                nowtext = " (playing now)"

            utcstring = i["start"]
            starttime =  parser.parse(i["start"]).astimezone(tz.gettz(LOCAL_TIMEZONE))
            ltstring = starttime.isoformat()
            hour = ltstring[11:13]
            minute = utcstring[14:16]
            if (int(hour) >= 13):
                hour = str(int(hour) - 12)

            last_played_list.append(f"`{hour}:{minute}`  {i['song']} - {i['artist']} | [{djname}]({djlink})" + nowtext + "\n")
            count += 1

        message = "".join(last_played_list)

        embed = Embed(
            title = f"Page {page}", description=message, color=cogs.shared.EMBED_COLOR
        )

        return embed


    @commands.hybrid_command(name="schedule", brief="The list of scheduled shows for the day")
    async def schedule(self, ctx: commands.Context, *, day: str = None):
        async with ctx.typing():
            if (ctx.channel.id == HD1_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('schedule1'), day=day)
            elif (ctx.channel.id == HD2_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('schedule2'), day=day)
            else:
                await ctx.send("Please either send this command in a dedicated channel or use the schedule1 or schedule2 commands")

    @commands.hybrid_command(name="schedule1", brief="The list of scheduled shows for the day on HD-1")
    async def schedule_hd1(self, ctx: commands.Context, *, day: str = None):
        async with ctx.typing():
            await self.get_schedule(ctx, day, 1)

    @commands.hybrid_command(name="schedule2", brief="The list of scheduled shows for the day on HD-2")
    async def schedule_hd2(self, ctx: commands.Context, *, day: str = None):
        async with ctx.typing():
            await self.get_schedule(ctx, day, 2)

    async def get_schedule(self, ctx: commands.Context, day: str, channelnum: int):
        embed: Embed

        if day:
            daylower = day.lower()

            date: datetime.date = None

            try:
                date = datetime.strptime(daylower,"%m/%d/%y")
                if date <= datetime.today():
                    await ctx.send("Please enter only future dates")
                    return
            except:
                if (daylower in cogs.shared.VALID_WEEKDAYS):
                    weekday: int
                    if re.search("^m", daylower):
                        weekday = 0
                    elif re.search("^tu", daylower):
                        weekday = 1
                    elif re.search("^w", daylower):
                        weekday = 2
                    elif re.search("^th", daylower):
                        weekday = 3
                    elif re.search("^f", daylower):
                        weekday = 4
                    elif re.search("^sa", daylower):
                        weekday = 5
                    elif re.search("^su", daylower):
                        weekday = 6
                    else:
                        await ctx.send("something went wrong that shouldn't have gone wrong lol can you @elijah and let me know")

                    daysuntil = (weekday - datetime.today().weekday() + 7) % 7
                    if daysuntil == 0:
                        daysuntil = 7

                    date = datetime.today() + timedelta(days = daysuntil)

                else:
                    await ctx.send("Please enter either a day of the week or a date in the format of MM/DD/YY")
                    return

            embed = self.day_show_schedule(channelnum, date)
            if (embed):
                await ctx.send(embed = embed)
            else:
                await ctx.send("It doesn't look like there are any shows that day")

        else:
            embed = self.upcoming_show_schedule(channelnum)
            if (embed):
                await ctx.send(embed = embed)
            else:
                await ctx.send("No more shows today! Check back tomorrow")

    def day_show_schedule(self, channel: int, date: datetime.date):
        if channel == 2:
            chheaders = headers_hd2
            channelstr = cogs.shared.SPINITRON_URL_CHANNEL_HD2
        else:
            chheaders = headers_hd1
            channelstr = cogs.shared.SPINITRON_URL_CHANNEL_HD1


        starttime = datetime.combine(date, datetime.min.time())
        endtime = starttime.replace(hour = 23, minute = 59, second = 59)

        starttimestr = urllib.parse.quote(starttime.isoformat())
        endtimestr = urllib.parse.quote(endtime.isoformat())


        upcoming_shows = r.get(
            "https://spinitron.com/api/shows?count=24&start={}&end={}".format(starttimestr, endtimestr),
            headers=chheaders,
        ).json()["items"]

        embed = Embed()

        schedule = []
        for show in upcoming_shows:
            showtime = show["start"]
            if not is_av(show, channel):
                persona_data = r.get(show["_links"]["personas"][0]["href"], headers=chheaders).json()
                show_persona = persona_data["name"]
                persona_id = persona_data["id"]
                schedule.append(
                    "`{}-{}`  {}: [{}]({})".format(my_parser(show["start"], False, False), my_parser(show["end"], False, True), show["title"], show_persona, f"https://spinitron.com/{channelstr}/dj/{persona_id}")
                )
        if schedule:
            embed.title = f"{cogs.shared.WEEKDAY_LIST[date.weekday()]}'s Schedule (HD-{channel})"
            embed.description = "\n".join(schedule)
            embed.color = cogs.shared.EMBED_COLOR

        return embed

    def upcoming_show_schedule(self, channel: int = 1) -> str:
        """Takes a list of shows and returns the ones that are both hosted by a human and occur in the future
        Args:
            upcoming_shows (list): A list of shows, taken from the Spinitron API
            channel (int): An int representing a WKNC channel: 1 for HD-1, 2 for HD-2
        Returns:
            str: A formatted string of upcoming shows or a message indicating there are no more shows
        """
        if channel == 2:
            chheaders = headers_hd2
            channelstr = cogs.shared.SPINITRON_URL_CHANNEL_HD2
        else:
            chheaders = headers_hd1
            channelstr = cogs.shared.SPINITRON_URL_CHANNEL_HD1

        upcoming_shows = r.get(
            "https://spinitron.com/api/shows",
            headers=chheaders,
        ).json()["items"]

        embed = Embed()

        schedule = []
        for show in upcoming_shows:
            if not is_today(show["start"]):
                break
            if not is_av(show, channel):
                persona_data = r.get(show["_links"]["personas"][0]["href"], headers=chheaders).json()
                show_persona = persona_data["name"]
                persona_id = persona_data["id"]
                schedule.append(
                    "`{}-{}`  {}: [{}]({})".format(my_parser(show["start"], False, False), my_parser(show["end"], False), show["title"], show_persona, f"https://spinitron.com/{channelstr}/dj/{persona_id}")
                )
        if schedule:
            embed.title = f"Today's Schedule (HD-{channel})"
            embed.description = "\n".join(schedule)
            embed.color = cogs.shared.EMBED_COLOR

        return embed


    @commands.hybrid_command(name="nextshow", brief="The next, non DJ AV show")
    async def next_up(self, ctx: commands.Context):
        async with ctx.typing():
            if (ctx.channel.id == HD1_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('nextshow1'))
            elif (ctx.channel.id == HD2_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('nextshow2'))
            else:
                await ctx.send("Please either send this command in a dedicated channel or use the nextshow1 or nextshow2 commands")

    @commands.hybrid_command(name="nextshow1", brief="The next, non DJ AV show on HD-1")
    async def next_up_hd1(self, ctx: commands.Context):
        async with ctx.typing():
            upcoming_shows = r.get(
                "https://spinitron.com/api/shows",
                headers=headers_hd1,
            ).json()["items"]
            next_dj_show = next_show(upcoming_shows, 1)
            response_message = "Coming up next is {} at {}".format(
                next_dj_show["title"], my_parser(next_dj_show["start"], True)
            )

            await ctx.send(response_message)

    @commands.hybrid_command(name="nextshow2", brief="The next, non DJ AV show on HD-2")
    async def next_up_hd2(self, ctx: commands.Context):
        async with ctx.typing():
            upcoming_shows = r.get(
                "https://spinitron.com/api/shows",
                headers=headers_hd2,
            ).json()["items"]
            next_dj_show = next_show(upcoming_shows, 2)
            response_message = "Coming up next is {} at {}".format(
                next_dj_show["title"], my_parser(next_dj_show["start"], True)
            )

            await ctx.send(response_message)


    @commands.hybrid_command(name="djset", brief="All songs played on the last, non DJ AV show")
    async def djset(self, ctx: commands.Context, *, djname: str = None):
        async with ctx.typing():
            if (ctx.channel.id == HD1_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('djset1'), djname=djname)
            elif (ctx.channel.id == HD2_CHANNEL_ID):
                await ctx.invoke(self.bot.get_command('djset2'), djname=djname)
            else:
                await ctx.send("Please either send this command in a dedicated channel or use the djset1 or djset2 commands")

    @commands.hybrid_command(name="djset1", brief="All songs played on the last, non DJ AV show on HD-1")
    async def djset_hd1(self, ctx: commands.Context, *, djname: str = None):
        async with ctx.typing():
            if not djname:
                embed = await self.last_set_query(ctx, headers_hd1, cogs.shared.SPINITRON_URL_CHANNEL_HD1, cogs.shared.DJ_AV_HD1_NUM)
            else:
                embed = await self.dj_last_set_query(ctx, headers_hd1, cogs.shared.SPINITRON_URL_CHANNEL_HD1, djname)

            if (embed):
                await ctx.send(embed=embed)

    @commands.hybrid_command(name="djset2", brief="All songs played on the last, non DJ AV show on HD-2")
    async def djset_hd2(self, ctx: commands.Context, *, djname: str = None):
        async with ctx.typing():
                if not djname:
                    embed = await self.last_set_query(ctx, headers_hd2, cogs.shared.SPINITRON_URL_CHANNEL_HD2, cogs.shared.DJ_AV_HD2_NUM)
                else:
                    embed = await self.dj_last_set_query(ctx, headers_hd2, cogs.shared.SPINITRON_URL_CHANNEL_HD2, djname)

                if (embed):
                    await ctx.send(embed=embed)

    async def last_set_query(self, ctx: commands.Context, headers, channel, av_num):
        last_playlists = r.get(f"https://spinitron.com/api/playlists?count={cogs.shared.LAST_SET_RANGE}", headers=headers).json()["items"]

        i = 0
        while (av_num in last_playlists[i]["_links"]["persona"]["href"] and i < cogs.shared.LAST_SET_RANGE - 1):
            i += 1

        if (i >= cogs.shared.LAST_SET_RANGE - 1):
            await ctx.send("No recent dj sets detected")
        else:
            lastset = last_playlists[i]
            return self.make_set_embed(lastset, headers, channel)

        return None

    async def dj_last_set_query(self, ctx: commands.Context, headers, channel, dj_name):
        if (channel == cogs.shared.SPINITRON_URL_CHANNEL_HD2):
            channelnum = 2
        else:
            channelnum = 1

        response = r.get(
            "https://spinitron.com/api/personas?name={}".format(dj_name.replace(" ", "%20")),
            headers=headers,
        ).json()["items"]

        response_message: str
        if not response:
            await ctx.send(f"Huh, I couldn't seem to find {dj_name} on HD{channelnum}. Are you sure that's the right DJ Name?")
        else:
            spinitron_id = response[0]["id"]

            last_playlists = r.get(f"https://spinitron.com/api/playlists?persona_id={spinitron_id}", headers=headers).json()["items"]

            if (last_playlists):
                return self.make_set_embed(last_playlists[0], headers, channel)

            await ctx.send(f"It doesn't look like {dj_name} has had any HD{channelnum} sets yet!")

        return None

    def make_set_embed(self, lastset, headers, channel):
        utcstring = lastset["start"]
        starttime =  parser.parse(lastset["start"]).astimezone(tz.gettz(LOCAL_TIMEZONE))
        ltstring = starttime.isoformat()
        timemessage = ""
        pm = False

        if is_today(utcstring):
            timemessage = "Today"
        elif is_yesterday(utcstring):
            timemessage = "Yesterday"
        else:
            month = ltstring[5:7]
            day = ltstring[8:10]

            if month[0] == '0':
                month = month[1:]

            if day[0] == '0':
                day = day[1:]

            timemessage = f"{month}/{day}"

        hour = ltstring[11:13]
        minute = utcstring[14:16]

        if (int(hour) >= 12):
            pm = True
            if (int(hour) >= 13):
                hour = str(int(hour) - 12)

        timemessage += f" at {hour}:{minute} "

        if (pm):
            timemessage += "pm"
        else:
            timemessage += "am"

        set_spin_list = []
        set_items = r.get(lastset["_links"]["spins"]["href"], headers=headers).json()["items"]

        moreitems = True
        j = 1;
        while (set_items):
            for i in set_items:
                utcstring = i["start"]
                starttime =  parser.parse(i["start"]).astimezone(tz.gettz(LOCAL_TIMEZONE))
                ltstring = starttime.isoformat()
                hour = ltstring[11:13]
                minute = utcstring[14:16]
                if (int(hour) >= 13):
                    hour = str(int(hour) - 12)
                set_spin_list.insert(0, f"`{hour}:{minute}`  {i['song']} - {i['artist']}" + "\n")

            j += 1
            if (j > cogs.shared.MAX_PAGES_FOR_DJSET):
                break
            set_items = r.get(lastset["_links"]["spins"]["href"]+f"&page={j}", headers=headers).json()["items"]


        set_spins_string = "".join(set_spin_list)

        message = timemessage + "\n\n" + set_spins_string# + "\n" + ctx.author.mention"""

        spinitron_id = lastset["persona_id"]

        #img_art = get_album_art(last_spin)
        img_art: str = None
        if lastset["image"]:
            img_art = lastset["image"]

        embed = Embed(
            title=lastset["title"], description=message, color=cogs.shared.EMBED_COLOR
        ).set_author(
            name=get_dj_name(str(spinitron_id), headers), url=f"https://spinitron.com/{channel}/dj/{spinitron_id}"
        )
        if img_art:
            embed.set_thumbnail(url=img_art)

        return embed


    @commands.hybrid_command(name="summary", brief="Gets a summary of the logged spins for the week")
    async def summary(self, ctx: commands.Context):
        if (ctx.channel.id == HD1_CHANNEL_ID):
            await ctx.invoke(self.bot.get_command('summary1'))
        elif (ctx.channel.id == HD2_CHANNEL_ID):
            await ctx.invoke(self.bot.get_command('summary2'))
        else:
            await ctx.send("Please either send this command in a dedicated channel or use the summary1 or summary2 commands")

    @commands.hybrid_command(name="summary1", brief="Gets a summary of the logged spins for the week on HD-1")
    async def summary_hd1(self, ctx: commands.Context, *, params: summary_param_converter = summary_param_converter.defaults()):
        days = params["days"]
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%x")
        show_id = ShowID[params["show"].replace(" ", "_").upper()]
        by = params["by"]

        if days > 30:
            await ctx.send(
                "For summaries more than 30 days please use https://spinitron.com/m/spin/chart"
            )
            return

        page = 1
        response = True
        song_dict = {}
        artist_dict = {}

        message = await ctx.send("Just a moment, let me get that for you...")

        while response:
            response = r.get(
                f"https://spinitron.com/api/spins?start={start_date}&count=200&page={page}&show_id={show_id.value}",
                headers=headers_hd1,
            ).json()["items"]
            print(page)
            for spin in response:
                key = "{} by {}".format(spin["song"], spin["artist"])
                artist = spin["artist"]
                if key not in song_dict:
                    song_dict[key] = 0
                    artist_dict[artist] = 0
                song_dict[key] += 1
                artist_dict[artist] += 1
            page += 1

        if by == "artist":
            counter = Counter(artist_dict).most_common(params["top"])
        else:
            counter = Counter(song_dict).most_common(params["top"])

        summary_list = []
        for key, value in counter:
            summary_list.append(f"    -{key} | {value} times")
        response_message = f"**Top {by}s of the past {days} days**\n" + "\n".join(summary_list)

        await message.edit(content=response_message)
        await ctx.send(ctx.author.mention)

    @commands.hybrid_command(name="summary2", brief="Gets a summary of the logged spins for the week on HD-2")
    async def summary_hd2(self, ctx: commands.Context, *, params: summary_param_converter = summary_param_converter.defaults()):
        days = params["days"]
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%x")
        show_id = ShowID[params["show"].replace(" ", "_").upper()]
        by = params["by"]

        if days > 30:
            await ctx.send(
                "For summaries more than 30 days please use https://spinitron.com/m/spin/chart"
            )
            return

        page = 1
        response = True
        song_dict = {}
        artist_dict = {}

        message = await ctx.send("Just a moment, let me get that for you...")

        while response:
            response = r.get(
                f"https://spinitron.com/api/spins?start={start_date}&count=200&page={page}&show_id={show_id.value}",
                headers=headers_hd2,
            ).json()["items"]
            print(page)
            for spin in response:
                key = "{} by {}".format(spin["song"], spin["artist"])
                artist = spin["artist"]
                if key not in song_dict:
                    song_dict[key] = 0
                    artist_dict[artist] = 0
                song_dict[key] += 1
                artist_dict[artist] += 1
            page += 1

        if by == "artist":
            counter = Counter(artist_dict).most_common(params["top"])
        else:
            counter = Counter(song_dict).most_common(params["top"])

        summary_list = []
        for key, value in counter:
            summary_list.append(f"    -{key} | {value} times")
        response_message = f"**Top {by}s of the past {days} days**\n" + "\n".join(summary_list)

        await message.edit(content=response_message)
        await ctx.send(ctx.author.mention)


async def setup(bot):
    await bot.add_cog(Broadcast(bot))
