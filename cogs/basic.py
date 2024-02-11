import discord
from discord.ext import commands, tasks
import random
import datetime
import settings

logger = settings.logging.getLogger("bot")


async def setup(bot):
    await bot.add_cog(Basic(bot))


class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # self.eleven_eleven.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if random.randint(0, 30) == 0:
            await message.add_reaction("😂")

    @commands.command()
    async def hello(self, ctx, *, member: discord.Member):
        await ctx.send(f"Hello {member.name}")

    @commands.command(
        aliases=['pang'],
        help="To use ping, simply type !ping or !p",
        description="When pinged, the bot will respond with a pong",
        brief="Responds with pong",
        enabled=True
    )
    async def ping(self, ctx):
        await ctx.send("pong")

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
            await ctx.send(" ".join(what))

    @commands.command()
    async def joined(self, ctx, who: discord.Member):
        await ctx.send(who.joined_at)

    # @tasks.loop(time=[datetime.time(hour=6, minute=11), datetime.time(hour=18, minute=11)])
    # async def eleven_eleven(self):
    #     await discord.Client().get_channel(1087798954525200384).send("11:11!")
    #     logger.info("Just elevened all over the place!")

    @commands.command()
    async def test(self, ctx):
        client = discord.Client()
        channel = client.get_channel(1145891925778513951)
        await channel.send("TEST")

    @commands.command()
    async def snail(self, ctx):
        author = ctx.author
        embed = discord.Embed(
            colour=discord.Colour.dark_green(),
            description="Race to the finish line in this nail biting game of coordination and sabatoge!",
            title="Snail Speedway",
            url="http://snailspeedway.click"
        )
        embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar.url)
        embed.set_author(name="Sir John W. Whoppah")

        await ctx.send(embed=embed)

    @commands.command(aliases=['mb'])
    async def mention_battle(self, ctx, mention):
        await ctx.send(f"You pinged user_id: {mention[2:-1]}")
        await ctx.send(f"Get pinged! {ctx.author.mention}")
