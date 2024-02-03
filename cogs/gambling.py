import random

import discord
from discord.ext import commands, tasks
from models.account import Account
import asyncio


async def setup(bot):
    await bot.add_cog(Gambling(bot))


class Gambling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ## HELPER METHODS
    @staticmethod
    async def deposit(account, amount):
        account.balance += amount
        account.save()

    @staticmethod
    async def send_gambling_psa(user):
        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            description=f"You've reached the daily limit for the gambling mini-games.\n\n"
                        f"Please use this restriction as an opportunity to step away and take a break.\n\n"
                        f"These mini-games can activate your brain's circuitry in a way that makes it highly addictive.\n\n"
                        f"I would encourage you to consider taking a look at these resources:\n"
                        f"https://www.helpguide.org/articles/addictions/gambling-addiction-and-problem-gambling.html"
                        f"https://www.apa.org/monitor/2023/07/how-gambling-affects-the-brain",
            title="Gambling"
        )
        await user.send(embed=embed)
        await asyncio.sleep(10)
        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            description=f"Please note that Whoppah Bot is still in very early stages of development.\n If you think this warning "
                        f"was sent out prematurely please send feedback. The intent of this message is not to treat users like addicts if "
                        f"they are just playing responsibly and not excessively.\n\n",
            title="A Note from the Developer"
        )
        await user.send(embed=embed)

    ## COMMANDS
    @commands.command(aliases=['dwtd'], help="Usage: !dwtd [Choice (1-6)] [Amount to Bet]")
    @commands.cooldown(1, 9, commands.BucketType.user)
    async def deal_with_the_devil(self, ctx, choice: int, amount: float):
        account = Account.fetch(ctx.message.author.id)
        embed = discord.Embed(
            colour=discord.Colour.dark_red(),
            title="A Deal with the Devil",
            description="Ahh...\n"
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        msg = await ctx.send(embed=embed)

        await asyncio.sleep(1)
        embed.description += "Come to make a deal with the devil have we?\n\n"
        await msg.edit(embed=embed)
        await asyncio.sleep(2)

        if amount <= 0:
            embed.description += f"You must put some skin in the game muchacho\n\n" \
                                 f"[Use !help dwtd]"
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        if choice < 1 or choice > 6:
            embed.description += "It's a roll of the die my friend, pick a number between 1 and 6 next time\n\n"
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        if account.daily_allocated_bets <= 0:
            embed.description += "No more gambling for you today.\n\n"
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        if amount > account.balance:
            embed.description += "Tried to put one past me eh?\n\n"
            await msg.edit(embed=embed)
            await asyncio.sleep(2)
            embed.description += "WELL YOU CANT BET MORE THAN YOU HAVE!!\n\n"
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        die = random.randint(1, 6)
        embed.description += f"You say {choice}, ey?\n\n"
        await msg.edit(embed=embed)
        await asyncio.sleep(3)

        embed.description += f"The die reads {die}\n\n"
        await msg.edit(embed=embed)
        await asyncio.sleep(2)

        if choice == die:
            await self.deposit(account, amount * 6.953)
            embed.description += f"It seems Madame Luck is in your throes tonight. You won ${amount * 6.953:.2f}\n\n"
            embed.colour = discord.Colour.gold()
            await msg.edit(embed=embed)
        else:
            await self.deposit(account, -amount)
            embed.description += f"It seems you lack what it takes to dance with the devil in " \
                                 f"the pale moonlight.\n\n"
            await msg.edit(embed=embed)
            await asyncio.sleep(2)
            embed.description += f"Don't worry, I'll make good use of that ${amount:.2f}\n\n"
            await msg.edit(embed=embed)

        account.daily_allocated_bets -= 1
        account.save()
        if account.daily_allocated_bets <= 0:
            await self.send_gambling_psa(ctx.author)

        await asyncio.sleep(3)
        embed.description += f"I hope to see another deal is in our future"
        await msg.edit(embed=embed)

    @commands.command(aliases=['c'], help="Usage: !coin [Heads/Tails] [Amount to Bet]")
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def coin(self, ctx, choice: str, amount: float):
        account = Account.fetch(ctx.message.author.id)
        embed = discord.Embed(
            colour=discord.Colour.light_grey(),
            title="A Flip of the Coin",
            description="Back again?\n\n"
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(1)

        if amount <= 0:
            embed.description += f"Try betting more than $0 next time..."
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        if account.daily_allocated_bets <= 0:
            embed.description += "No more gambling for you today.\n\n"
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        if amount > account.balance:
            embed.description += f"You don't have enough money for that..."
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        choice = choice.lower()[0]
        if choice not in "ht":
            embed.description += f"Invalid choice, please select either heads or tails"
            embed.colour = discord.Colour.darker_gray()
            await msg.edit(embed=embed)
            return

        heads = random.randint(0, 1)
        embed.description += f"It's {'heads' if heads else 'tails'}.\n\n"
        await msg.edit(embed=embed)
        await asyncio.sleep(1)

        if (heads and choice == "t") or (not heads and choice == "h"):
            amount = -amount  # User lost coin flip, they will be given the negative amount they bet
        await self.deposit(account, amount)

        account.daily_allocated_bets -= 1
        account.save()
        if account.daily_allocated_bets <= 0:
            await self.send_gambling_psa(ctx.author)

        if amount > 0:
            embed.description += f"Congratulations, you won ${amount:.2f}"
            embed.colour = discord.Colour.green()
            await msg.edit(embed=embed)
        else:
            embed.description += f"I'll be keeping that ${-amount:.2f}"
            embed.colour = discord.Colour.red()
            await msg.edit(embed=embed)
