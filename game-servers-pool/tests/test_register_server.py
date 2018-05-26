from copy import deepcopy

import pytest
from sage_utils.amqp.clients import RpcAmqpClient
from sage_utils.constants import VALIDATION_ERROR
from sage_utils.wrappers import Response

from app.game_servers.documents import GameServer
from app.workers.register_server import RegisterServerWorker


REQUEST_QUEUE = RegisterServerWorker.QUEUE_NAME
REQUEST_EXCHANGE = RegisterServerWorker.REQUEST_EXCHANGE_NAME
RESPONSE_EXCHANGE = RegisterServerWorker.RESPONSE_EXCHANGE_NAME


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
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]) == 4

    for field in ['host', 'port', 'available_slots', 'game_mode']:
        assert field in error[Response.ERROR_DETAILS_FIELD_NAME]
        assert len(error[Response.ERROR_DETAILS_FIELD_NAME][field]) == 1
        assert error[Response.ERROR_DETAILS_FIELD_NAME][field][0] == 'Missing data for ' \
                                                                     'required field.'

    servers_count = await GameServer.collection.find().count()
    assert servers_count == 0

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_registers_a_new_server_successfully(sanic_server):
    await GameServer.collection.delete_many({})

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload={
        'host': '127.0.0.1',
        'port': 9000,
        'available_slots': 100,
        'credentials': {
            'token': 'super_secret_token'
        },
        'game_mode': '1v1'
    })

    assert Response.EVENT_FIELD_NAME in response.keys()
    assert Response.CONTENT_FIELD_NAME in response.keys()
    content = response[Response.CONTENT_FIELD_NAME]

    assert len(content.keys()) == 1
    assert 'id' in content.keys()

    servers_count = await GameServer.collection.find().count()
    assert servers_count == 1

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_updates_a_new_server_successfully(sanic_server):
    await GameServer.collection.delete_many({})

    create_data = {
        'host': '127.0.0.1',
        'port': 9000,
        'available_slots': 100,
        'credentials': {
            'token': 'super_secret_token'
        },
        'game_mode': '1v1'
    }

    game_server = GameServer(**create_data)
    await game_server.commit()

    update_data = deepcopy(create_data)
    update_data.update({
        'id': str(game_server.id),
        'available_slots': 80
    })

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload=update_data)

    assert Response.EVENT_FIELD_NAME in response.keys()
    assert Response.CONTENT_FIELD_NAME in response.keys()
    content = response[Response.CONTENT_FIELD_NAME]

    assert len(content.keys()) == 1
    assert 'id' in content.keys()

    servers_count = await GameServer.collection.find().count()
    assert servers_count == 1

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_a_validation_error_for_invalid_data(sanic_server):
    await GameServer.collection.delete_many({})

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload="/", raw_data=True)

    assert Response.ERROR_FIELD_NAME in response.keys()
    error = response[Response.ERROR_FIELD_NAME]

    assert Response.ERROR_TYPE_FIELD_NAME in error.keys()
    assert error[Response.ERROR_TYPE_FIELD_NAME] == VALIDATION_ERROR

    assert Response.ERROR_DETAILS_FIELD_NAME in error.keys()
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]) == 4

    for field in ['host', 'port', 'available_slots', 'game_mode']:
        assert field in error[Response.ERROR_DETAILS_FIELD_NAME]
        assert len(error[Response.ERROR_DETAILS_FIELD_NAME][field]) == 1
        assert error[Response.ERROR_DETAILS_FIELD_NAME][field][0] == 'Missing data for ' \
                                                                     'required field.'

    servers_count = await GameServer.collection.find().count()
    assert servers_count == 0

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_a_validation_error_for_invalid_id(sanic_server):
    await GameServer.collection.delete_many({})

    create_data = {
        'id': "INVALID_ID",
        'host': '127.0.0.1',
        'port': 9000,
        'available_slots': 100,
        'credentials': {
            'token': 'super_secret_token'
        },
        'game_mode': '1v1'
    }

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload=create_data)

    assert Response.ERROR_FIELD_NAME in response.keys()
    error = response[Response.ERROR_FIELD_NAME]

    assert Response.ERROR_TYPE_FIELD_NAME in error.keys()
    assert error[Response.ERROR_TYPE_FIELD_NAME] == VALIDATION_ERROR

    assert Response.ERROR_DETAILS_FIELD_NAME in error.keys()
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]) == 1

    assert 'id' in error[Response.ERROR_DETAILS_FIELD_NAME]
    assert len(error[Response.ERROR_DETAILS_FIELD_NAME]['id']) == 1
    assert error[Response.ERROR_DETAILS_FIELD_NAME]['id'][0] == "'INVALID_ID' is not a valid " \
                                                                "ObjectId, it must be a 12-byte " \
                                                                "input or a 24-character hex " \
                                                                "string."

    servers_count = await GameServer.collection.find().count()
    assert servers_count == 0

    await GameServer.collection.delete_many({})
