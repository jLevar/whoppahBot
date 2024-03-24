import asyncio
import discord
import datetime


async def safe_shutdown(bot):
    await bot.close()


async def validate_user_id(bot, user_id):
    try:
        await bot.fetch_user(user_id)
    except discord.errors.HTTPException:
        return False
    return True


### EMBED LIBRARY ###
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


### 'DISCORD.PY PLUS' ###

class SecureButton(discord.ui.Button):
    def __init__(self, ctx, label=None, emoji=None, style=None):
        super().__init__(label=label, emoji=emoji, style=style)
        self.ctx = ctx
        self.pressed = False

    async def verify_user(self, interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Please don't interact with other users' buttons", ephemeral=True)
            return False
        return True

    async def callback(self, interaction):
        if not await self.verify_user(interaction):
            return False

        self.pressed = True
        return True


class TrackerButton(SecureButton):
    def __init__(self, ctx, embed, field_index, field_value="<var>", var=0, listeners=None, label=None, emoji=None,
                 style=None):
        super().__init__(ctx=ctx, label=label, emoji=emoji, style=style)
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
        if not await super().callback(interaction):
            return

        self.var += 1
        self.embed.set_field_at(index=self.field_index, name=self.field_name, value=self.value_format(),
                                inline=self.inline)
        await interaction.response.edit_message(embed=self.embed)

        for listener in self.listeners:
            await listener.on_event(interaction, data={"name": self.field_name, "value": self.var})

    def value_format(self) -> str:
        return self.field_value.replace("<var>", f"{self.var:.2f}" if isinstance(self.var, float) else str(self.var))


class ExitButton(SecureButton):
    def __init__(self, ctx, embed, exit_field: {} = None, value_symbol="", label=None, emoji=None, style=None):
        super().__init__(ctx=ctx, label=label, emoji=emoji, style=style)
        self.embed = embed
        self.exit_field = exit_field
        self.value_symbol = value_symbol

    # noinspection PyUnresolvedReferences
    async def callback(self, interaction):
        if not await super().callback(interaction):
            return

        await interaction.response.defer()
        await self.on_exit(interaction, self.embed)

        if self.exit_field:
            self.embed.add_field(name=self.exit_field["name"], value=f"{self.value_symbol}{self.exit_field['value']}",
                                 inline=False)

        msg = await interaction.original_response()
        await msg.edit(embed=self.embed, view=None)

    @staticmethod
    async def on_exit(interaction, _embed):
        return


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
        return self.value.replace("<var>", str(self.var))


async def confirmation_request(ctx, text: str = "Proceed?", timeout=60):
    embed = discord.Embed(
        colour=discord.Colour.lighter_grey(),
        title="Confirmation Request",
        description=text
    )

    buttons = [
        SecureButton(ctx, emoji="✔", style=discord.ButtonStyle.success),
        SecureButton(ctx, emoji="✖", style=discord.ButtonStyle.danger),
    ]

    view = discord.ui.View()
    for button in buttons:
        view.add_item(button)

    msg = await ctx.send(embed=embed, view=view)

    start_time = datetime.datetime.now()

    while datetime.datetime.now() - start_time < datetime.timedelta(seconds=timeout):
        if buttons[0].pressed:
            embed.set_footer(text="Action Confirmed")
            await msg.edit(embed=embed, view=None)
            return True
        elif buttons[1].pressed:
            embed.set_footer(text="Action Denied")
            await msg.edit(embed=embed, view=None)
            return False
        else:
            await asyncio.sleep(1)

    embed.set_footer(text=f"Confirmation Request Timed Out ({timeout}s)")
    await msg.edit(embed=embed, view=None)
    return False
