import peewee

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

    @staticmethod
    async def fetch(id_str: str, is_entity: bool = False):
        if is_entity:
            assets, is_created = Assets.get_or_create(entity_id=id_str)
        else:
            if not await helper.validate_user_id(BaseModel.bot, id_str):
                return
            assets, is_created = Assets.get_or_create(user_id=id_str)
        return assets

    @staticmethod
    async def update_assets(user=None, user_id=None, entity_id=None, **kwargs):
        expected_args = ['cash', 'cash_delta', 'gold', 'gold_delta']

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
        if column == 'cash':
            return [(user.user_id, user.cash) for user in
                    Assets.select().where(Assets.user_id.is_null(False)).order_by(-Assets.cash)][:num_users]
        elif column == 'gold':
            return [(user.user_id, user.gold) for user in
                    Assets.select().where(Assets.user_id.is_null(False)).order_by(-Assets.gold)][:num_users]
        else:
            raise AttributeError("Called Assets.users_by_column() with bad column arg")

    @staticmethod
    def format(asset_type: str, balance: int) -> str:
        balance = int(balance)
        if asset_type == "cash":
            dollars = balance // 100
            cents = balance % 100

            dollar_str = ""
            while dollars > 0:
                dollar_str = f"{dollars % 1000:03}," + dollar_str
                dollars //= 1000

            dollar_str = dollar_str[:-1].lstrip("0") if dollar_str else "0"

            return f"${dollar_str}.{cents:02}"
        elif asset_type == "gold":
            return f"{balance} oz"
        else:
            return f"{balance}"

    @staticmethod
    def standardize(asset_type: str, amount) -> int:
        if asset_type == "cash":
            amount = float(amount) * 100
        return int(amount)

    @staticmethod
    async def from_entity(user, entity_id, amount, asset):
        await Assets.update_assets(entity_id=entity_id, **{f"{asset}_delta": -amount})
        await Assets.update_assets(user=user, **{f"{asset}_delta": amount})
