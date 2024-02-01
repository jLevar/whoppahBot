import peewee
import settings

accounts_db = peewee.SqliteDatabase("./databases/accounts.db")

logger = settings.logging.getLogger('bot')


class Account(peewee.Model):
    user_id: str = peewee.CharField(max_length=255)
    guild_id: str = peewee.CharField(max_length=255)
    balance: float = peewee.FloatField()

    class Meta:
        database = accounts_db

    @staticmethod
    def fetch(user_id: str):
        account, is_created = Account.get_or_create(user_id=user_id, defaults={'guild_id': 0, 'amount': 0})
        return account

    @staticmethod
    def leaderboard(num_users: int):
        return [user.user_id for user in Account.select().order_by(-Account.balance)][:num_users]

    @staticmethod
    def close_account(ctx):
        acct = Account.get(user_id=ctx.message.author.id)
        acct.delete_instance()

