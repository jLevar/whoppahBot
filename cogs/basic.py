import discord
from discord.ext import commands
import random


class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if random.randint(0, 20) == 0:
            await message.add_reaction("😂")

    @commands.command()
    async def hello(self, ctx, *, member: discord.Member):
        await ctx.send(f"Hello {member.name}")

    @commands.command(
        aliases=['p'],
        help="To use ping, simply type !ping or !p",
        description="When pinged, the bot will respond with a pong",
        brief="Responds with pong",
        enabled=True
    )
    async def ping(self, ctx):
        await ctx.send("pong")

    @commands.command()
    async def joke(self, ctx):
        await ctx.send("How many doctors does it take to screw in a lightbulb? Two, one to screw it in and the other to"
                       " hold the ladder 😂😂😂😂😂😂😂😂")
        await ctx.message.author.send("Please don't ask me to tell any more jokes, it's so embarrassing")

    @commands.command()
    async def say(self, ctx, *what):
        if what == ():
            # NOTE - This error message is a prank DM
            with open("error_message.txt", "r") as f:
                error_message = f.read()
            await ctx.message.author.send(error_message)
        else:
            await ctx.send(" ".join(what))

    @commands.command()
    async def joined(self, ctx, who: discord.Member):
        await ctx.send(who.joined_at)


async def setup(bot):
    await bot.add_cog(Basic(bot))
