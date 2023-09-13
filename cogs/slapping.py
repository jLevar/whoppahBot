import discord
from discord.ext import commands
import random


class Slapper(commands.Converter):
    def __init__(self, *, use_nicknames) -> None:
        self.use_nicknames = use_nicknames

    async def convert(self, ctx, argument):
        someone = random.choice(ctx.guild.members)
        name = ctx.author
        if self.use_nicknames:
            name = ctx.author.nick
        return f"{name} slaps {someone} with {argument}"


class Slapping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def slap(self, ctx, reason: Slapper(use_nicknames=True)):
        await ctx.send(reason)


async def setup(bot):
    await bot.add_cog(Slapping(bot))
