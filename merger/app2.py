from pika import PlainCredentials, ConnectionParameters, BlockingConnection
from loguru import logger

from core.settings import settings


class DaemonApp:
    def __init__(self) -> None:
        self.connect()

    def connect(self) -> None:
        """ Соединение с очередью """

        credentials = PlainCredentials(
            settings.rabbitmq_name, settings.rabbitmq_password
        )
        parameters = ConnectionParameters(
            settings.rabbitmq_host, settings.rabbitmq_port, "/", credentials
        )

        connection = BlockingConnection(parameters)
        self.channel = connection.channel()

    def callback(self, ch, method, properties, body: str) -> None:
        body = str(body)

        logger.info(f"Received {body}")
        # TODO: тут должен быть запуск мерджера по заданным параметрам
        logger.info("Done")
        channel.basic_ack(delivery_tag=method.delivery_tag)

    def recieve(self) -> None:
        self.channel.queue_declare(queue="main_queue", durable=True)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue="main_queue", on_message_callback=self.callback
        )
        logger.info("Waiting for messages. To exit press CTRL+C")
        self.channel.start_consuming()


if __name__ == "__main__":
    deamon = DaemonApp()
    deamon.recieve()
