import peewee
import settings

accounts_db = peewee.SqliteDatabase("./databases/accounts.db")

logger = settings.logging.getLogger('bot')


class Account(peewee.Model):
    user_id: str = peewee.CharField(max_length=255, primary_key=True)
    balance: float = peewee.FloatField()
    job_title: str = peewee.CharField(max_length=255)
    shift_start: float = peewee.DateTimeField()
    shift_length: int = peewee.IntegerField()
    has_redeemed_daily: bool = peewee.BooleanField()
    daily_allocated_bets: int = peewee.IntegerField()

    class Meta:
        database = accounts_db

    @staticmethod
    def fetch(user_id: str):
        account, is_created = Account.get_or_create(user_id=user_id, defaults={
            'balance': 0, 'job_title': "Unemployed", 'has_redeemed_daily': 0, "daily_allocated_bets": 150
        })
        return account

    @staticmethod
    def leaderboard(num_users: int):
        return [user.user_id for user in Account.select().order_by(-Account.balance)][:num_users]

    @staticmethod
    def close_account(ctx):
        acct = Account.get(user_id=ctx.message.author.id)
        acct.delete_instance()

    @staticmethod
    def update_acct(user_id=None, account=None, **kwargs):
        expected_args = ['balance', 'balance_delta', 'job_title', 'shift_start', 'shift_length', 'has_redeemed_daily', 'daily_allocated_bets', 'dab_delta']
        acct = account or Account.fetch(user_id=user_id)

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
