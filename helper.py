import asyncio

import discord
from PIL import Image, ImageDraw


async def validate_user_id(bot, ctx, user_id):
    try:
        await bot.fetch_user(user_id)
    except discord.errors.HTTPException as e:
        await ctx.send(f"{type(e)}\nError: Invalid Mention")
        return False
    return True


async def embed_edit(embed, msg, append: str, sleep: int = 0, color: discord.Colour = None):
    if color:
        embed.colour = color

    embed.description += append
    await msg.edit(embed=embed)

    if sleep > 0:
        await asyncio.sleep(sleep)
