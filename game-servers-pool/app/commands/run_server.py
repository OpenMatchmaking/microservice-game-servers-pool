import asyncio
from sanic_script import Command, Option

from app import app
from app.workers.microservice_register import MicroserviceRegisterWorker


class RunServerCommand(Command):
    """
    Run the HTTP/HTTPS server.
    """
    app = app

    option_list = (
        Option('--host', '-h', dest='host'),
        Option('--port', '-p', dest='port'),
    )

    def register_microservice(self):
        loop = asyncio.get_event_loop()
        worker = MicroserviceRegisterWorker(self.app)
        loop.run_until_complete(worker.run(loop=loop))
        loop.stop()
        loop.close()

    def run(self, *args, **kwargs):
        self.register_microservice()
        self.app.run(
            host=kwargs.get('host', None) or self.app.config["APP_HOST"],
            port=kwargs.get('port', None) or self.app.config["APP_PORT"],
            debug=self.app.config["APP_DEBUG"],
            ssl=self.app.config["APP_SSL"],
            workers=self.app.config["APP_WORKERS"],
        )
