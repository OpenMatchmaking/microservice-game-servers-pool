from bson import ObjectId
from marshmallow import Schema, fields, validate, validates, ValidationError

from app import app


GameServer = app.config["LAZY_UMONGO"].GameServer


class RequestGetServerSchema(Schema):
    required_slots = fields.Integer(
        attribute="required-slots",
        load_from="required-slots",
        required=True,
        allow_none=False,
        validate=[
            validate.Range(min=0, error="Field must have a positive value."),
        ]
    )
    game_mode = fields.String(
        attribute="game-mode",
        load_from="game-mode",
        required=True,
        allow_none=False,
        validate=[
            validate.Length(min=1, error='Field cannot be blank.'),
        ]
    )

    class Meta:
        ordered = True


class RetrieveGameServerSchema(GameServer.schema.as_marshmallow_schema()):

    class Meta:
        model = GameServer
        ordered = True
        fields = (
            'host',
            'port',
            'credentials',
        )


class RegisterGameServerSchema(Schema):
    id = fields.String(required=False)
    host = fields.String(
        required=True,
        allow_none=False,
        validate=[
            validate.Length(min=1, error="Field cannot be blank."),
        ]
    )
    port = fields.Integer(
        required=True,
        allow_none=False,
        validate=[
            validate.Range(min=0, error="Field must have a positive value."),
        ]
    )
    available_slots = fields.Integer(
        load_from="available-slots",
        allow_none=False,
        required=True,
        validate=[
            validate.Range(min=1, error="The value must be positive integer.")
        ]
    )
    game_mode = fields.String(
        load_from="game-mode",
        required=True,
        allow_none=False,
        validate=[
            validate.Length(min=1, error='Field cannot be blank.'),
        ]
    )
    credentials = fields.Dict(
        allow_none=False,
        required=False,
        missing={}
    )

    @validates('id')
    def validate_id(self, value):
        if not ObjectId.is_valid(value):
            raise ValidationError(
                "'{}' is not a valid ObjectId, it must be a 12-byte "
                "input or a 24-character hex string.".format(value)
            )

    class Meta:
        model = GameServer
        ordered = True
        fields = (
            'id',
            'host',
            'port',
            'available_slots',
            'credentials',
            'game_mode',
        )


class UpdateGameServerSchema(Schema):
    id = fields.String(
        required=True
    )
    freed_slots = fields.Integer(
        load_from="freed-slots",
        allow_none=False,
        required=True,
        validate=[
            validate.Range(min=1, error="The value must be positive integer.")
        ]
    )

    @validates('id')
    def validate_id(self, value):
        if not ObjectId.is_valid(value):
            raise ValidationError(
                "'{}' is not a valid ObjectId, it must be a 12-byte "
                "input or a 24-character hex string.".format(value)
            )

    class Meta:
        model = GameServer
        ordered = True
        fields = (
            'id',
            'freed_slots',
        )


class SimpleGameServerSchema(Schema):
    id = fields.String(
        dump_only=True
    )
    available_slots = fields.Integer(
        dump_only=True,
        dump_to="available-slots",
    )

    class Meta:
        model = GameServer
        ordered = True
        fields = (
            'id',
            'available_slots',
        )
