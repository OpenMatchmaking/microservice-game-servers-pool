from marshmallow import Schema, fields, validate

from app import app


GameServer = app.config["LAZY_UMONGO"].GameServer


class RequestGetServerSchema(Schema):
    required_slots = fields.Integer(
        required=True,
        allow_none=False,
        validate=[
            validate.Range(min=0, error="Field must have a positive value."),
        ]
    )
    game_mode = fields.String(
        required=True,
        allow_none=False,
        validate=[
            validate.Length(min=1, error='Field cannot be blank.'),
        ]
    )


class GameServerSchema(GameServer.schema.as_marshmallow_schema()):

    class Meta:
        model = GameServer
        fields = (
            'host',
            'port',
            'credentials'
        )
