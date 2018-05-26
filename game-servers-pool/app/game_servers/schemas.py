from bson import ObjectId
from marshmallow import Schema, fields, validate, validates, ValidationError

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


class RegisterGameServerSchema(GameServer.schema.as_marshmallow_schema()):
    id = fields.String(required=False)

    @validates('id')
    def validate_id(self, value):
        if not ObjectId.is_valid(value):
            raise ValidationError(
                "'{}' is not a valid ObjectId, it must be a 12-byte "
                "input or a 24-character hex string.".format(value)
            )

    class Meta:
        model = GameServer
        fields = (
            'id',
            'host',
            'port',
            'available_slots',
            'credentials',
            'game_mode',
        )


class RetrieveGameServerSchema(GameServer.schema.as_marshmallow_schema()):

    class Meta:
        model = GameServer
        fields = (
            'host',
            'port',
            'credentials',
        )
