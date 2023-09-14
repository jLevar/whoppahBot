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
        try:
            return Account.get(user_id=user_id)
        except BaseException as e:
            logger.warning(type(e))
            return Account.create(user_id=user_id, guild_id=0, amount=0)

    @staticmethod
    def create_account(message):
        Account.create(user_id=message.author.id, guild_id=message.guild.id, amount=0)

