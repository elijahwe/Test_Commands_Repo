from bs4 import BeautifulSoup
from datetime import datetime
from discord import Embed
from discord.ext import commands
import random
import requests as r

import cogs.shared


def month_string_to_datetime(month_string: str) -> datetime:
    # Get the current date
    now = datetime.now()

    # Convert the month string to a month number
    try:
        # Try parsing the month string as a full month name
        month_number = datetime.strptime(month_string, '%B').month
    except ValueError:
        # If that fails, try parsing the month string as a short month name
        month_number = datetime.strptime(month_string, '%b').month

    # If the month number is in the past, set the year to the next year
    if month_number < now.month:
        year = now.year + 1
    else:
        year = now.year

    # Set the day to the last day of the month
    first_day = datetime(year, month_number, 1)

    return first_day


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_command(name="about", brief="A little bit about me!")
    async def about(self, ctx: commands.Context):
        async with ctx.typing():
            await ctx.send(
                (
                    "2 weeks/bot/python. https://github.com/wdecicc/wknc-bot\n"
                    "I'm a bot meant to provide some integration with Spinitron! Use !help to find out more"
                )
            )
    

    @commands.hybrid_command(name="help", description="Shows all commands")
    async def help(self, ctx: commands.Context):
        async with ctx.typing():
            embed = self.help_query()
            await ctx.send(embed=embed)

    def help_query(self):
        embed = Embed(
            color=cogs.shared.EMBED_COLOR
        ).add_field(
            name = "HD-1 commands",
            value = """
    **djset** - All songs played on the last, non DJ AV show
    **lp** - The last played song
    **lps** - A list of the last played songs
    **nextshow** - The next, non DJ AV show
    **np** - The song currently playing
    **schedule** - The list of scheduled shows for the day
    **summary** - Gets a summary of the logged spins for the week
    """
        ).add_field(
            name = "HD-2 commands",
            value = """
    **djset2** - All songs played on the last, non DJ AV show
    **lp2** - The last played song
    **lps2** - A list of the last played songs
    **nextshow2** - The next, non DJ AV show
    **np2** - The song currently playing
    **schedule2** - The list of scheduled shows for the day
    **summary2** - Gets a summary of the logged spins for the week
    """
        ).add_field(
            name = "Bindings",
            value = """
    **bind** - Binds your DJ name to your Discord ID ex. !bind DJ Jazzy Jeff
    **bindings** - Shows the current Discord - Spinitron bindings
    **unbind** - Remove your bound DJ name
    **whoami** - Your associated DJ name and page
    **whois** - Someone else's associated DJ name and page. ex. !whois @Jeffrey
    """
        ).add_field(
            name = "Misc",
            value = """
    **about** - A little bit about me!
    **help** - Shows all commands
    """
        )

        return embed


    @commands.hybrid_command(name="report", brief="Sends the WKNC Track Report Form")
    async def report(self, ctx: commands.Context):
        await ctx.send("Heard a song with an expletive, an outdated promo or something that otherwise needs to be reviewed? Report it here: https://wknc.org/report")
    

    @commands.hybrid_command(name="sports", brief="Upcoming sports broadcasts for the month")
    async def sports(self, ctx: commands.Context, month: str = None):
        async with ctx.typing():
            if month:
                try:
                    startingtime = month_string_to_datetime(month)
                except:
                    await ctx.send("Please enter a valid month")
                    return
            else:
                startingtime = datetime(datetime.now().year, datetime.now().month, 1)

            embed = self.sports_schedule_month(startingtime)
            if (embed):
                await ctx.send(embed = embed)
            else:
                if month:
                    await ctx.send("I can't find any sports that month")
                else:
                    await ctx.send("I can't find any sports this month")

    def sports_schedule_month(self, starting_time):
        ending_time = datetime(starting_time.year, starting_time.month, 1)
        if starting_time.month == 12:
            ending_time = datetime(starting_time.year + 1, 1, 1)
        else:
            ending_time = datetime(starting_time.year, starting_time.month + 1, 1)

        # Replace URL with the actual URL of the website
        URL_WBB = 'https://gopack.com/sports/womens-basketball/schedule'
        URL_MBB = "https://gopack.com/sports/baseball/schedule"

        # Replace CLASS with the actual class of the unordered list items
        CLASS = 'sidearm-schedule-game-upcoming'

        # Send a GET request to the website
        response_WBB = r.get(URL_WBB)
        response_MBB = r.get(URL_MBB)

        # Parse the HTML of the website
        soup_WBB = BeautifulSoup(response_WBB.text, 'html.parser')
        soup_MBB = BeautifulSoup(response_MBB.text, 'html.parser')

        # Find all unordered list items with the specified class
        list_items_WBB = soup_WBB.find_all('li', class_=CLASS)
        list_items_MBB = soup_MBB.find_all('li', class_=CLASS)

        #list_items = list_items_MBB + list_items_WBB

        # Print the list items
        date_strings = []
        for item in list_items_WBB:
            datetextentry = ""
            div = item.find('div', class_='sidearm-schedule-game-opponent-date')
            if div:
                # Get the first two span elements
                spans = div.find_all('span', limit=2)
                # Print the text of the first two span elements
                datetextentry = spans[0].text + " " + spans[1].text

                if datetextentry[-2:] == "M ":
                    datetextentry = datetextentry[:-1]
            else:
                print('Div element not found')

            date_strings.append(":two_women_holding_hands::basketball: " + datetextentry)
        for item in list_items_MBB:
            datetextentry = ""
            div = item.find('div', class_='sidearm-schedule-game-opponent-date')
            if div:
                # Get the first two span elements
                spans = div.find_all('span', limit=2)
                # Print the text of the first two span elements
                datetextentry = spans[0].text + " " + spans[1].text

                datetextentry = datetextentry.replace("a.m.", "AM")
                datetextentry = datetextentry.replace("p.m.", "PM")
                if datetextentry[-2:] == "M ":
                    datetextentry = datetextentry[:-1]
            else:
                print('Div element not found')

            date_strings.append(":two_men_holding_hands::baseball: " + datetextentry)

        # Create a list of tuples with the parsed dates and the original string
        parsed_dates = []
        for date_string in date_strings:
            # Split the string on the space character to get the month, day, and time
            parts = date_string.split(" ")
            month = parts[1]
            day = parts[2] # remove the trailing ")" character
            weekday = parts[3]
            year = str(datetime.today().year)
            time = parts[4] + " " + parts[5] # combine the time and AM/PM parts

            timeformat = True
            # Check if the time string contains a colon character
            if ":" in time:
                # Use the datetime.strptime function to parse the time string into a time object
                try:
                    time_d = datetime.strptime(time, "%I:%M %p").time()
                except:
                    timeformat = False
            else:
                # If there is no colon, the time string is in the format "HH AM/PM"
                # Use the datetime.strptime function to parse the time string into a time object
                try:
                    time_d = datetime.strptime(time, "%I %p").time()
                except:
                    timeformat = False
            if (not timeformat):
                time_d = datetime.strptime("12 am", "%I %p").time()
            # Use the datetime.combine function to create a datetime object from the date and time
            date = datetime.combine(datetime.strptime(f"{month} {day} {year}", "%b %d %Y"), time_d)
            # Check if the date is later than today
            if date < datetime.now():
                date = date.replace(year=datetime.now().year + 1)
            # Add the tuple with the parsed date and the original string to the list
            if (date > starting_time and date < ending_time):
                parsed_dates.append((date, date_string))

        # Sort the list of tuples by the parsed dates
        sorted_dates = sorted(parsed_dates, key=lambda x: x[0])

        if not sorted_dates:
            return

        # Extract the sorted list of strings from the tuples
        sorted_date_strings = [t[1] for t in sorted_dates]

        embed_text = ""
        for entry in sorted_date_strings:
            embed_text += entry + "\n"

        embed = Embed(
            title = "Upcoming Sports Broadcasts for " + starting_time.strftime("%B"), description=embed_text, color=cogs.shared.EMBED_COLOR
        )

        return embed
    
    
    @commands.command(name="fart", brief="farts")
    async def fart(self, ctx: commands.Context):
        fart_str = 'p'
        for i in range(0, random.randint(3, 20)):
            fart_str += random.choice(['b', 'f', 'p', 'r'])
        
        await ctx.send(fart_str)
    

async def setup(bot):
    await bot.add_cog(Misc(bot))
