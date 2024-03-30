import random

import discord
from discord.ext import commands, tasks

import helper
from models.account import Account
from models.assets import Assets
import asyncio


async def setup(bot):
    await bot.add_cog(Casino(bot))


class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ## HELPER METHODS
    @staticmethod
    async def send_gambling_psa(user):
        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            description=f"You've reached the daily limit for the gambling mini-games.\n\n"
                        f"Let this restriction be an opportunity to step away from Discord and take a break.\n\n"
                        f"This restriction's purpose is twofold. One, to limit game usage in case you have found a "
                        f"highly effective strategy to win money. And two, to make sure addictive usage is minimized."
                        f"\n-\n"
                        f"These mini-games can activate your brain's circuitry in a way that makes it addictive.\n\n"
                        f"If you felt stuck playing until you hit the daily limit, consider maybe taking a look at these resources:\n"
                        f"https://www.helpguide.org/articles/addictions/gambling-addiction-and-problem-gambling.html\n"
                        f"https://www.apa.org/monitor/2023/07/how-gambling-affects-the-brain\n-\n"
                        f"*Again, your engagement with the bot and games are greatly appreciated.*\n\n**Feel free to continue playing tomorrow!**",
            title="Casino Daily Limit Reached"
        )
        await user.send(embed=embed)

    ## COMMANDS
    @commands.command(hidden=True, help="Antiquated gateway for `!dice`")
    async def dwtd(self, ctx, choice: int, amount):
        await ctx.send("Warning: Command name won't be supported in future. Please use `!dice` instead")
        await ctx.invoke(self.bot.get_command('dice'), choice=choice, amount=amount)

    @commands.command(brief="Fair die betting game", help="Usage: !dice [Choice (1-6)] [Amount to Bet]")
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def dice(self, ctx, choice: int, amount):
        amount = Assets.standardize('cash', amount)
        account = await Account.fetch(ctx.message.author.id)
        account_assets = await Assets.fetch(ctx.message.author.id)
        embed = discord.Embed(
            colour=discord.Colour.dark_red(),
            title="A Deal with the Devil",
            description=""
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        msg = await ctx.send(embed=embed)

        await helper.embed_edit(embed, msg, f"Ahh...\n", sleep=1)
        await helper.embed_edit(embed, msg, "Come to make a deal with the devil have we?\n\n", sleep=2)

        if amount <= 0:
            await helper.embed_edit(embed, msg, f"You must put some skin in the game muchacho\n\n[Use !help dice]",
                                    color=discord.Colour.darker_gray())
            return

        if choice < 1 or choice > 6:
            await helper.embed_edit(embed, msg,
                                    "It's a roll of the die my friend, pick a number between 1 and 6 next time\n\n",
                                    color=discord.Colour.darker_gray())
            return

        if account.daily_allocated_bets <= 0:
            await helper.embed_edit(embed, msg, "No more gambling for you today.\n\n",
                                    color=discord.Colour.darker_gray())
            return

        if amount > account_assets.cash:
            await helper.embed_edit(embed, msg, "Tried to put one past me eh?\n\n", sleep=2)
            await helper.embed_edit(embed, msg, "WELL YOU CANT BET MORE THAN YOU HAVE!!\n\n",
                                    color=discord.Colour.darker_gray())
            return

        await helper.embed_edit(embed, msg, f"You say {choice}, ey?\n\n", sleep=3)
        die = random.randint(1, 6)
        await helper.embed_edit(embed, msg, f"The die reads {die}\n\n", sleep=2)

        if choice == die:
            amount = amount * 6.12
            await helper.embed_edit(embed, msg,
                                    f"It seems Madame Luck is in your throes tonight. "
                                    f"You won ${Assets.format('cash', amount)}\n\n",
                                    color=discord.Colour.gold(), sleep=2)
        else:
            amount = -amount
            await helper.embed_edit(embed, msg,
                                    f"It seems you lack what it takes to dance with the devil in the pale moonlight.\n\n",
                                    sleep=2)
            await helper.embed_edit(embed, msg, f"Don't worry, I'll make good use of that "
                                                f"{Assets.format('cash', -amount)}\n\n", sleep=2)

        await Account.update_acct(account=account, daily_allocated_bets_delta=-1)
        await Assets.update_assets(user=account_assets, cash_delta=amount)
        await helper.embed_edit(embed, msg, f"I hope to see another deal is in our future")

        if account.daily_allocated_bets <= 0:
            await self.send_gambling_psa(ctx.author)

    @commands.command(aliases=['c'], brief="Fair coin betting game", help="Usage: !coin [Heads/Tails] [Amount to Bet]")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def coin(self, ctx, choice: str, amount: float):
        amount = Assets.standardize('cash', amount)
        account = await Account.fetch(ctx.message.author.id)
        account_assets = await Assets.fetch(ctx.message.author.id)
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

        if amount > account_assets.cash:
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

        await Account.update_acct(account=account, daily_allocated_bets_delta=-1)
        await Assets.update_assets(user=account_assets, cash_delta=amount)

        if amount > 0:
            embed.description += f"Congratulations, you won ${Assets.format('cash', amount)}"
            embed.colour = discord.Colour.green()
            await msg.edit(embed=embed)
        else:
            embed.description += f"I'll be keeping that {Assets.format('cash', -amount)}"
            embed.colour = discord.Colour.red()
            await msg.edit(embed=embed)

        if account.daily_allocated_bets <= 0:
            await self.send_gambling_psa(ctx.author)
