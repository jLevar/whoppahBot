import discord
from discord.ext import commands


class Dev(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, cog: str):
        await self.bot.load_extension(f"cogs.{cog.lower()}")
        await ctx.send("Loaded successfully")

    @load.error
    async def load_error(self, ctx, error):
        if isinstance(error, commands.errors.NotOwner):
            await ctx.send("Error: Invalid Permissions!")
        elif isinstance(error, commands.errors.CommandInvokeError):
            await ctx.send(f"Error: cog is already loaded")

    @commands.command()
    async def unload(self, ctx, cog: str):
        cog = cog.lower()
        if cog == "dev":
            await ctx.send("You cannot unload the dev cog")
        else:
            await self.bot.unload_extension(f"cogs.{cog}")
            await ctx.send("Unloaded successfully")

    @commands.command()
    async def reload(self, ctx, cog: str):
        await self.bot.reload_extension(f"cogs.{cog.lower()}")
        await ctx.send("Reloaded successfully")


async def setup(bot):
    await bot.add_cog(Dev(bot))
