import threading
import functools

from pika import (
    PlainCredentials,
    ConnectionParameters,
    BlockingConnection,
    BasicProperties,
)


from loguru import logger

from core.utils import parce_message
from core.settings import settings
from core.merge import merge


ON_MERGE_QUEUE = "on_merge"
ON_PUBLISH_QUEUE = "on_publish"


class DaemonApp:
    def __init__(self) -> None:
        self.connect()

    def ack_message(self, channel, delivery_tag):
        if channel.is_open:
            channel.basic_ack(delivery_tag)
        else:
            logger.error("Channel was closed unexpectadly, reconnect")
            self.connect()

    def connect(self) -> None:
        """Соединение с очередью"""

        credentials = PlainCredentials(
            settings.rabbitmq_name, settings.rabbitmq_password
        )
        parameters = ConnectionParameters(
            settings.rabbitmq_host, settings.rabbitmq_port, "/", credentials
        )

        self.connection = BlockingConnection(parameters)
        self.channel = self.connection.channel()

        logger.info("Connection sucssessful")

        return self.connection

    def on_message(self, channel, method, properties, body: str, args) -> None:
        """
        Ф-ия реагирования на полученное сообщение - получает сообщение, запускает ф-ию его обработки merge,
        подтверждает получение сообщения. Если ф-ия обработки вернула 'resend', то сообщение с таким же текстом
        перезаписывается в очередь.
        """
        connection = args
        logger.info(f"Received {body}")
        input_message = parce_message(body)
        if not input_message:
            logger.error("parce exception, deleted from queue")
            channel.basic_ack(
                delivery_tag=method.delivery_tag
            )  # say we achieved message and proceeded it
        else:
            delivery_tag = method.delivery_tag
            t = threading.Thread(
                target=self.do_work,
                args=(input_message, connection, channel, delivery_tag),
            )
            t.start()

    def do_work(self, input_message, connection, channel, delivery_tag):
        import asyncio

        result_of_merge = asyncio.run(merge(input_message))

        cb = functools.partial(self.ack_message, channel, delivery_tag)
        connection.add_callback_threadsafe(cb)

        input_message["url"] = result_of_merge
        self.send_message(input_message, queue=ON_PUBLISH_QUEUE)

    def start_listening(self) -> None:
        """Запуск прослушивания main очереди"""

        self.channel.queue_declare(queue=ON_MERGE_QUEUE, durable=True)

        self.channel.basic_qos(prefetch_count=1)
        on_message_callback = functools.partial(self.on_message, args=(self.connection))
        self.channel.basic_consume(
            queue=ON_MERGE_QUEUE, on_message_callback=on_message_callback
        )
        logger.debug("Waiting for messages. To exit press CTRL+C")

        self.channel.start_consuming()

    def send_message(
        self,
        message: str,
        queue=ON_MERGE_QUEUE,
    ) -> None:
        """Отправка сообщения в конец очереди"""
        connection = self.connect()
        channel = connection.channel()
        channel.queue_declare(queue=queue, durable=True)
        message = str(message)
        channel.basic_publish(
            exchange="",
            routing_key=queue,
            body=message,
            properties=BasicProperties(delivery_mode=2),
        )
        logger.info(f"Resent message - '{message}'")


if __name__ == "__main__":
    deamon = DaemonApp()
    deamon.start_listening()
