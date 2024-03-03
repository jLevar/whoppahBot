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
    def __init__(self, embed, field_index, field_value="<var>", var=0, listeners=None, label=None, emoji=None,
                 style=None):
        super().__init__(label=label, emoji=emoji, style=style)
        self.embed = embed

        self.field_index = field_index
        self.field_name = self.embed.fields[self.field_index].name
        self.field_value = field_value
        self.inline = self.embed.fields[self.field_index].inline

        self.var = var

        if listeners is None:
            listeners = []
        self.listeners = listeners

    # noinspection PyUnresolvedReferences
    async def callback(self, interaction):
        self.var += 1
        self.embed.set_field_at(index=self.field_index, name=self.field_name, value=self.value_format(),
                                inline=self.inline)

        await interaction.response.edit_message(embed=self.embed)

        for listener in self.listeners:
            await listener.on_event(interaction, data={"name": self.field_name, "value": self.var})

    def value_format(self) -> str:
        return self.field_value.replace("<var>", f"{self.var:.2f}" if isinstance(self.var, float) else str(self.var))


class ExitButton(discord.ui.Button):
    def __init__(self, embed, exit_field=None, value_symbol="", label=None, emoji=None, style=None):
        super().__init__(label=label, emoji=emoji, style=style)
        if exit_field is None:
            exit_field = {"name": "", "value": ""}
        self.embed = embed
        self.exit_field = exit_field
        self.value_symbol = value_symbol

    # noinspection PyUnresolvedReferences
    async def callback(self, interaction):
        self.embed.add_field(name=self.exit_field["name"], value=f"{self.value_symbol}{self.exit_field['value']}",
                             inline=False)
        await interaction.response.edit_message(embed=self.embed, view=None)


class ListenerField:
    def __init__(self, embed, name=None, value="<var>", var=0, inline=None):
        self.embed = embed

        self.name = name
        self.value = value
        self.var = var

        self.embed.add_field(name=name, value=self.value_format(), inline=inline)
        self.index = len(self.embed.fields) - 1
        self.inline = inline

    async def on_event(self, interaction, data):
        self.var += self.get_delta(data)
        self.embed.set_field_at(index=self.index, name=self.name, value=self.value_format(), inline=self.inline)
        msg = await interaction.original_response()
        await msg.edit(embed=self.embed)

    @staticmethod
    def get_delta(data):
        return 1

    def value_format(self) -> str:
        return self.value.replace("<var>", f"{self.var:.2f}" if isinstance(self.var, float) else str(self.var))
