from discord.ext import commands


async def setup(bot):
    bot.add_command(math)


@commands.group()
async def math(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"No, {ctx.subcommand_passed} does not belong to math")


@math.group()
async def simple(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f"No, {ctx.subcommand_passed} does not belong to simple")


@simple.command()
async def add(ctx, a: int, b: int):
    await ctx.send(a + b)


@add.error
async def add_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("handled error locally")


@simple.command()
async def subtract(ctx, a: int, b: int):
    await ctx.send(a - b)


