import asyncio
import discord


async def validate_user_id(bot, ctx, user_id):
    try:
        await bot.fetch_user(user_id)
    except discord.errors.HTTPException:
        return False
    return True


async def embed_edit(embed, msg, append: str = "", sleep: int = 0, color: discord.Colour = None, footer: str = ""):
    if color:
        embed.colour = color

    if footer:
        embed.set_footer(text=footer)

    if append:
        embed.description += append

    await msg.edit(embed=embed)

    if sleep > 0:
        await asyncio.sleep(sleep)


class TrackerButton(discord.ui.Button):
    def __init__(self, label=None, emoji=None, style=None):
        super().__init__(label=label, emoji=emoji, style=style)
        self.tracker = 0

    async def callback(self, interaction):
        self.tracker += 1
        embed = interaction.message.embeds[0]
        embed.description = embed.description[:embed.description.index("\u200b") + 1] + f"{self.tracker}"
        await interaction.response.edit_message(embed=embed)
