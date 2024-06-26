import datetime
import random

import discord
from discord.ext import commands, tasks

import helper
import settings
from models.account import Account
from models.assets import Assets

logger = settings.logging.getLogger('bot')


async def setup(bot):
    await bot.add_cog(Actions(bot))


class Actions(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.jobs = {
            "Unemployed": {"salary": 0, "requirements": {"balance": 0, "xp": 0}},
            "Dishwasher": {"salary": 725, "requirements": {"balance": 0, "xp": 0}},
            "Burger Flipper": {"salary": 1350, "requirements": {"balance": 75000, "xp": 2500}},
            "Grill Master": {"salary": 1675, "requirements": {"balance": 500000, "xp": 15000}},
            "Shift Lead": {"salary": 2000, "requirements": {"balance": 2500000, "xp": 50000}}
        }
        self.check_action_times.start()

    ## COMMANDS
    @commands.command(brief="Shows action status")
    async def status(self, ctx):
        account = await Account.fetch(ctx.author.id)
        if account.action_start is not None:
            await self.send_action_status(ctx, account)
        else:
            await ctx.reply("You currently aren't performing any action", mention_author=False)

    @commands.command(brief="Cancels current action")
    async def cancel(self, ctx):
        user_id = ctx.author.id
        user = await self.bot.fetch_user(user_id)
        account = await Account.fetch(user_id)

        if not account.action_start:
            await ctx.reply("You weren't doing anything to begin with!", mention_author=False)
            return

        elapsed_time = (datetime.datetime.utcnow() - account.action_start)
        elapsed_seconds = elapsed_time / datetime.timedelta(seconds=1)

        if elapsed_seconds < 10:
            await ctx.reply(f"Please wait at least 10 seconds before cancelling action ({elapsed_seconds:.2}s)",
                            mention_author=False)
            return

        if not await helper.confirmation_request(ctx, text=f"Cancel action '{account.action_type}'?", timeout=20,
                                                 user=user):
            return

        await self.pop_actions(account, elapsed_time)

    @commands.command(aliases=['w'], brief="Starts BK shift", help="Usage: !work [Shift Duration (hours)]")
    async def work(self, ctx, num_hours: int = 0):
        user_id = ctx.author.id
        account = await Account.fetch(user_id)

        if account.job_title == "Unemployed":
            await ctx.reply("You can't work until you are hired!\n*(Hint: Try !promotion)*", mention_author=False)
            return

        if account.action_start is not None:
            await ctx.reply("You are already performing an action!", mention_author=False)
            await self.send_action_status(ctx, account)
            return

        if num_hours < 1:
            await ctx.reply("You have to work at least 1 hour to get paid!", mention_author=False)
            return

        if num_hours > 24:
            await ctx.reply("You cannot work more than 24 hours in a single shift!", mention_author=False)
            return

        await Account.update_acct(account=account, action_start=datetime.datetime.utcnow(), action_length=num_hours,
                                  action_type="work")

        await ctx.reply("You started working!", mention_author=False)

    @commands.command(brief="Requests BK promotion")
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

    @commands.command(aliases=['m'], brief="Starts gold dig", help="Usage: !mine [Action Duration (hours)]")
    async def mine(self, ctx, num_hours: int = 0):
        user_id = ctx.author.id
        account = await Account.fetch(user_id)

        if account.action_start is not None:
            await ctx.reply("You are already performing an action!", mention_author=False)
            await self.send_action_status(ctx, account)
            return

        if num_hours < 1:
            await ctx.reply("You aughta mine fer at least an hour if yer expectin' any gold or such!",
                            mention_author=False)
            return

        if num_hours > 24:
            await ctx.reply("Ev'n da finest prospectors inda West can't mine fer longer than uhday!",
                            mention_author=False)
            return

        await Account.update_acct(account=account, action_start=datetime.datetime.utcnow(), action_length=num_hours,
                                  action_type="mine")

        await ctx.reply("You started mining!", mention_author=False)

    ## HELPER METHODS
    async def work_result(self, account, elapsed_time):
        user = await self.bot.fetch_user(account.user_id)
        user_assets = await Assets.fetch(account.user_id)

        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)

        money_earned = elapsed_hours * self.jobs[account.job_title]["salary"]
        xp_earned = int(elapsed_hours * 30)

        await Assets.from_entity(user=user_assets, entity_id="BK", amount=money_earned, asset='cash')
        await Account.update_acct(account=account, main_xp_delta=xp_earned)

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(77, 199, 222),  # Space Blue
            title=f"Shift for {datetime.datetime.now():%m-%d-%Y}"
        )

        embed.add_field(name="You Earned:", value=f"{Assets.format('cash', money_earned)}\n{xp_earned} xp")
        await user.send(embed=embed)

    async def mine_result(self, account, elapsed_time):
        user = await self.bot.fetch_user(account.user_id)
        user_assets = await Assets.fetch(account.user_id)

        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)

        xp_earned = int(elapsed_hours * 21)

        gold_rate = 12.5
        silver_rate = 34

        gold_earned, silver_earned = 0, 0
        for i in range(int(elapsed_hours)):
            if random.randrange(100) < gold_rate:
                gold_earned += 1
            if random.randrange(100) < silver_rate:
                silver_earned += 1

        await Assets.from_entity(user=user_assets, entity_id="TERRA", amount=gold_earned, asset='gold')
        await Assets.from_entity(user=user_assets, entity_id="TERRA", amount=silver_earned, asset='silver')
        await Account.update_acct(account=account, main_xp_delta=xp_earned)

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(153, 101, 21),  # Golden Brown
            title=f"Dig of {datetime.datetime.now():%m-%d-%Y}"
        )

        embed.add_field(name="You Earned:", value=f"{Assets.format('gold', gold_earned)} gold\n"
                                                  f"{Assets.format('silver', silver_earned)} silver\n{xp_earned} XP")
        await user.send(embed=embed)

    async def pop_actions(self, account, elapsed_time):
        action_type = account.action_type
        if action_type == "work":
            await self.work_result(account, elapsed_time)
        elif action_type == "mine":
            await self.mine_result(account, elapsed_time)
        await Account.update_acct(account=account, action_start="NULL", action_length="NULL", action_type="NULL")

    async def send_action_status(self, ctx, account):
        elapsed_time = (datetime.datetime.utcnow() - account.action_start)
        elapsed_hours = elapsed_time / datetime.timedelta(hours=1)
        percent_left = (elapsed_hours / account.action_length)

        if percent_left > 1:
            await ctx.reply("Your action just finished!", mention_author=False)
            await self.pop_actions(account, elapsed_time)
            return

        blank_bar = "# [----------------]"
        progress_bar = blank_bar.replace("-", "#", int(blank_bar.count("-") * percent_left))
        elapsed_seconds = elapsed_time / datetime.timedelta(seconds=1)
        et, eu = await self.convert_time(elapsed_seconds, "seconds")

        embed = discord.Embed(
            title=f"{account.action_type.title()} {(percent_left * 100):.2f}% complete",
            colour=discord.Colour.blue(),
            description=progress_bar
        )
        embed.set_footer(text=f"{et:.2f} {eu} out of {account.action_length} hr(s)")
        await ctx.send(embed=embed)

    @staticmethod
    async def convert_time(time, units="seconds"):
        for i in range(2):
            if time >= 60:
                time /= 60
                units = "minutes" if units == "seconds" else "hours"
        return time, units

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
                try:
                    await self.pop_actions(account, elapsed_time)
                except discord.Forbidden:
                    logger.warning(f"CAN'T DM USER={account.user_id} | REMOVING ACTION FROM DATABASE")
                    await Account.update_acct(account=account, action_start="NULL", action_length="NULL",
                                              action_type="NULL")
                except Exception as e:
                    logger.warning(
                        f"ENCOUNTERED MISCELLANEOUS ERROR ON USER={account.user_id} | {e} | REMOVING ACTION FROM DATABASE")
                    await Account.update_acct(account=account, action_start="NULL", action_length="NULL",
                                              action_type="NULL")

    @check_action_times.before_loop
    async def before_check_action_times(self):
        await self.bot.wait_until_ready()

    ## DEV COMMANDS
    @commands.command(hidden=True)
    @commands.is_owner()
    async def clear_all_actions(self, ctx):
        for account in Account.select().where(Account.action_start.is_null(False)):
            await self.pop_actions(account, datetime.timedelta(hours=account.action_length))
        await ctx.reply("Cleared all actions!")
