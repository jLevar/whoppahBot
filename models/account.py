import peewee
import settings

accounts_db = peewee.SqliteDatabase("./databases/accounts.db")

logger = settings.logging.getLogger('bot')


class Account(peewee.Model):
    user_id: str = peewee.CharField(max_length=255)
    guild_id: str = peewee.CharField(max_length=255)
    amount: float = peewee.FloatField()

    class Meta:
        database = accounts_db

    @staticmethod
    def fetch(user_id):
        Account.get_or_create(user_id=user_id, defaults={'guild_id': 0, 'amount': 0})
        # try:
        #     return Account.get(user_id=user_id)
        # except BaseException as e:
        #     logger.warning(type(e))
        #     return Account.create(user_id=user_id, guild_id=0, amount=0)

    @staticmethod
    def leaderboard(num_users: int):
        return [user.user_id for user in Account.select().order_by(Account.amount)][:num_users]

    @staticmethod
    def create_account(ctx):
        Account.create(user_id=ctx.message.author.id, guild_id=ctx.message.guild.id, amount=0)

    @staticmethod
    def close_account(ctx):
        acct = Account.get(user_id=ctx.message.author.id)
        acct.delete_instance()

