import json

from aioamqp import AmqpClosedConnection
from marshmallow import ValidationError
from sanic_amqp_ext import AmqpWorker
from sage_utils.constants import VALIDATION_ERROR
from sage_utils.wrappers import Response


class GetServerWorker(AmqpWorker):
    QUEUE_NAME = 'game-servers-pool.server.retrieve'
    REQUEST_EXCHANGE_NAME = 'open-matchmaking.direct'
    RESPONSE_EXCHANGE_NAME = 'open-matchmaking.responses.direct'
    CONTENT_TYPE = 'application/json'

    def __init__(self, app, *args, **kwargs):
        super(GetServerWorker, self).__init__(app, *args, **kwargs)
        from app.game_servers.documents import GameServer
        from app.game_servers.schemas import RequestGetServerSchema, GameServerSchema
        self.game_server_document = GameServer
        self.schema = GameServerSchema
        self.request_schema = RequestGetServerSchema

    async def validate_data(self, raw_data):
        try:
            data = json.loads(raw_data.strip())
        except json.decoder.JSONDecodeError:
            data = {}

        deserializer = self.request_schema()
        result = deserializer.load(data)
        if result.errors:
            raise ValidationError(result.errors)

        return result.data

    async def get_game_server(self, raw_data):
        try:
            data = await self.validate_data(raw_data)
        except ValidationError as exc:
            return Response.from_error(VALIDATION_ERROR, exc.normalized_messages())

        pipeline = [
            {'$match': {
                '$and': [
                    {'available_slots': {'$gte': data['required_slots']}},
                    {"game_mode": data['game_mode']}
                ]
            }}
        ]
        instance = await self.game_server_document.collection.aggregate(pipeline).limit(1)

        serializer = self.schema()
        serialized_instance = serializer.dump(instance).data
        return Response.with_content(serialized_instance)

    async def process_request(self, channel, body, envelope, properties):
        response = await self.get_game_server(body)
        response.data[Response.EVENT_FIELD_NAME] = properties.correlation_id

        if properties.reply_to:
            await channel.publish(
                json.dumps(response.data),
                exchange_name=self.RESPONSE_EXCHANGE_NAME,
                routing_key=properties.reply_to,
                properties={
                    'content_type': self.CONTENT_TYPE,
                    'delivery_mode': 2,
                    'correlation_id': properties.correlation_id
                },
                mandatory=True
            )

        await channel.basic_client_ack(delivery_tag=envelope.delivery_tag)

    async def consume_callback(self, channel, body, envelope, properties):
        self.app.loop.create_task(self.process_request(channel, body, envelope, properties))

    async def run(self, *args, **kwargs):
        try:
            _transport, protocol = await self.connect()
        except AmqpClosedConnection as exc:
            print(exc)
            return

        channel = await protocol.channel()
        await channel.queue_declare(
            queue_name=self.QUEUE_NAME,
            durable=True,
            passive=False,
            auto_delete=False
        )
        await channel.queue_bind(
            queue_name=self.QUEUE_NAME,
            exchange_name=self.REQUEST_EXCHANGE_NAME,
            routing_key=self.QUEUE_NAME
        )
        await channel.basic_qos(prefetch_count=1, prefetch_size=0, connection_global=False)
        await channel.basic_consume(self.consume_callback, queue_name=self.QUEUE_NAME)
