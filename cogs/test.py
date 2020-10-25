from discord.ext import commands

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(pass_context=True)
    async def cogtest(self, ctx, *, text):
        await ctx.send(text)