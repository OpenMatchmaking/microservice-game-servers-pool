import pytest
from sage_utils.amqp.clients import RpcAmqpClient
from sage_utils.constants import VALIDATION_ERROR
from sage_utils.wrappers import Response

from app.game_servers.documents import GameServer
from app.workers.get_server import GetServerWorker


REQUEST_QUEUE = GetServerWorker.QUEUE_NAME
REQUEST_EXCHANGE = GetServerWorker.REQUEST_EXCHANGE_NAME
RESPONSE_EXCHANGE = GetServerWorker.RESPONSE_EXCHANGE_NAME


async def create_game_servers(init_data_list):
    objects = []
    for create_data in init_data_list:
        game_server = GameServer(**create_data)
        await game_server.commit()
        objects.append(game_server)
    return objects


@pytest.mark.asyncio
async def test_worker_returns_one_existing_server_for_one_server_in_list(sanic_server):
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
    objects = await create_game_servers([create_data, ])

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload={
        'required_slots': 20,
        'game_mode': "1v1"
    })

    assert Response.EVENT_FIELD_NAME in response.keys()
    assert Response.CONTENT_FIELD_NAME in response.keys()
    content = response[Response.CONTENT_FIELD_NAME]

    assert len(list(content.keys())) == 3
    assert set(content.keys()) == {'host', 'port', 'credentials'}

    assert content['host'] == objects[0].host
    assert content['port'] == objects[0].port
    assert content['credentials'] == objects[0].credentials

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_a_random_server_from_a_list(sanic_server):
    await GameServer.collection.delete_many({})

    objects = await create_game_servers([
        {
            'host': '127.0.0.1',
            'port': 9000,
            'available_slots': 100,
            'credentials': {
                'token': 'super_secret_token'
            },
            'game_mode': 'team-deathmatch'
        },
        {
            'host': '127.0.0.1',
            'port': 9001,
            'available_slots': 50,
            'credentials': {
                'token': 'super_secret_token2'
            },
            'game_mode': 'team-deathmatch'
        },
        {
            'host': '127.0.0.1',
            'port': 9002,
            'available_slots': 10,
            'credentials': {
                'token': 'super_secret_token3'
            },
            'game_mode': 'team-deathmatch'
        },
    ])

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload={
        'required_slots': 10,
        'game_mode': 'team-deathmatch'
    })

    assert Response.EVENT_FIELD_NAME in response.keys()
    assert Response.CONTENT_FIELD_NAME in response.keys()
    content = response[Response.CONTENT_FIELD_NAME]

    assert len(list(content.keys())) == 3
    assert set(content.keys()) == {'host', 'port', 'credentials'}

    filter_func = lambda obj: obj.host == content['host'] and obj.port == content['port']  # NOQA
    extracted_server = list(filter(filter_func, objects))[0]

    assert content['host'] == extracted_server.host
    assert content['port'] == extracted_server.port
    assert content['credentials'] == extracted_server.credentials

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_none_for_an_empty_list_of_servers(sanic_server):
    await GameServer.collection.delete_many({})

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload={
        'required_slots': 10,
        'game_mode': 'team-deathmatch'
    })

    assert Response.EVENT_FIELD_NAME in response.keys()
    assert Response.CONTENT_FIELD_NAME in response.keys()
    content = response[Response.CONTENT_FIELD_NAME]

    assert content is None

    await GameServer.collection.delete_many({})


@pytest.mark.asyncio
async def test_worker_returns_none_for_an_non_existing_server_type(sanic_server):
    await GameServer.collection.delete_many({})

    client = RpcAmqpClient(
        sanic_server.app,
        routing_key=REQUEST_QUEUE,
        request_exchange=REQUEST_EXCHANGE,
        response_queue='',
        response_exchange=RESPONSE_EXCHANGE
    )
    response = await client.send(payload={
        'required_slots': 10,
        'game_mode': 'battle-royal'
    })

    assert Response.EVENT_FIELD_NAME in response.keys()
    assert Response.CONTENT_FIELD_NAME in response.keys()
    content = response[Response.CONTENT_FIELD_NAME]

    assert content is None

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

    for field in ['required_slots', 'game_mode']:
        assert field in error[Response.ERROR_DETAILS_FIELD_NAME]
        assert len(error[Response.ERROR_DETAILS_FIELD_NAME][field]) == 1
        assert error[Response.ERROR_DETAILS_FIELD_NAME][field][0] == 'Missing data for ' \
                                                                     'required field.'

    servers_count = await GameServer.collection.find().count()
    assert servers_count == 0

    await GameServer.collection.delete_many({})
