import datetime

import discord
from discord.ext import commands, tasks

import helper
import settings
from models.account import Account
from models.assets import Assets

logger = settings.logging.getLogger('bot')


async def setup(bot):
    await bot.add_cog(Economy(bot))


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.refresh_daily.start()

    ## COMMANDS
    @commands.command(aliases=['bal', 'b'], brief="Displays asset balance")
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

    @commands.command(aliases=['p'], brief="Displays user profile")
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

    @commands.command(aliases=['lb'], brief="Displays top users")
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

    @commands.command(brief="Grants gift each day")
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
            await Assets.from_entity(user=user_assets, entity_id="GOV", amount=daily_cash * 100)
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

    @commands.command(aliases=['t'], brief="Transfers assets",
                      help="Usage: !transfer [recipient] [amount] <asset_type>")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def transfer(self, ctx, mention, amount_given, asset_given="cash"):
        amount_given = Assets.standardize(asset_given, amount_given)

        receiver_name = (await self.bot.fetch_user(mention[2:-1])).name
        confirmation_text = f"Transfer {Assets.format(asset_given, amount_given)} in {asset_given} to {receiver_name.capitalize()}?"

        msg_txt = await self._transfer_validation(ctx, ctx.author.id, mention[2:-1], amount_given, asset_given,
                                                  confirmation_text=confirmation_text)
        if msg_txt:
            await ctx.send(f"Error: {msg_txt}")
            return

        await self._transfer_execute(ctx.author.id, mention[2:-1], amount_given, asset_given)
        await ctx.send("Transfer complete!")

    @commands.command(aliases=['ex'], brief="Initiates asset exchange",
                      help="Usage: !exchange [recipient] [amount_given] [asset_given] [amount_received] [asset_received]")
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def exchange(self, ctx, mention, amount_given, asset_given, amount_received, asset_received):
        amount_given = Assets.standardize(amount_given, asset_given)
        amount_received = Assets.standardize(amount_received, asset_received)

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
                                                  confirmation_text=receiver_confirm, timeout=600)
        if msg_txt:
            await ctx.send(f"Error: {msg_txt} [Sender <- Receiver]")
            return

        await self._transfer_execute(ctx.author.id, mention[2:-1], amount_given, asset_given)
        await self._transfer_execute(mention[2:-1], ctx.author.id, amount_received, asset_received)

        await ctx.send("Exchange Complete!")

    @commands.command(aliases=["store"], brief="Opens BK menu")
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
                _embed.add_field(name=f"Insufficient Funds",
                                 value=f"Your Balance: {Assets.format('cash', user_assets.cash)}")
                msg = await interaction.original_response()
                await msg.edit(embed=embed)
            else:
                old_bal = user_assets.cash
                await Assets.from_entity(user=user_assets, entity_id="BK", amount=-cost, asset='cash')
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

    @commands.command(brief="Retrieve entity info", help=f"Usage: !edgar [entity_id] <asset_type>")
    async def edgar(self, ctx, entity_id: str = commands.parameter(description=f"Such as: GOV, BK, CASINO"),
                    asset_type: str = "cash"):
        entity_id = entity_id.upper()

        if entity_id == "TERRA" and ctx.author.id != settings.OWNER_ID:
            await ctx.send("`Error: Requested Info With Insufficient Clearance`")
            return

        try:
            entity = await Assets.fetch(id_str=entity_id, is_entity=True)
        except Assets.DoesNotExist:
            await ctx.send("`Error: Invalid Entity ID`")
            return

        balance = getattr(entity, asset_type)

        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            title=f"{entity_id}'s {asset_type.title()} Balance:",
            description=f"# {Assets.format(asset_type, balance)}"
        )
        embed.set_footer(text=f"\nRequested by {ctx.author}")

        await ctx.send(embed=embed)

    ## HELPER METHODS
    @staticmethod
    def daily_ladder(day: int):
        return (((day - 1) % 7) * day) + 50

    async def _transfer_validation(self, ctx, sender_id, receiver_id, amount, asset="cash", confirmation_text=None,
                                   timeout=30):
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

        if not await helper.confirmation_request(ctx, text=confirmation_text, timeout=timeout, user=sender):
            return "Timed Out"

        return

    @staticmethod
    async def _transfer_execute(sender_id, receiver_id, amount, asset):
        await Assets.update_assets(user_id=receiver_id, **{f"{asset}_delta": amount})
        await Assets.update_assets(user_id=sender_id, **{f"{asset}_delta": -amount})

    ## TASKS
    @tasks.loop(time=datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc))  # 2:00 MST (NO DST)
    async def refresh_daily(self):
        for person in Account.select(Account.user_id, Account.has_redeemed_daily):
            if person.has_redeemed_daily:
                await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False, daily_allocated_bets=175)
            else:
                await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False, daily_allocated_bets=175,
                                          daily_streak=0)

        logger.info("Daily Refresh Executed\n-----------------------------------")

    @refresh_daily.before_loop
    async def before_refresh_daily(self):
        await self.bot.wait_until_ready()
