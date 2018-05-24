from umongo import Document
from umongo.fields import StringField, IntegerField, DictField

from app import app


instance = app.config["LAZY_UMONGO"]


@instance.register
class GameServer(Document):
    host = StringField(allow_none=False, required=True)
    port = IntegerField(allow_none=False, required=True)
    available_slots = IntegerField(allow_none=False, required=True)
    credentials = DictField(allow_none=False, required=False, default={})
    game_mode = StringField(allow_none=False, required=True)
