from peewee import *

database = SqliteDatabase('story.db')


class BaseModel(Model):
    class Meta:
        database = database


class Asset(BaseModel):
    data = TextField()
    meta = TextField()


class Localization(BaseModel):
    text = TextField()


class Entity(BaseModel):
    name = ForeignKeyField(Localization, backref='entities')
    preview = ForeignKeyField(Asset, backref='entities')


class Dialogue(BaseModel):
    name = ForeignKeyField(Localization, backref='dialogues')


class DialogueSpeaker(BaseModel):
    dialogue = ForeignKeyField(Dialogue, backref='speakers', on_delete='CASCADE')
    speaker = ForeignKeyField(Entity, backref='dialogues', on_delete='CASCADE')


class Fragment(BaseModel):
    dialogue = ForeignKeyField(Dialogue, backref='fragments', on_delete='CASCADE')
    speaker = ForeignKeyField(Entity, backref='fragments', on_delete='CASCADE')
    text = ForeignKeyField(Localization, backref='fragments')


class FragmentConnection(BaseModel):
    source = ForeignKeyField(Fragment, backref='outputs', on_delete='CASCADE')
    target = ForeignKeyField(Fragment, backref='inputs', on_delete='CASCADE')


def initialize_database():
    with database:
        database.create_tables([
            Asset,
            Localization,
            Entity,
            Dialogue,
            DialogueSpeaker,
            Fragment,
            FragmentConnection,
        ])


if __name__ == '__main__':
    initialize_database()
