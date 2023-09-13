import discord
import peewee
import random
from discord.ext import commands
import settings
from models.account import Account

logger = settings.logging.getLogger('Economy Logger')


class EconomyBot(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def balance(self, ctx):
        account = Account.fetch(ctx.message)
        await ctx.send(f"Your balance is {account.amount}")

    @commands.command()
    async def coin(self, ctx, choice: str, amount: int):
        if amount <= 0:
            await ctx.send("You cannot bet an amount <= 0")
            return
        account = Account.fetch(ctx.message)
        if amount > account.amount:
            await ctx.send("You don't have enough credits")
            return

        heads = random.randint(0, 1)
        if (heads and choice.lower().startswith("t")) or (not heads and choice.lower().startswith("h")):
            amount = -amount  # User lost coin flip, they will be given the negative amount they bet
        account.amount += amount
        account.save()
        await ctx.send("You Won!!" if amount > 0 else "You Lost!!")


async def setup(bot):
    await bot.add_cog(EconomyBot(bot))