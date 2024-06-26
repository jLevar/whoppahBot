import re

import peewee
from discord.ext import commands

import helper
from models.base import BaseModel
from models.account import Account


class UnsignedIntegerField(peewee.IntegerField):
    field_type = 'int unsigned'


# noinspection PyTypeChecker
class Assets(BaseModel):
    user: str = peewee.ForeignKeyField(Account, to_field='user_id', null=True)
    entity_id: str = peewee.CharField(max_length=255, null=True)
    cash: int = UnsignedIntegerField(default=0)
    gold: int = UnsignedIntegerField(default=0)
    silver: int = UnsignedIntegerField(default=0)

    @staticmethod
    async def fetch(id_str: str, is_entity: bool = False):
        if is_entity:
            assets = Assets.get(entity_id=id_str)
        else:
            if not await helper.validate_user_id(BaseModel.bot, id_str):
                return
            assets, is_created = Assets.get_or_create(user_id=id_str)
        return assets

    @staticmethod
    async def create_entity(entity_id):
        Assets.create(entity_id=entity_id)

    @staticmethod
    async def update_assets(user=None, user_id=None, entity_id=None, **kwargs):
        expected_args = ['cash', 'cash_delta', 'gold', 'gold_delta', 'silver', 'silver_delta']

        assets = user or await Assets.fetch(user_id)
        if not assets:
            assets = await Assets.fetch(entity_id, is_entity=True)

        for key, value in kwargs.items():
            if key not in expected_args:
                raise AttributeError("Tried updating account with bad argument")

            if value is not None:
                if value == "NULL":
                    value = None

                # Parameters ending in _delta are meant to modify without overwriting existing data
                if key[-6:] == '_delta':
                    curr_data = getattr(assets, key[:-6])
                    setattr(assets, key[:-6], curr_data + value)
                else:
                    setattr(assets, key, value)
        assets.save()

    @staticmethod
    async def top_users(num_users: int, column="cash"):
        if column not in Assets._meta.fields:  # Check if column exists in model
            raise commands.errors.BadArgument("Invalid column name")

        column_attr = getattr(Assets, column)
        query = Assets.select().where(Assets.user_id.is_null(False)).order_by(-column_attr)

        return [(user.user_id, getattr(user, column)) for user in query][:num_users]

    @staticmethod
    def format(asset_type: str, balance) -> str:
        balance = int(balance)
        if asset_type == "cash":
            dollars = balance // 100
            cents = balance % 100
            return f"${dollars:,}.{cents:02}"
        elif asset_type == "gold" or asset_type == "silver":
            return f"{balance:,} oz"
        else:
            return f"{balance:,}"

    @staticmethod
    def standardize(asset_type: str, amount) -> int:
        if asset_type == "cash":
            amount = re.sub("[^0-9.]+", "", amount)
            return int(float(amount) * 100)
        else:
            amount = re.sub("[^0-9]+", "", amount)
            return int(amount)

    @staticmethod
    async def from_entity(user, entity_id, amount, asset="cash"):
        await Assets.update_assets(entity_id=entity_id, **{f"{asset}_delta": -amount})
        await Assets.update_assets(user=user, **{f"{asset}_delta": amount})
