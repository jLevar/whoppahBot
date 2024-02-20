import discord
from discord.ext import commands, tasks
import settings
from models.account import Account
import helper
import datetime
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
        self.jobs = {"Unemployed": 0, "Dishwasher": 7.25, "Burger Flipper": 13.50, "Grill Master": 16.75}
        self.daily_locked_users = []
        self.check_work_timers.start()
        self.refresh_daily.start()

    ## COMMANDS
    @commands.command(aliases=['bal', 'b'])
    async def balance(self, ctx, mention: str = None):
        user_id = mention[2:-1] if mention else ctx.author.id
        account = Account.fetch(user_id)
        user = await self.bot.fetch_user(user_id)

        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            title=f"Balance: ${account.balance:.2f}",
        )
        embed.set_author(name=f"{user.name.capitalize()}", icon_url=user.display_avatar.url)
        embed.set_footer(text=f"\nRequested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(aliases=['p'])
    async def profile(self, ctx, mention: str = None):
        user_id = mention[2:-1] if mention else ctx.author.id
        account = Account.fetch(user_id)
        user = await self.bot.fetch_user(user_id)

        embed = discord.Embed(
            colour=discord.Colour.dark_blue(),
            title=f"Profile",
            description=f"Balance: ${account.balance:.2f}\nJob Title: {account.job_title}"
        )
        embed.set_author(name=f"{user.name.capitalize()}", icon_url=user.display_avatar.url)
        embed.set_footer(text=f"\nRequested by {ctx.author}")
        await ctx.send(embed=embed)

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

    @commands.command()
    async def daily(self, ctx):
        embed = discord.Embed(
            color=discord.Colour.light_grey(),
            title="Daily Gift Redemption",
            description="",
        )
        msg = await ctx.send(embed=embed)

        account = Account.fetch(ctx.author.id)

        if account.has_redeemed_daily:
            await helper.embed_edit(embed, msg, append="You have already redeemed your daily gift today.", sleep=1)
        else:
            Account.update_acct(account=account, balance_delta=50, has_redeemed_daily=1)
            await helper.embed_edit(embed, msg, append="Today's gift of $50 has been added to your account!", color=discord.Colour.brand_green(), sleep=1)

        await helper.embed_edit(embed, msg, footer="Refreshes at 0:00 MST")

    @commands.command(aliases=['t'])
    async def transfer(self, ctx, amount: float, mention):
        if amount <= 0:
            await ctx.send("Sorry, you have to send more than $0")
            return

        sender = Account.fetch(ctx.author.id)
        receiver = Account.fetch(mention[2:-1])

        if sender == receiver:
            await ctx.send("You cannot transfer money to self")
            return

        if sender.balance < amount:
            await ctx.send("Insufficient Funds")
            return

        if not await helper.validate_user_id(self.bot, ctx, receiver):
            await ctx.send("Recipient Unknown")
            return

        Account.update_acct(account=receiver, balance_delta=amount)
        Account.update_acct(account=sender, balance_delta=-amount)

        await ctx.send("Transfer complete!")

    @commands.group(invoke_without_command=True, aliases=['w'], help="Usage: !work [Shift Duration (hours)]")
    async def work(self, ctx, num_hours: int = 0):
        user_id = ctx.author.id
        account = Account.fetch(user_id)

        if account.job_title == "Unemployed":
            await ctx.send("You can't work until you are hired!\n*(Hint: Try !promotion)*")
            return

        if account.shift_start is not None:
            elapsed_time = (datetime.datetime.utcnow() - account.shift_start)
            elapsed_hours = elapsed_time / datetime.timedelta(hours=1)
            percent_left = (elapsed_hours / account.shift_length)

            if percent_left > 100:
                await self.pop_work_timer(account, elapsed_time)
                await ctx.send("Your shift's up!")
                return

            blank_bar = "# [----------------]"
            progress_bar = blank_bar.replace("-", "#", int(blank_bar.count("-") * percent_left))
            elapsed_seconds = elapsed_time / datetime.timedelta(seconds=1)
            et, eu = await convert_time(elapsed_seconds, "seconds")

            embed = discord.Embed(
                title=f"Your shift is {(percent_left * 100):.2f}% complete",
                colour=discord.Colour.blue(),
                description=f"You started your {account.shift_length} hour shift {et:.2f} {eu} ago\n"
                            f"{progress_bar}"
            )
            await ctx.send(embed=embed)
            return

        if num_hours < 1:
            await ctx.send("You have to work at least 1 hour to get paid!")
            return

        if num_hours > 24:
            await ctx.send("You cannot work more than 24 hours in a single shift!")
            return

        Account.update_acct(account=account, shift_start=datetime.datetime.utcnow(), shift_length=num_hours)

        await ctx.send("You started working!")

    @work.command()
    async def cancel(self, ctx):
        await ctx.send("Cancelling your shift...")
        user_id = ctx.author.id
        account = Account.fetch(user_id)

        if not account.shift_start:
            await ctx.send("You weren't working to begin with fool!")
            return

        elapsed_time = (datetime.datetime.utcnow() - account.shift_start)
        await self.pop_work_timer(account, elapsed_time)
        await ctx.send("Work cancel successful!")

    @commands.command()
    async def promotion(self, ctx):
        account = Account.fetch(ctx.author.id)
        await ctx.send(f"Promotion Request Received...")
        await asyncio.sleep(3)
        if account.job_title == "Unemployed":
            await ctx.send(f"Checking qualifications...")
            await asyncio.sleep(2)
            account.update_acct(account=account, job_title="Dishwasher")
            await ctx.send(f"Congratulations! You've been accepted to join the Burger King crew as a Dishwasher. "
                           f"Your starting salary will be: {self.jobs['Dishwasher']:.2f} an hour!")
            return
        elif account.job_title == "Dishwasher":
            await ctx.send(f"Checking performance...")
            await asyncio.sleep(2)
            if account.balance > 750:
                account.update_acct(account=account, job_title="Burger Flipper")
                await ctx.send(f"Congratulations! You've been promoted to the title of Burger Flipper. "
                               f"Your new salary will be: {self.jobs['Burger Flipper']:.2f} an hour!")
            else:
                await ctx.send(f"Sorry, but we will not be moving forward with your promotion at this time.")
                await ctx.send(f"(hint: you need $750 in the bank to get the next job)")
            return
        elif account.job_title == "Burger Flipper":
            await ctx.send(f"Checking performance...")
            await asyncio.sleep(2)
            if account.balance > 5000:
                account.update_acct(account=account, job_title="Grill Master")
                await ctx.send(f"Congratulations! You've been promoted to the title of Grill Master. "
                               f"Your new salary will be: {self.jobs['Grill Master']:.2f} an hour!")
            else:
                await ctx.send(f"Sorry, but we will not be moving forward with your promotion at this time.")
                await ctx.send(f"(hint: you need $5000 in the bank to get the next job)")
            return

        await ctx.send("Sorry, but there is no openings for you at this time.")
        await ctx.send("(which for the record means you have the best job currently in the game)")

    ## HELPER METHODS
    async def pop_work_timer(self, account, elapsed_time):
        user = await self.bot.fetch_user(account.user_id)
        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)

        if elapsed_time / datetime.timedelta(minutes=1) < 1:
            return

        money_earned = elapsed_hours * self.jobs[account.job_title]
        Account.update_acct(account=account, balance_delta=money_earned, shift_start="NULL", shift_length="NULL")

        await user.send(f"You earned ${money_earned:.2f} Burger Bucks for working!")

    ## TASKS
    @tasks.loop(seconds=300)  # Check every 5 minutes
    async def check_work_timers(self):
        current_time = datetime.datetime.utcnow()
        for account in Account.select().where(Account.shift_start.is_null(False)):
            elapsed_time = (current_time - account.shift_start)
            elapsed_hours = elapsed_time / datetime.timedelta(hours=1)
            # logger.info(f"{account.user_id} | {account.shift_start} | {account.shift_length} | {elapsed_hours}")
            if elapsed_hours >= account.shift_length:
                await self.pop_work_timer(account, elapsed_time)

    @tasks.loop(time=datetime.time(hour=7, minute=0, tzinfo=datetime.timezone.utc))  # 0:00 MST
    async def refresh_daily(self):
        query = Account.update(has_redeemed_daily=False, daily_allocated_bets=175)
        query.execute()

        # No daily's for these users!
        for user_id in self.daily_locked_users:
            Account.update_acct(user_id=user_id, has_redeemed_daily=True)

        logger.info("Daily Refresh Executed")
        logger.info(f"-----------------------------------")

    @check_work_timers.before_loop
    async def before_check_work_timers(self):
        await self.bot.wait_until_ready()

    @refresh_daily.before_loop
    async def before_refresh_daily(self):
        await self.bot.wait_until_ready()


