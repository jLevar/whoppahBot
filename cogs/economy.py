import datetime

import discord
from discord.ext import commands, tasks

import helper
import settings
from models.account import Account
from models.assets import Assets

logger = settings.logging.getLogger('bot')


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
        self.jobs = {
            "Unemployed": {"salary": 0, "requirements": {"balance": 0, "xp": 0}},
            "Dishwasher": {"salary": 725, "requirements": {"balance": 0, "xp": 0}},
            "Burger Flipper": {"salary": 1350, "requirements": {"balance": 75000, "xp": 2500}},
            "Grill Master": {"salary": 1675, "requirements": {"balance": 500000, "xp": 15000}},
            "Shift Lead": {"salary": 2000, "requirements": {"balance": 2500000, "xp": 50000}}
        }
        self.daily_locked_users = []
        self.check_work_timers.start()
        self.refresh_daily.start()

    ## COMMANDS
    @commands.command(aliases=['bal', 'b'])
    async def balance(self, ctx, mention: str = None):
        user_id = mention[2:-1] if mention else ctx.author.id
        user_assets = await Assets.fetch(user_id)
        user = await self.bot.fetch_user(user_id)

        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            title=f"Balance: {helper.to_dollars(user_assets.cash)}",
        )
        embed.set_author(name=f"{user.name.capitalize()}", icon_url=user.display_avatar.url)
        embed.set_footer(text=f"\nRequested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(aliases=['p'])
    async def profile(self, ctx, mention: str = None):
        user_id = mention[2:-1] if mention else ctx.author.id
        user_acc = await Account.fetch(user_id)
        user_assets = await Assets.fetch(user_id)
        user = await self.bot.fetch_user(user_id)

        embed = discord.Embed(
            colour=discord.Colour.dark_blue(),
            title=f"Profile",
            description=f"Balance: {helper.to_dollars(user_assets.cash)}\nJob Title: {user_acc.job_title}\nDaily Streak: {user_acc.daily_streak}"
                        f"\nXP: {user_acc.main_xp}\nGold: {user_assets.gold}"
        )
        embed.set_author(name=f"{user.name.capitalize()}", icon_url=user.display_avatar.url)
        embed.set_footer(text=f"\nRequested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx, sort_attr="cash"):
        embed = discord.Embed(
            colour=discord.Colour.dark_green(),
            title=f"Top 10 Users by {sort_attr.title()}",
            description=""
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        for i, user_data in enumerate(await Assets.top_users(10, column=sort_attr)):
            user_id = user_data[0]
            user_value = user_data[1]
            user = await self.bot.fetch_user(user_id)

            if sort_attr == "cash":
                user_value = helper.to_dollars(user_value)

            if user.id == ctx.author.id:
                embed.description += f"**{i + 1} |\t{user.name} -- {user_value}**\n"
            else:
                embed.description += f"{i + 1} |\t{user.name} -- {user_value}\n"

        await ctx.send(embed=embed)

    @commands.command()
    async def daily(self, ctx):
        embed = discord.Embed(
            color=discord.Colour.light_grey(),
            title="Daily Gift Redemption",
            description="",
        )
        msg = await ctx.send(embed=embed)

        account = await Account.fetch(ctx.author.id)
        user_assets = await Assets.fetch(ctx.author.id)

        if account.has_redeemed_daily:
            await helper.embed_edit(embed, msg, append="You have already redeemed your daily gift today.\n", sleep=1)
        else:
            daily_streak = account.daily_streak + 1
            daily_cash = self.daily_ladder(daily_streak)
            daily_xp = 50
            await Assets.update_assets(user=user_assets, cash_delta=daily_cash * 100)
            await Account.update_acct(account=account, main_xp_delta=daily_xp, has_redeemed_daily=1,
                                      daily_streak_delta=1)
            await helper.embed_edit(embed, msg,
                                    append=f"Nice to have you back! Here's today gift!\n",
                                    color=discord.Colour.brand_green(), sleep=1)
            await helper.embed_edit(embed, msg, append=f"**+${daily_cash}**\n", sleep=1)
            await helper.embed_edit(embed, msg, append=f"**+{daily_xp}xp**\n\n", sleep=1)

            daily_ladder_chart = ""
            start_day = (((daily_streak - 1) // 7) * 7) + 1
            for i in range(start_day, start_day + 7):
                if i == daily_streak:
                    daily_ladder_chart += f"**Day {i}:\t${self.daily_ladder(i)}**\t*(Today)*\n"
                else:
                    daily_ladder_chart += f"Day {i}:\t${self.daily_ladder(i)}\n"

            await helper.embed_edit(embed, msg, append=daily_ladder_chart, sleep=1)

        await helper.embed_edit(embed, msg, append=f"\nCurrent Active Streak: {account.daily_streak}", sleep=1)
        await helper.embed_edit(embed, msg, footer="Refreshes at 0:00 MST")

    @staticmethod
    def daily_ladder(day: int):
        return (((day - 1) % 7) * day) + 50

    @commands.command(aliases=['t'])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def transfer(self, ctx, amount: float, mention):
        amount = int(amount * 100)

        if amount <= 0:
            await ctx.send("Sorry, you have to send more than $0")
            return

        sender = await Assets.fetch(ctx.author.id)
        receiver = await Assets.fetch(mention[2:-1])

        if sender == receiver:
            await ctx.send("You cannot transfer money to self")
            return

        if sender.cash < amount:
            await ctx.send("Insufficient Funds")
            return

        if not await helper.validate_user_id(self.bot, receiver.user_id):
            await ctx.send("Recipient Unknown")
            return

        await Assets.update_assets(user=receiver, cash_delta=amount)
        await Assets.update_assets(user=sender, cash_delta=-amount)

        await ctx.send("Transfer complete!")

    @commands.group(invoke_without_command=True, aliases=['w'], help="Usage: !work [Shift Duration (hours)]")
    async def work(self, ctx, num_hours: int = 0):
        user_id = ctx.author.id
        account = await Account.fetch(user_id)

        if account.job_title == "Unemployed":
            await ctx.send("You can't work until you are hired!\n*(Hint: Try !promotion)*")
            return

        if account.shift_start is not None:
            elapsed_time = (datetime.datetime.utcnow() - account.shift_start)
            elapsed_hours = elapsed_time / datetime.timedelta(hours=1)
            percent_left = (elapsed_hours / account.shift_length)

            if percent_left > 1:
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

        await Account.update_acct(account=account, shift_start=datetime.datetime.utcnow(), shift_length=num_hours)

        await ctx.send("You started working!")

    @work.command()
    async def cancel(self, ctx):
        await ctx.send("Cancelling your shift...")
        user_id = ctx.author.id
        account = await Account.fetch(user_id)

        if not account.shift_start:
            await ctx.send("You weren't working to begin with fool!")
            return

        elapsed_time = (datetime.datetime.utcnow() - account.shift_start)
        if elapsed_time / datetime.timedelta(minutes=1) < 1:
            await ctx.send("You must work at least one minute before you cancel!")
            return
        await self.pop_work_timer(account, elapsed_time)
        await ctx.send("Work cancel successful!")

    @commands.command()
    async def promotion(self, ctx):
        account = await Account.fetch(ctx.author.id)
        user_assets = await Assets.fetch(ctx.author.id)
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Promotion Request",
            description=""
        )
        msg = await ctx.send(embed=embed)

        await helper.embed_edit(embed, msg, append="Promotion Request Received...\n\n", sleep=3)
        await helper.embed_edit(embed, msg, append="Checking qualifications...\n\n", sleep=2)

        jobs_list = [*self.jobs, "MAX"]
        next_job = jobs_list[jobs_list.index(account.job_title) + 1]

        if next_job == "MAX":
            await helper.embed_edit(embed, msg, append="Sorry, but there is no opening for you at this time.", sleep=2)
            await helper.embed_edit(embed, msg, footer="Note: You have the best job currently in the game")
            return

        requirements = self.jobs[next_job]["requirements"]

        if user_assets.cash >= requirements["balance"] and account.main_xp >= requirements["xp"]:
            await Account.update_acct(account=account, job_title=next_job)
            await helper.embed_edit(embed, msg,
                                    append=f"Congratulations! Your job title is now: {next_job}\n\n",
                                    sleep=2)
            await helper.embed_edit(embed, msg,
                                    append=f"Your salary is now: {helper.to_dollars(self.jobs[next_job]['salary'])} an hour!\n\n")
        else:
            await helper.embed_edit(embed, msg,
                                    append="Sorry, but we will not be moving forward with your promotion at this time.",
                                    sleep=2)
            await helper.embed_edit(embed, msg,
                                    footer=f"Hint: you need {helper.to_dollars(requirements['balance'])} and {requirements['xp']}xp to get the next job")

    @commands.command(aliases=["store"])
    async def shop(self, ctx):
        account = await Account.fetch(ctx.author.id)
        user_assets = await Assets.fetch(ctx.author.id)

        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            title="Welcome to Burger King",
            description="What can I get for you today?\n\n"
        )

        menu = {
            "Whoppers:": {"price": 225, "xp": 20},
            "Fries:": {"price": 169, "xp": 15},
            "Drink:": {"price": 120, "xp": 10}
        }

        # Fields
        embed.add_field(name="Menu", value="Whoppers: $2.25\nFries: $1.69\nDrink: $0.99", inline=False)
        embed.add_field(name="Whoppers:", value="0x")
        embed.add_field(name="Fries:", value="0x")
        embed.add_field(name="Drink:", value="0x")

        total_items = helper.ListenerField(embed=embed, name="Total Items:", inline=False)

        total_cost = helper.ListenerField(embed=embed, name="Subtotal:", value="<var>", inline=False)
        total_cost.get_delta = lambda data: menu[data["name"]]["price"]

        def value_format(self):
            return self.value.replace("<var>", f"{helper.to_dollars(self.var)}")

        total_cost.value_format = value_format.__get__(total_cost, helper.ListenerField)

        total_xp = helper.ListenerField(embed=embed, name="Total XP:", value="<var> xp")
        total_xp.get_delta = lambda data: menu[data["name"]]["xp"]

        buttons = [
            helper.TrackerButton(ctx=ctx, embed=embed, field_index=1, field_value="<var>x", emoji="🍔",
                                 style=discord.ButtonStyle.blurple,
                                 listeners=[total_items, total_cost, total_xp]),

            helper.TrackerButton(ctx=ctx, embed=embed, field_index=2, field_value="<var>x", emoji="🍟",
                                 style=discord.ButtonStyle.blurple,
                                 listeners=[total_items, total_cost, total_xp]),

            helper.TrackerButton(ctx=ctx, embed=embed, field_index=3, field_value="<var>x", emoji="🥤",
                                 style=discord.ButtonStyle.blurple,
                                 listeners=[total_items, total_cost, total_xp]),

            helper.ExitButton(ctx=ctx, embed=embed,
                              exit_field={"name": "\n\nThanks for shopping with us!", "value": ""},
                              label="Checkout", style=discord.ButtonStyle.green),

            helper.ExitButton(ctx=ctx, embed=embed,
                              exit_field={"name": "\n\nCome back if you change your mind!", "value": ""},
                              label="X", style=discord.ButtonStyle.danger),
        ]

        async def checkout(interaction, _embed):
            cost = total_cost.var
            if cost > user_assets.cash:
                await interaction.response.send_message("Insufficient Funds", ephemeral=True)
            else:
                old_bal = user_assets.cash
                await Assets.update_assets(user=user_assets, cash_delta=-cost)
                await Account.update_acct(account=account, main_xp_delta=total_xp.var)
                _embed.add_field(name=f"Transaction Complete",
                                 value=f"Starting Balance: {helper.to_dollars(old_bal)}\nNew Balance: {helper.to_dollars(user_assets.cash)}")
                msg = await interaction.original_response()
                await msg.edit(embed=embed)

        buttons[-2].on_exit = checkout

        view = discord.ui.View()
        for button in buttons:
            view.add_item(button)

        await ctx.send(embed=embed, view=view)

    ## HELPER METHODS
    async def pop_work_timer(self, account, elapsed_time):
        user = await self.bot.fetch_user(account.user_id)
        user_assets = await Assets.fetch(account.user_id)

        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)

        money_earned = elapsed_hours * self.jobs[account.job_title]["salary"]
        xp_earned = int(elapsed_hours * 30)

        await Assets.update_assets(user=user_assets, cash_delta=money_earned)
        await Account.update_acct(account=account, main_xp_delta=xp_earned, shift_start="NULL", shift_length="NULL")

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(77, 199, 222),  # Space Blue
            title=f"Shift for {datetime.datetime.now():%m-%d-%Y}"
        )
        embed.add_field(name="You Earned:", value=f"{helper.to_dollars(money_earned)}\n{xp_earned} xp")

        await user.send(embed=embed)

    ## TASKS
    @tasks.loop(seconds=300)  # Check every 5 minutes
    async def check_work_timers(self):
        await Account.clean_database(self.bot)
        current_time = datetime.datetime.utcnow()
        for account in Account.select().where(Account.shift_start.is_null(False)):
            elapsed_time = (current_time - account.shift_start)
            elapsed_hours = elapsed_time / datetime.timedelta(hours=1)
            logger.debug(f"{account.user_id} | {account.shift_start} | {account.shift_length} | {elapsed_hours}")
            if elapsed_hours >= account.shift_length:
                await self.pop_work_timer(account, elapsed_time)

    @tasks.loop(time=datetime.time(hour=7, minute=0, tzinfo=datetime.timezone.utc))  # 0:00 MST
    async def refresh_daily(self):
        for person in Account.select(Account.user_id, Account.has_redeemed_daily):
            if person.has_redeemed_daily:
                await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False, daily_allocated_bets=175)
            else:
                await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False, daily_allocated_bets=175,
                                          daily_streak=0)

        logger.info("Daily Refresh Executed\n-----------------------------------")

    @check_work_timers.before_loop
    async def before_check_work_timers(self):
        await self.bot.wait_until_ready()

    @refresh_daily.before_loop
    async def before_refresh_daily(self):
        await self.bot.wait_until_ready()
