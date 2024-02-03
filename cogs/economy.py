import discord
from discord.ext import commands, tasks
import settings
from models.account import Account
import graphics
import datetime
import random
import asyncio

logger = settings.logging.getLogger('econ')


async def convert_time(time, units="seconds"):
    for i in range(2):
        if time >= 60:
            time /= 60
            units = "minutes" if units == "seconds" else "hours"
    return time, units


async def setup(bot):
    await bot.add_cog(Economy(bot))


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.jobs = {"Unemployed": 0, "Dishwasher": 7.25, "Burger Flipper": 13.50}
        self.check_work_timers.start()

    ## HELPER METHODS
    @staticmethod
    async def deposit(account, amount):
        account.balance += amount
        account.save()

    async def validate_user_id(self, ctx, user_id):
        try:
            await self.bot.fetch_user(user_id)
        except discord.errors.HTTPException as e:
            await ctx.send(f"Error: Invalid Mention")
            return False
        return True

    ## COMMANDS
    @commands.command(aliases=['bal', 'b'])
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
                embed.description += f"{i + 1} |\t{user.name} -- ${account.balance:.2f}\n"
        await ctx.send(embed=embed)

    @commands.command(aliases=['t'])
    async def transfer(self, ctx, amount, mention):
        amount = float(amount)
        if amount <= 0:
            await ctx.send("nice try buckaroo, but you can't send negative money 😂😂😂")
            return

        user_account = Account.fetch(ctx.author.id)
        if user_account.balance < amount:
            await ctx.send("you ain't got the money you broke bastard 😂😂😂")
            return

        if not await self.validate_user_id(ctx, mention[2:-1]):
            await ctx.send("i ain't sending no money to that fake user 😂😂😂")
            return

        target_account = Account.fetch(mention[2:-1])
        target_account.balance += amount
        target_account.save()

        user_account.balance -= amount
        user_account.save()

        await ctx.send("Transfer complete!")

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
    async def work(self, ctx, num_hours: int = 0):
        user_id = ctx.author.id
        account = Account.fetch(user_id)
        num_hours = int(num_hours)

        if account.shift_start is not None:
            elapsed_seconds = (asyncio.get_event_loop().time() - account.shift_start)
            elapsed_time, e_units = await convert_time(elapsed_seconds, "seconds")
            percent_left = ((elapsed_seconds / 3600) / account.shift_length) * 100
            graphics.create_progress_bar(percent_left)

            embed = discord.Embed(
                title=f"Your shift is {percent_left:.2f}% complete",
                colour=discord.Colour.blue(),
                description=f"You started your {account.shift_length} hour shift {elapsed_time:.2f} {e_units} ago"
            )

            file = discord.File(f"{settings.IMGS_DIR}/progress.png", filename="progress.png")
            embed.set_image(url="attachment://progress.png")
            await ctx.send(file=file, embed=embed)
            return

        if account.job_title == "Unemployed":
            await ctx.send("You can't work until you are hired!\n*(Hint: Try !promotion)*")
            return

        if num_hours < 1:
            await ctx.send("You have to work at least 1 hour to get paid!")
            return

        if num_hours > 24:
            await ctx.send("You cannot work more than 24 hours in a single shift!")
            return

        account.shift_start = asyncio.get_event_loop().time()
        account.shift_length = num_hours
        account.save()
        await ctx.send("You started working!")

    @commands.command()
    async def promotion(self, ctx):
        account = Account.fetch(ctx.author.id)
        await ctx.send(f"Promotion Request Received...")
        await asyncio.sleep(3)
        if account.job_title == "Unemployed":
            await ctx.send(f"Checking qualifications...")
            await asyncio.sleep(2)
            account.job_title = "Dishwasher"
            account.save()
            await ctx.send(f"Congratulations! You've been accepted to join the Burger King crew as a Dishwasher. "
                           f"Your starting salary will be: {self.jobs['Dishwasher']:.2f} an hour!")
            return
        elif account.job_title == "Dishwasher":
            await ctx.send(f"Checking performance...")
            await asyncio.sleep(2)
            if account.balance > 750:
                account.job_title = "Dishwasher"
                account.save()
                await ctx.send(f"Congratulations! You've been promoted to the title of Burger Flipper. "
                               f"Your new salary will be: {self.jobs['Burger Flipper']:.2f} an hour!")
            else:
                await ctx.send(f"Sorry, but we will not be moving forward with your promotion at this time.")
            return

        await ctx.send("Sorry, but there is no openings for you at this time.")

    @commands.command()
    async def daily(self, ctx):
        account = Account.fetch(ctx.author.id)
        if account.has_redeemed_daily:
            await ctx.send("You have already redeemed your daily gift. Try again tomorrow.")
            return
        account.balance += 50
        account.has_redeemed_daily = 1
        account.save()
        await ctx.send("Today's gift of $50 has been added to your account!")

    ## TASKS
    @tasks.loop(seconds=300)  # Check every 5 minutes
    async def check_work_timers(self):
        current_time = asyncio.get_event_loop().time()
        logger.info(f"Current Time = {current_time}")

        for account in Account.select().where(Account.shift_start.is_null(False)):
            elapsed_hours = (current_time - account.shift_start) / 3600
            # logger.info(f"{account.user_id} | {account.shift_start} | {account.shift_length} | {elapsed_hours}")

            if elapsed_hours >= account.shift_length:
                money_earned = round(account.shift_length * self.jobs[account.job_title], 2)
                user = await self.bot.fetch_user(account.user_id)
                await self.deposit(account, money_earned)
                await user.send(f"You earned ${money_earned:.2f} Burger Bucks for working!")
                account.shift_start = None
                account.shift_length = None
                account.save()

        # logger.info(f"-----------------------------------")

    new_day = datetime.time(hour=0, minute=0, tzinfo=datetime.timezone.utc)

    @tasks.loop(time=new_day)
    async def refresh_daily(self):
        query = Account.update(has_redeemed_daily=False)
        query.execute()
        query = Account.update(daily_allocated_bets=200)
        query.execute
        logger.info("DAILY'S REFRESHED!")

    @check_work_timers.before_loop
    async def before_check_work_timers(self):
        await self.bot.wait_until_ready()

    @refresh_daily.before_loop
    async def refresh_daily(self):
        await self.bot.wait_until_ready()
