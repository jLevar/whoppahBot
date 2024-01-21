import discord
import peewee
import random
from discord.ext import commands, tasks
import settings
from models.account import Account
import asyncio

#TODO certifate of deposits
logger = settings.logging.getLogger('econ')


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.jobs = {"Burger Flipper": 690.00}
        self.work_timers = {}
        self.check_work_timers.start()

    @commands.command()
    async def open_account(self, ctx):
        Account.create_account(ctx.message)

    @staticmethod
    async def deposit(account, amount):
        account.amount += amount
        account.save()

    @staticmethod
    async def convert_time(time, units="seconds"):
        for i in range(2):
            if time >= 60:
                time /= 60
                units = "minutes" if units == "seconds" else "hours"
        return time, units

    @commands.command()
    async def balance(self, ctx):
        account = Account.fetch(ctx.message.author.id)
        await ctx.send(f"Your balance is ${account.amount:.2f} Burger Buck$")

    @commands.command()
    async def coin(self, ctx, choice: str, amount: int):
        if amount <= 0:
            await ctx.send("You cannot 0 or fewer Burger Bucks")
            return
        account = Account.fetch(ctx.message.author.id)
        if amount > account.amount:
            await ctx.send("You don't have enough Burger Bucks")
            return

        heads = random.randint(0, 1)
        if (heads and choice.lower().startswith("t")) or (not heads and choice.lower().startswith("h")):
            amount = -amount  # User lost coin flip, they will be given the negative amount they bet
        await self.deposit(account, amount)
        await ctx.send("You Won!!" if amount > 0 else "You Lost!!")

    @commands.command()
    async def work(self, ctx, num_hours: float = 0.0):
        user_id = ctx.author.id
        job_title = 'Burger Flipper'  # aTODO store user's job somewhere and get it here
        hourly_rate = self.jobs[job_title]

        if user_id in self.work_timers:
            start_time, num_hours, hourly_rate = self.work_timers[user_id]
            shift_length, su = await self.convert_time(num_hours * 3600, "seconds")
            elapsed_time, eu = await self.convert_time((asyncio.get_event_loop().time() - start_time), "seconds")
            await ctx.send(f"You already started working your {shift_length} {su[:-1]} shift, {elapsed_time:.2f} {eu} ago")
            return

        if num_hours <= 0:
            await ctx.send("You have to work for more than 0 hours to get paid")
            return

        self.work_timers[user_id] = (asyncio.get_event_loop().time(), num_hours, hourly_rate)
        await ctx.send("You started working!")

    @tasks.loop(seconds=60)  # Check every minute
    async def check_work_timers(self):
        logger.info(f"{self.work_timers}")
        current_time = asyncio.get_event_loop().time()
        for user_id, (start_time, num_hours, hourly_rate) in self.work_timers.copy().items():
            elapsed_hours = (current_time - start_time) / 3600  # Convert seconds to hours
            if elapsed_hours >= num_hours:
                currency_earned = round(elapsed_hours * hourly_rate, 2)
                user = self.bot.get_user(user_id)
                account = Account.fetch(user_id)
                if user:
                    await self.deposit(account, currency_earned)
                    await user.send(f"You earned ${currency_earned} Burger Bucks for working!")
                del self.work_timers[user_id]
                logger.info(f"Removed {user_id} from work_timers")

    @check_work_timers.before_loop
    async def before_check_work_timers(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Economy(bot))
