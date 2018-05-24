from sage_utils.amqp.workers import BaseRegisterWorker
from sage_utils.amqp.mixins import SanicAmqpExtensionMixin


class MicroserviceRegisterWorker(SanicAmqpExtensionMixin, BaseRegisterWorker):

    def get_microservice_data(self, _app):
        return {
            'name': self.app.config['SERVICE_NAME'],
            'version': self.app.config['SERVICE_VERSION'],
            'permissions': [
                {
                    'codename': 'game-servers-pool.server.register',
                    'description': 'Register a new game server',
                },
                {
                    'codename': 'game-servers-pool.server.retrieve',
                    'description': 'Get a server with credentials to connect',
                },
            ]
        }
