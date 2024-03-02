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
    def __init__(self, embed, field_index=None, label=None, emoji=None, style=None):
        super().__init__(label=label, emoji=emoji, style=style)

        self.embed = embed
        self.field_index = field_index

        self.tracker_name = self.embed.fields[self.field_index].name
        self.tracker_value = 0

    async def callback(self, interaction):
        self.tracker_value += 1
        self.embed.set_field_at(index=self.field_index, name=self.tracker_name, value=self.tracker_value)
        await interaction.response.edit_message(embed=self.embed)
