import datetime
import random

import discord
from discord.ext import commands, tasks

import helper
import settings

logger = settings.logging.getLogger("bot")


async def setup(bot):
    await bot.add_cog(Basic(bot))


class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.eleven_eleven.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if "burger" in message.content and random.randint(0, 20) == 15:
            await message.add_reaction("😂")

    @commands.command()
    async def joke(self, ctx):
        await ctx.send("How many doctors does it take to screw in a lightbulb? Two, one to screw it in and the other to"
                       " hold the ladder 😂😂😂😂😂😂😂😂")
        await ctx.message.author.send("Please don't ask me to tell any more jokes, it's so embarrassing")

    @commands.command()
    async def say(self, ctx, *what):
        if what == "@everyone":
            await ctx.send("not cool!")
        elif what == ():
            # NOTE - This error message is a prank DM
            with open("error_message.txt", "r") as f:
                error_message = f.read()
            await ctx.message.author.send(error_message)
        else:
            await ctx.send(f"> {' '.join(what)}\n-{ctx.message.author}")

    @tasks.loop(time=datetime.time(hour=18, minute=11))
    async def eleven_eleven(self):
        drumbledwarf = await self.bot.fetch_user("350393195085168650")
        await drumbledwarf.send("11:11!")
        logger.info("11:11!")

    @commands.command()
    async def suggestion(self, ctx):
        embed = discord.Embed(
            colour=discord.Colour.purple(),
            title="Have a suggestion for a new feature or change?",
            description="Fill out this form to let us know!\nhttps://forms.gle/hE3A4Neiia3njCJV7"
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        await ctx.send(embed=embed)

    @commands.command()
    async def github(self, ctx):
        embed = discord.Embed(
            colour=discord.Colour.orange(),
            title="Curious about how Whoppah Bot works?",
            description="It's all open source on GitHub!\nhttps://github.com/jLevar/whoppahBot"
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        await ctx.send(embed=embed)

    @commands.command()
    async def bug(self, ctx):
        embed = discord.Embed(
            colour=discord.Colour.dark_purple(),
            title="Experienced a bug or technical issue?",
            description="Fill out this form to get it resolved as quickly as possible!\nhttps://forms.gle/jwEGTjM11jDakSQA7"
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        await ctx.send(embed=embed)

    @commands.command(aliases=['whoppah'])
    async def whoppa(self, ctx):
        await ctx.send("https://tenor.com/view/whoppa-whoppah-did-you-get-a-whoppa-woppa-whopper-gif-23161878")

    @commands.command()
    async def tutorial(self, ctx):
        await ctx.send("This command gives users a starting tutorial!")

