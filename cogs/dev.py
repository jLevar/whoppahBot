import discord.errors
from discord.ext import commands

import helper
import settings
from cogs import gambling
from models.account import Account

logger = settings.logging.getLogger('bot')


async def setup(bot):
    await bot.add_cog(Dev(bot))


class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def cleanup_timers(cog_instance):
        if hasattr(cog_instance, "check_work_timers") and cog_instance.check_work_timers.is_running():
            cog_instance.check_work_timers.cancel()

        if hasattr(cog_instance, "refresh_daily") and cog_instance.refresh_daily.is_running():
            cog_instance.refresh_daily.cancel()

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, cog: str):
        cog_name = f"cogs.{cog.lower()}"

        if cog_name in self.bot.extensions:
            await ctx.send("Cog Already Loaded")
            return

        await self.bot.load_extension(cog_name)
        await ctx.send("Loaded successfully")

    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx, cog: str):
        cog_name = f"cogs.{cog.lower()}"

        if cog_name == "cogs.dev":
            await ctx.send("You cannot unload the dev cog")
            return

        if cog_name not in self.bot.extensions:
            await ctx.send("Cog not loaded")
            return

        cog_instance = self.bot.get_cog(cog_name[5:].title())
        self.cleanup_timers(cog_instance)

        await self.bot.unload_extension(cog_name)
        await ctx.send("Unloaded successfully")

    @commands.command(aliases=['r'])
    @commands.is_owner()
    async def reload(self, ctx, cog: str):
        if cog == "e":
            cog = "economy"
        cog_name = f"cogs.{cog.lower()}"

        if cog_name == "cogs.dev":
            await self.bot.reload_extension(cog_name)
            await ctx.send("Reloading Dev [Basic Reload | No Cleanup]")
            return

        if cog_name in self.bot.extensions:
            await self.unload(ctx, cog)

        await self.bot.load_extension(cog_name)
        await ctx.send("Reloaded successfully")

    ## ECONOMY
    @commands.command()
    @commands.is_owner()
    async def close_account(self, ctx, mention="<@350393195085168650>"):
        user_id = mention[2:-1]
        if not await helper.validate_user_id(self.bot, user_id):
            await ctx.send("Invalid user_id")
            return

        await Account.close_account(ctx.message.author.id)
        await ctx.send("await Account Closed!")

    @commands.command(aliases=['cd'])
    @commands.is_owner()
    async def change_data(self, ctx, flag: str = None, data=None, mention: str = "<@350393195085168650>"):
        user_id = mention[2:-1]

        if not data:
            await ctx.send("Invalid data argument")
            return

        if flag not in ["-b", "-ds", "-jt", "-xp"]:
            await ctx.send("Invalid flag")
            return

        if not await helper.validate_user_id(self.bot, user_id):
            await ctx.send("Invalid user_id")
            return

        if flag == "-b":
            data = int(data)
            await Account.update_acct(user_id=user_id, balance_delta=data)
        elif flag == "-ds":
            data = int(data)
            await Account.update_acct(user_id=user_id, daily_streak=data)
        elif flag == "-jt":
            data = "Unemployed" if data == "0" else str(data)
            await Account.update_acct(user_id=user_id, job_title=data)
        elif flag == "-xp":
            data = int(data)
            await Account.update_acct(user_id=user_id, main_xp_delta=data)
        else:
            await ctx.send("This block should be unreachable")
            return

        await ctx.send("Successful Gamesharking!")

    @commands.command()
    @commands.is_owner()
    async def gambling_psa(self, ctx, mention="<@350393195085168650>"):
        user_id = mention[2:-1]
        if not await helper.validate_user_id(self.bot, user_id):
            await ctx.send("Invalid user_id")
            return

        user = await self.bot.fetch_user(user_id)
        await gambling.Gambling.send_gambling_psa(user)

    @commands.command()
    @commands.is_owner()
    async def changelog(self, ctx):
        with open(settings.CHANGELOG_PATH, 'r') as file:
            text = file.read().split("\n", 1)

        embed = discord.Embed(
            colour=discord.Colour.blurple(),
            title=f"{text[0]}",
            description=f"{text[1]}"
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["mdr"])
    @commands.is_owner()
    async def manual_daily_reset(self, ctx, flag: str = None):
        if flag == "-m":
            await Account.update_acct(user_id=ctx.author.id, has_redeemed_daily=False)
            await ctx.send("Your daily has been reset")
        elif flag == "-a":
            for person in Account.select(Account.user_id, Account.has_redeemed_daily):
                if person.has_redeemed_daily:
                    await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False,
                                              daily_allocated_bets=175)
                else:
                    await Account.update_acct(user_id=person.user_id, has_redeemed_daily=False,
                                              daily_allocated_bets=175,
                                              daily_streak=0)
            await ctx.send("Everyone's daily has been reset")

    @commands.command()
    @commands.is_owner()
    # Set my daily allocated bets to N
    async def smdabtn(self, ctx, n):
        await Account.update_acct(user_id=ctx.author.id, daily_allocated_bets=n)
        await ctx.send("successfully smdabtn'd")
