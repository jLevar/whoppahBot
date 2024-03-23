import peewee
from models.base import BaseModel

import helper
import settings

logger = settings.logging.getLogger('bot')


class Account(BaseModel):
    user_id: str = peewee.CharField(primary_key=True, max_length=255)
    job_title: str = peewee.CharField(max_length=255, default="Unemployed")
    shift_start: float = peewee.DateTimeField(null=True)
    shift_length: int = peewee.IntegerField(null=True)
    has_redeemed_daily: bool = peewee.BooleanField(default=0)
    daily_allocated_bets: int = peewee.IntegerField(default=150)
    daily_streak: int = peewee.IntegerField(default=0)
    main_xp: int = peewee.IntegerField(default=0)

    @staticmethod
    async def fetch(user_id: str):
        account, is_created = Account.get_or_create(user_id=user_id)
        return account

    @staticmethod
    async def close_account(user_id: str):
        acct = Account.get(user_id=user_id)
        acct.delete_instance()

    @staticmethod
    async def clean_database(bot):
        for account in Account.select():
            attempts = 0
            while attempts < 6:
                if not await helper.validate_user_id(bot, account.user_id):
                    if attempts < 5:
                        attempts += 1
                        continue
                    else:
                        logger.info(f"REMOVED INVALID ID [{account.user_id}] from accounts.db")
                        account.delete_instance()
                else:
                    break

    @staticmethod
    async def update_acct(user_id=None, account=None, **kwargs):
        expected_args = ['job_title', 'shift_start', 'shift_length', 'has_redeemed_daily',
                         'daily_allocated_bets', 'daily_allocated_bets_delta', 'daily_streak', 'daily_streak_delta',
                         'main_xp', 'main_xp_delta']
        acct = account or await Account.fetch(user_id=user_id)

        for key, value in kwargs.items():
            if key not in expected_args:
                raise AttributeError("Tried updating account with bad argument")

            if value is not None:
                if value == "NULL":
                    value = None

                # Parameters ending in _delta are meant to modify without overwriting existing data
                if key[-6:] == '_delta':
                    curr_data = getattr(acct, key[:-6])
                    setattr(acct, key[:-6], curr_data + value)
                else:
                    setattr(acct, key, value)
        acct.save()
