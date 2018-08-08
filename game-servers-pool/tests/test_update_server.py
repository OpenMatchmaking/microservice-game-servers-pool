import pytest
from sage_utils.amqp.clients import RpcAmqpClient
from sage_utils.constants import VALIDATION_ERROR, NOT_FOUND_ERROR
from sage_utils.wrappers import Response

from app.game_servers.documents import GameServer
from app.workers.update_server import UpdateServerWorker


REQUEST_QUEUE = UpdateServerWorker.QUEUE_NAME
REQUEST_EXCHANGE = UpdateServerWorker.REQUEST_EXCHANGE_NAME
RESPONSE_EXCHANGE = UpdateServerWorker.RESPONSE_EXCHANGE_NAME


@pytest.mark.asyncio
async def test_worker_returns_an_updated_information_about_slots(sanic_server):
    await GameServer.collection.delete_many({})

    game_server = GameServer(**{
        'host': '127.0.0.1',
        'port': 9000,
        'available_slots': 100,
        'credentials': {
            'token': 'super_secret_token'
        },
        'game_mode': '1v1'
    })
    await game_server.commit()

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    data = {
        'id': str(game_server.id),
        'freed-slots': 10
    }
    response = await client.send(payload=data)

    assert Response.EVENT_FIELD_NAME in response.keys()
    assert Response.CONTENT_FIELD_NAME in response.keys()
    content = response[Response.CONTENT_FIELD_NAME]

    assert set(content.keys()) == {'id', 'available-slots'}
    assert content['id'] == str(game_server.id)
    assert content['available-slots'] == game_server.available_slots + data['freed-slots']

    servers_count = await GameServer.collection.count_documents({})
    assert servers_count == 1

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_not_found_error_for_non_existing_game_server(sanic_server):
    await GameServer.collection.delete_many({})

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    data = {
        'id': '5b6a085123cf24aef53b4c78',
        'freed-slots': 10
    }
    response = await client.send(payload=data)

    assert Response.ERROR_FIELD_NAME in response.keys()
    error = response[Response.ERROR_FIELD_NAME]

    assert Response.ERROR_TYPE_FIELD_NAME in error.keys()
    assert error[Response.ERROR_TYPE_FIELD_NAME] == NOT_FOUND_ERROR

    assert Response.ERROR_DETAILS_FIELD_NAME in error.keys()
    assert error[Response.ERROR_DETAILS_FIELD_NAME] == 'The requested game server ' \
                                                       'was not found.'

    servers_count = await GameServer.collection.count_documents({})
    assert servers_count == 0

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_a_validation_error_for_missing_fields(sanic_server):
    await GameServer.collection.delete_many({})

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload={})

    assert Response.ERROR_FIELD_NAME in response.keys()
    error = response[Response.ERROR_FIELD_NAME]

    assert Response.ERROR_TYPE_FIELD_NAME in error.keys()
    assert error[Response.ERROR_TYPE_FIELD_NAME] == VALIDATION_ERROR

    assert Response.ERROR_DETAILS_FIELD_NAME in error.keys()
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]) == 2

    for field in ['id', 'freed-slots']:
        assert field in error[Response.ERROR_DETAILS_FIELD_NAME]
        assert len(error[Response.ERROR_DETAILS_FIELD_NAME][field]) == 1
        assert error[Response.ERROR_DETAILS_FIELD_NAME][field][0] == 'Missing data for ' \
                                                                     'required field.'

    servers_count = await GameServer.collection.count_documents({})
    assert servers_count == 0

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_a_validation_error_for_invalid_id_and_slots_type(sanic_server):
    await GameServer.collection.delete_many({})

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    data = {
        'id': 'INVALID_OBJECT_ID',
        'freed-slots': 'INVALID_VALUE'
    }
    response = await client.send(payload=data)

    assert Response.ERROR_FIELD_NAME in response.keys()
    error = response[Response.ERROR_FIELD_NAME]

    assert Response.ERROR_TYPE_FIELD_NAME in error.keys()
    assert error[Response.ERROR_TYPE_FIELD_NAME] == VALIDATION_ERROR

    assert Response.ERROR_DETAILS_FIELD_NAME in error.keys()
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]) == 2

    assert 'id' in error[Response.ERROR_DETAILS_FIELD_NAME]
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]['id']) == 1
    assert error[Response.ERROR_DETAILS_FIELD_NAME]['id'][0] == "'INVALID_OBJECT_ID' is not a " \
                                                                "valid ObjectId, it must be a " \
                                                                "12-byte input or a " \
                                                                "24-character hex string."

    assert 'freed-slots' in error[Response.ERROR_DETAILS_FIELD_NAME]
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]['freed-slots']) == 1
    assert error[Response.ERROR_DETAILS_FIELD_NAME]['freed-slots'][0] == 'Not a valid integer.'

    servers_count = await GameServer.collection.count_documents({})
    assert servers_count == 0

    await GameServer.collection.delete_many({})
