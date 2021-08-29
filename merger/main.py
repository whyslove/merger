from pika import PlainCredentials, ConnectionParameters, BlockingConnection
from loguru import logger

from core.settings import settings
from merge import merge


QUEUE = "main_queue"


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

        logger.info("Connection sucssessful")

    def callback(self, ch, method, properties, body: str) -> None:
        """
        Ф-ия реагирования на полученное сообщение - получает сообщение, запускает ф-ию его обработки merge,
        подтверждает получение сообщения. Если ф-ия обработки вернула 'resend', то сообщение с таким же текстом
        перезаписывается в очередь.
        """

        body = str(body)
        logger.info(f"Received {body}")

        result_of_merge = merge(body)
        self.channel.basic_ack(delivery_tag=method.delivery_tag)

        if result_of_merge == "resend":
            logger.warning("Video is not ready for merging yet...")
            self.resend_message(body)

    def recieve(self) -> None:
        """ Запуск прослушивания очереди """

        self.channel.queue_declare(queue=QUEUE, durable=True)

        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue=QUEUE, on_message_callback=self.callback)
        logger.info("Waiting for messages. To exit press CTRL+C")
        self.channel.start_consuming()

    def resend_message(self, message: str) -> None:
        """ Повторная отправка сообщения в конец очереди """

        channel.queue_declare(queue=QUEUE, durable=True)

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2),
        )
        logger.info(f"Resent message - '{message}'")


if __name__ == "__main__":
    deamon = DaemonApp()
    deamon.recieve()
