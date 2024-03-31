import peewee

db = peewee.SqliteDatabase('./data.db')


class BaseModel(peewee.Model):
    class Meta:
        database = db
