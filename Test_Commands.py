from discord.ext import commands

class Test_Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="test1")
    async def test1(self, ctx: commands.Context):
        await ctx.send("Test 1 successful")


async def setup(bot):
    await bot.add_cog(Test_Commands(bot))
