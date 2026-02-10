from peewee import (
    SqliteDatabase,
    Model,
    CharField,
    IntegerField,
    AutoField,
    ForeignKeyField,
)

from config_data.config import DB_PATH

db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    id = IntegerField(primary_key=True)


class Station(BaseModel):
    title = CharField(unique=False)
    code = CharField()  # yandex_code
    transport_type = CharField()

    class Meta:
        indexes = (
            (("title",), False),
            (("transport_type",), False),
        )


class Search(BaseModel):
    search_id = AutoField()
    user = ForeignKeyField(User, backref="history")

    search_type = CharField()
    departure_station = CharField()
    arrival_station = CharField()
    date = CharField(null=True)
    transport = CharField()

    def __str__(self):
        if self.search_type == "routes_between":
            return "{search_id}. Рейсы на {transport} {from_station} - {to_station} на {date}".format(
                search_id=self.search_id,
                from_station=self.departure_station,
                to_station=self.arrival_station,
                date=self.date,
                transport=self.transport,
            )

        if self.search_type == "route_stations":
            return "{search_id}. Маршрут для: {transport} {from_station} - {to_station}".format(
                search_id=self.search_id,
                from_station=self.departure_station,
                to_station=self.arrival_station,
                transport=self.transport,
            )


def create_tables():
    db.connect(reuse_if_open=True)
    db.create_tables([User, Station, Search])
    db.close()
