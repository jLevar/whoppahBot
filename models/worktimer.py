# import peewee
#
# db = peewee.SqliteDatabase('work_timers.db')
#
# class WorkTimer(peewee.Model):
#     user_id = peewee.IntegerField(unique=True)
#     start_time = peewee.DateTimeField()
#     requested_hours = peewee.FloatField()
#     hourly_rate = peewee.FloatField()
#
#     class Meta:
#         database = db