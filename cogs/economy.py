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
        self.check_action_times.start()
        self.refresh_daily.start()

    ## COMMANDS
    @commands.command(aliases=['bal', 'b'])
    async def balance(self, ctx, asset_type: str = "cash", mention: str = None):
        user_id = mention[2:-1] if mention else ctx.author.id
        user_assets = await Assets.fetch(user_id)
        user = await self.bot.fetch_user(user_id)
        balance = getattr(user_assets, asset_type)

        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            title=f"{asset_type.title()} Balance: {Assets.format(asset_type, balance)}",
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
            description=f"Balance: {Assets.format('cash', user_assets.cash)}\nJob Title: {user_acc.job_title}\nDaily Streak: {user_acc.daily_streak}"
                        f"\nXP: {user_acc.main_xp}\nGold: {Assets.format('gold', user_assets.gold)}"
        )
        embed.set_author(name=f"{user.name.capitalize()}", icon_url=user.display_avatar.url)
        embed.set_footer(text=f"\nRequested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx, sort_asset="cash"):
        embed = discord.Embed(
            colour=discord.Colour.dark_green(),
            title=f"Top 10 Users by {sort_asset.title()}",
            description=""
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        for i, user_data in enumerate(await Assets.top_users(10, column=sort_asset)):
            user_id = user_data[0]
            user_value = user_data[1]
            user = await self.bot.fetch_user(user_id)

            if user.id == ctx.author.id:
                embed.description += f"**{i + 1} |\t{user.name} -- {Assets.format(sort_asset, user_value)}**\n"
            else:
                embed.description += f"{i + 1} |\t{user.name} -- {Assets.format(sort_asset, user_value)}\n"

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
        await helper.embed_edit(embed, msg, footer="Refreshes at 8:00 UTC")

    @staticmethod
    def daily_ladder(day: int):
        return (((day - 1) % 7) * day) + 50

    @commands.command(aliases=['t'], help="Usage: !transfer [recipient] [amount] <asset_type>")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def transfer(self, ctx, mention, amount_given, asset_given="cash"):
        amount_given = self._transfer_standardize(amount_given, asset_given)

        receiver_name = (await self.bot.fetch_user(mention[2:-1])).name
        confirmation_text = f"Transfer {Assets.format(asset_given, amount_given)} in {asset_given} to {receiver_name.capitalize()}?"

        msg_txt = await self._transfer_validation(ctx, ctx.author.id, mention[2:-1], amount_given, asset_given,
                                                  confirmation_text=confirmation_text)
        if msg_txt:
            await ctx.send(f"Error: {msg_txt}")
            return

        await self._transfer_execute(ctx.author.id, mention[2:-1], amount_given, asset_given)
        await ctx.send("Transfer complete!")

    @staticmethod
    def _transfer_standardize(amount, asset) -> int:
        if asset == "cash":
            amount = float(amount) * 100
        return int(amount)

    async def _transfer_validation(self, ctx, sender_id, receiver_id, amount, asset="cash", confirmation_text=None):
        if amount <= 0:
            return "Sorry, you can't transfer with amount <= 0!"

        sender = await self.bot.fetch_user(sender_id)
        sender_data = await Assets.fetch(sender_id)
        receiver = await self.bot.fetch_user(receiver_id)

        if getattr(sender_data, asset) < amount:
            return "Insufficient Funds"

        if sender == receiver:
            return "You cannot transfer money to self"

        if not receiver:
            return "Recipient Unknown"

        if not await helper.confirmation_request(ctx, text=confirmation_text, timeout=60, user=sender):
            return

        return

    @staticmethod
    async def _transfer_execute(sender_id, receiver_id, amount, asset):
        await Assets.update_assets(user_id=receiver_id, **{f"{asset}_delta": amount})
        await Assets.update_assets(user_id=sender_id, **{f"{asset}_delta": -amount})

    @commands.command(aliases=['ex'],
                      help="Usage: !exchange [recipient] [amount_given] [asset_given] [amount_received] [asset_received]")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def exchange(self, ctx, mention, amount_given, asset_given, amount_received, asset_received):
        amount_given = self._transfer_standardize(amount_given, asset_given)
        amount_received = self._transfer_standardize(amount_received, asset_received)

        # Sender Confirmation
        sender_confirm = f"<@{ctx.author.id}>\n***You* give**:\n{Assets.format(asset_given, amount_given)} in {asset_given}" \
                         f"\n\n**They give:**\n{Assets.format(asset_received, amount_received)} in {asset_received}"

        msg_txt = await self._transfer_validation(ctx, ctx.author.id, mention[2:-1], amount_given, asset_given,
                                                  confirmation_text=sender_confirm)
        if msg_txt:
            await ctx.send(f"Error: {msg_txt} [Sender -> Receiver]")
            return

        # Receiver Confirmation
        receiver_confirm = f"{mention}\n***You* give:**\n{Assets.format(asset_received, amount_received)} in {asset_received}" \
                           f"\n\n**They give:**\n{Assets.format(asset_given, amount_given)} in {asset_given}"

        msg_txt = await self._transfer_validation(ctx, mention[2:-1], ctx.author.id, amount_received, asset_received,
                                                  confirmation_text=receiver_confirm)
        if msg_txt:
            await ctx.send(f"Error: {msg_txt} [Sender <- Receiver]")
            return

        await self._transfer_execute(ctx.author.id, mention[2:-1], amount_given, asset_given)
        await self._transfer_execute(mention[2:-1], ctx.author.id, amount_received, asset_received)

        await ctx.send("Exchange Complete!")

    @commands.group(invoke_without_command=True, aliases=['w'], help="Usage: !work [Shift Duration (hours)]")
    async def work(self, ctx, num_hours: int = 0):
        user_id = ctx.author.id
        account = await Account.fetch(user_id)

        if account.job_title == "Unemployed":
            await ctx.send("You can't work until you are hired!\n*(Hint: Try !promotion)*")
            return

        if account.action_start is not None:
            await self.send_action_status(ctx, account)
            return

        if num_hours < 1:
            await ctx.send("You have to work at least 1 hour to get paid!")
            return

        if num_hours > 24:
            await ctx.send("You cannot work more than 24 hours in a single shift!")
            return

        await Account.update_acct(account=account, action_start=datetime.datetime.utcnow(), action_length=num_hours,
                                  action_type="work")

        await ctx.send("You started working!")

    @commands.command()
    async def cancel(self, ctx):
        user_id = ctx.author.id
        user = await self.bot.fetch_user(user_id)
        account = await Account.fetch(user_id)

        if not account.action_start:
            await ctx.send("You weren't doing anything to begin with!")
            return

        elapsed_time = (datetime.datetime.utcnow() - account.action_start)
        elapsed_seconds = elapsed_time / datetime.timedelta(seconds=1)

        if elapsed_seconds < 10:
            await ctx.send(f"Please wait at least 10 seconds before cancelling action ({elapsed_seconds:.2}s)")
            return

        if not await helper.confirmation_request(ctx, text=f"Cancel action '{account.action_type}'?", timeout=20,
                                                 user=user):
            return

        await self.pop_action_time(account, elapsed_time)

    @commands.command(aliases=['m'], help="Usage: !mine [Action Duration (hours)]")
    async def mine(self, ctx, num_hours: int = 0):
        user_id = ctx.author.id
        account = await Account.fetch(user_id)

        if account.action_start is not None:
            await self.send_action_status(ctx, account)
            return

        if num_hours < 8:
            await ctx.send("You aughta mine fer at least 8 hours if yer expectin' gold!")
            return

        if num_hours > 24:
            await ctx.send("Ev'n da finest prospectors inda West can't mine fer longer than uhday!")
            return

        await Account.update_acct(account=account, action_start=datetime.datetime.utcnow(), action_length=num_hours,
                                  action_type="mine")

        await ctx.send("You started mining!")

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
                                    append=f"Your salary is now: {Assets.format('cash', self.jobs[next_job]['salary'])} an hour!\n\n")
        else:
            await helper.embed_edit(embed, msg,
                                    append="Sorry, but we will not be moving forward with your promotion at this time.",
                                    sleep=2)
            await helper.embed_edit(embed, msg,
                                    footer=f"Hint: you need {Assets.format('cash', requirements['balance'])} and {requirements['xp']}xp to get the next job")

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
            return self.value.replace("<var>", f"{Assets.format('cash', self.var)}")

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
                                 value=f"Starting Balance: {Assets.format('cash', old_bal)}\n"
                                       f"New Balance: {Assets.format('cash', user_assets.cash)}")
                msg = await interaction.original_response()
                await msg.edit(embed=embed)

        buttons[-2].on_exit = checkout

        view = discord.ui.View()
        for button in buttons:
            view.add_item(button)

        await ctx.send(embed=embed, view=view)

    ## HELPER METHODS
    async def pop_work_time(self, account, elapsed_time):
        user = await self.bot.fetch_user(account.user_id)
        user_assets = await Assets.fetch(account.user_id)

        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)

        money_earned = elapsed_hours * self.jobs[account.job_title]["salary"]
        xp_earned = int(elapsed_hours * 30)

        await Assets.update_assets(user=user_assets, cash_delta=money_earned)
        await Account.update_acct(account=account, main_xp_delta=xp_earned)

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(77, 199, 222),  # Space Blue
            title=f"Shift for {datetime.datetime.now():%m-%d-%Y}"
        )

        embed.add_field(name="You Earned:", value=f"{Assets.format('cash', money_earned)}\n{xp_earned} xp")
        await user.send(embed=embed)

    async def pop_mine_time(self, account, elapsed_time):
        user = await self.bot.fetch_user(account.user_id)
        user_assets = await Assets.fetch(account.user_id)

        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)

        gold_rate = 0.125
        gold_earned = elapsed_hours * gold_rate
        xp_earned = int(elapsed_hours * 21)

        await Assets.update_assets(user=user_assets, gold_delta=gold_earned)
        await Account.update_acct(account=account, main_xp_delta=xp_earned)

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(153, 101, 21),  # Golden Brown
            title=f"Dig of {datetime.datetime.now():%m-%d-%Y}"
        )

        embed.add_field(name="You Earned:", value=f"{Assets.format('gold', gold_earned)} gold\n{xp_earned} XP")
        await user.send(embed=embed)

    async def pop_action_time(self, account, elapsed_time):
        action_type = account.action_type
        if action_type == "work":
            await self.pop_work_time(account, elapsed_time)
        elif action_type == "mine":
            await self.pop_mine_time(account, elapsed_time)
        await Account.update_acct(account=account, action_start="NULL", action_length="NULL", action_type="NULL")

    async def send_action_status(self, ctx, account):
        elapsed_time = (datetime.datetime.utcnow() - account.action_start)
        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)
        percent_left = (elapsed_hours / account.action_length)

        if percent_left > 1:
            await self.pop_action_time(account, elapsed_time)
            return

        blank_bar = "# [----------------]"
        progress_bar = blank_bar.replace("-", "#", int(blank_bar.count("-") * percent_left))
        elapsed_seconds = elapsed_time / datetime.timedelta(seconds=1)
        et, eu = await convert_time(elapsed_seconds, "seconds")

        embed = discord.Embed(
            title=f"{account.action_type.title()} {(percent_left * 100):.2f}% complete",
            colour=discord.Colour.blue(),
            description=progress_bar
        )
        embed.set_footer(text=f"{et:.2f} {eu} out of {account.action_length} hr(s)")
        await ctx.send(embed=embed)

    ## TASKS
    @tasks.loop(seconds=300)  # Check every 5 minutes
    async def check_action_times(self):
        current_time = datetime.datetime.utcnow()
        for account in Account.select().where(Account.action_start.is_null(False)):
            elapsed_time = (current_time - account.action_start)
            elapsed_hours = elapsed_time / datetime.timedelta(hours=1)
            logger.debug(f"{account.user_id} | {account.action_type} | "
                         f"{account.action_start} | {account.action_length} | {elapsed_hours}")
            if elapsed_hours >= account.action_length:
                await self.pop_action_time(account, elapsed_time)

    @tasks.loop(time=datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc))  # 2:00 MST (NO DST)
    async def refresh_daily(self):
        for person in Account.select(Account.user_id, Account.has_redeemed_daily):
            if person.has_redeemed_daily:
                await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False, daily_allocated_bets=175)
            else:
                await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False, daily_allocated_bets=175,
                                          daily_streak=0)

        logger.info("Daily Refresh Executed\n-----------------------------------")

    @check_action_times.before_loop
    async def before_check_action_times(self):
        await self.bot.wait_until_ready()

    @refresh_daily.before_loop
    async def before_refresh_daily(self):
        await self.bot.wait_until_ready()
