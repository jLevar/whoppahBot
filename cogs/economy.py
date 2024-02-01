import time
import discord
import random
from discord.ext import commands, tasks
import settings
from models.account import Account
import asyncio


logger = settings.logging.getLogger('econ')


async def convert_time(time_, units="seconds"):
    for i in range(2):
        if time_ >= 60:
            time_ /= 60
            units = "minutes" if units == "seconds" else "hours"
    return time_, units


async def setup(bot):
    await bot.add_cog(Economy(bot))


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.jobs = {"Unemployed": 0, "Burger Flipper": 690.00}
        self.work_timers = {}
        self.check_work_timers.start()

    ## HELPER METHODS
    @staticmethod
    async def deposit(account, amount):
        account.balance += amount
        account.save()

    ## COMMANDS
    @commands.command(aliases=['b'])
    async def balance(self, ctx):
        account = Account.fetch(ctx.author.id)
        await ctx.send(f"Your balance is ${account.balance:.2f} Burger Bucks!")

    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx):
        embed = discord.Embed(
            colour=discord.Colour.dark_green(),
            title="Top 10 Richest Users",
            description=""
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        for i, user_id in enumerate(Account.leaderboard(10)):
            user = await self.bot.fetch_user(user_id)
            account = Account.fetch(user_id)
            if user.id == ctx.author.id:
                embed.description += f"**{i + 1} |\t{user.name} -- ${account.balance:.2f}**\n"
            else:
                embed.description += f"{i+1} |\t{user.name} -- ${account.balance:.2f}\n"
        await ctx.send(embed=embed)

    @commands.command(aliases=['p'])
    async def profile(self, ctx):
        account = Account.fetch(ctx.author.id)
        embed = discord.Embed(
            colour=discord.Colour.dark_blue(),
            title="Your User Profile",
            description=f"Balance: ${account.balance:.2f}\nJob Title: {account.job_title}"
        )
        embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(help="Usage: !work [Shift Duration (hours)]")
    async def work(self, ctx, num_hours: float = 0.0):
        user_id = ctx.author.id
        job_title = Account.fetch(user_id).job_title
        hourly_rate = self.jobs[job_title]

        if user_id in self.work_timers:
            start_time, num_hours, hourly_rate = self.work_timers[user_id]
            shift_length, s_units = await convert_time(num_hours * 3600, "seconds")
            elapsed_time, e_units = await convert_time((asyncio.get_event_loop().time() - start_time), "seconds")
            await ctx.send(f"You already started working your {shift_length} {s_units[:-1]} shift,"
                           f" {elapsed_time:.2f} {e_units} ago")
            return

        if num_hours <= 0:
            await ctx.send("You have to work for more than 0 hours to get paid!")
            return

        if num_hours > 24:
            await ctx.send("You cannot work more than 24 hours in a single shift!")
            return

        if job_title == "Unemployed":
            await ctx.send("You can't work until you are hired!")
            return

        self.work_timers[user_id] = (asyncio.get_event_loop().time(), num_hours)
        await ctx.send("You started working!")

    @commands.command()
    async def promotion(self, ctx):
        account = Account.fetch(ctx.author.id)
        await ctx.send(f"Promotion Request Received...")
        time.sleep(3)
        if account.job_title == "Unemployed":
            await ctx.send(f"Checking qualifications...")
            time.sleep(2)
            account.job_title = "Burger Flipper"
            account.save()
            await ctx.send(f"Congratulations! You've been accepted to join the Burger King crew as a Burger Flipper. "
                           f"Your starting salary will be: {self.jobs['Burger Flipper']:.2f} an hour!")
            return
        await ctx.send("Sorry, but there is no openings for you at this time.")

    @commands.command(help="Usage: !coin [Heads/Tails] [Amount to Bet]", aliases=['c'])
    async def coin(self, ctx, choice: str, amount: int):
        if amount <= 0:
            await ctx.send("You cannot 0 or fewer Burger Bucks")
            return
        account = Account.fetch(ctx.message.author.id)
        if amount > account.balance:
            await ctx.send("You don't have enough Burger Bucks")
            return

        heads = random.randint(0, 1)
        if (heads and choice.lower().startswith("t")) or (not heads and choice.lower().startswith("h")):
            amount = -amount  # User lost coin flip, they will be given the negative amount they bet
        await self.deposit(account, amount)
        await ctx.send("You Won!!" if amount > 0 else "You Lost!!")

    ## TASKS
    @tasks.loop(seconds=60)  # Check every minute
    async def check_work_timers(self):
        current_time = asyncio.get_event_loop().time()
        logger.info(f"{current_time} | {self.work_timers}")
        for user_id, (start_time, num_hours) in self.work_timers.copy().items():
            elapsed_hours = (current_time - start_time) / 3600  # Convert seconds to hours
            if elapsed_hours >= num_hours:
                user = self.bot.get_user(user_id)
                account = Account.fetch(user_id)
                currency_earned = round(elapsed_hours * self.jobs[account.job_title], 2)
                if user:
                    await self.deposit(account, currency_earned)
                    await user.send(f"You earned ${currency_earned} Burger Bucks for working!")
                del self.work_timers[user_id]
                logger.info(f"Removed {user_id} from work_timers")

    @check_work_timers.before_loop
    async def before_check_work_timers(self):
        await self.bot.wait_until_ready()


