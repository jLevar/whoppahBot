from discord.ext import commands
import settings
from models.account import Account

logger = settings.logging.getLogger('bot')


class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def cleanup_timers(cog_instance):
        if hasattr(cog_instance, "check_work_timers") and cog_instance.check_work_timers.is_running():
            cog_instance.check_work_timers.cancel()

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

    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx, cog: str):
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
    async def close_account(self, ctx):
        Account.close_account(ctx)
        await ctx.send("Account Closed!")

    @commands.command()
    @commands.is_owner()
    async def deposit(self, ctx, amount, mention="<@350393195085168650>"):
        account = Account.fetch(mention[2:-1])
        account.balance += float(amount)
        account.save()

    @commands.command(aliases=['cdb'])
    @commands.is_owner()
    async def clean_database(self, ctx):
        # for user in Account.select().where(Account.user_id << 3503931950851686501):
        #     await ctx.send(f"{user.user_id}")
        await ctx.send("This function broke as hell atm!")
        await ctx.send("Data Cleaning Complete!")


async def setup(bot):
    await bot.add_cog(Dev(bot))
