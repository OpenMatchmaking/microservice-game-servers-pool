import json

from aioamqp import AmqpClosedConnection
from bson import ObjectId
from marshmallow import ValidationError
from sanic_amqp_ext import AmqpWorker
from sage_utils.constants import VALIDATION_ERROR, NOT_FOUND_ERROR
from sage_utils.wrappers import Response


class UpdateServerWorker(AmqpWorker):
    QUEUE_NAME = 'game-servers-pool.server.update'
    REQUEST_EXCHANGE_NAME = 'open-matchmaking.game-server-pool.server.update.direct'
    RESPONSE_EXCHANGE_NAME = 'open-matchmaking.responses.direct'
    CONTENT_TYPE = 'application/json'

    def __init__(self, app, *args, **kwargs):
        super(UpdateServerWorker, self).__init__(app, *args, **kwargs)
        from app.game_servers.documents import GameServer
        from app.game_servers.schemas import UpdateGameServerSchema, SimpleGameServerSchema
        self.game_server_document = GameServer
        self.schema = UpdateGameServerSchema
        self.response_schema = SimpleGameServerSchema

    async def validate_data(self, raw_data):
        try:
            data = json.loads(raw_data.strip())
        except json.decoder.JSONDecodeError:
            data = {}
        deserializer = self.schema()
        result = deserializer.load(data)
        if result.errors:
            raise ValidationError(result.errors)

        return result.data

    async def update_game_server(self, raw_data):
        try:
            data = await self.validate_data(raw_data)
        except ValidationError as exc:
            return Response.from_error(VALIDATION_ERROR, exc.normalized_messages())

        document_id = ObjectId(data['id'])
        document = await self.game_server_document.find_one({'_id': document_id})

        if not document:
            return Response.from_error(
                NOT_FOUND_ERROR,
                "The requested game server was not found."
            )

        document.available_slots += data['freed_slots']
        await document.commit()

        serializer = self.response_schema()
        return Response.with_content(serializer.dump(document).data)

    async def process_request(self, channel, body, envelope, properties):
        response = await self.update_game_server(body)
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
