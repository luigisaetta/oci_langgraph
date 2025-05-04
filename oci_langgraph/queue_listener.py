"""
Email dequeuer:

    - Dequeues emails from INBOUND queue
    - use channel_id as selector
"""

import time
import json
from abc import ABC, abstractmethod
import oci
from oci.queue import QueueClient

from .utils import get_console_logger

logger = get_console_logger()


class QueueListener(ABC):
    """
    Reads from an INBOUND queue and processes messages
    """

    def __init__(
        self,
        config_path: str,
        service_endpoint: str,
        queue_id: str,
        channel_id: str,
        profile: str = "DEFAULT",
        max_wait_time: int = 60,
        get_messages_timeout: int = 10,
        visibility_timeout: int = 30,
        message_limit: int = 5,
    ):
        """
        Initializes the OCIQueueListener with the specified parameters.

        Args:
            config_path (str): Path to the OCI configuration file.
            profile (str): Profile name within the OCI configuration file.
            service_endpoint (str): The service endpoint URL for the OCI Queue.
            queue_id (str): The OCID of the OCI Queue.
            max_wait_time (int, optional): Maximum duration in seconds to listen for messages.
                Defaults to 60.
            get_messages_timeout (int, optional): Timeout in seconds for each get_messages call.
                Defaults to 10.
            visibility_timeout (int, optional): Duration in seconds that a message remains
                invisible to other consumers after being retrieved. Defaults to 30.
            message_limit (int, optional): Maximum number of messages to retrieve
                per get_messages call.
            Defaults to 5.
        """
        self.config = oci.config.from_file(config_path, profile)
        self.service_endpoint = service_endpoint
        self.queue_id = queue_id
        self.channel_id = channel_id
        self.max_wait_time = max_wait_time
        self.get_messages_timeout = get_messages_timeout
        self.visibility_timeout = visibility_timeout
        self.message_limit = message_limit
        self.queue_client = QueueClient(
            config=self.config, service_endpoint=self.service_endpoint
        )

    def listen(self, expected_sender_list: list = None):
        """
        Starts listening to the OCI Queue for messages.

        The method listens for messages until the specified max_wait_time is reached
        or until all expected senders have sent their messages.
        For each retrieved message, it processes and deletes the message from the queue.
        """
        logger.info(
            "Started queue listener, max_wait_time %d (sec.)...", self.max_wait_time
        )
        logger.info("")

        # Start the listening loop
        expected_sender_list = expected_sender_list.copy()

        start_time = time.time()
        msgs_received = 0

        received_msgs_list = []

        while ((time.time() - start_time) < self.max_wait_time) and (
            len(expected_sender_list) > 0
        ):
            try:
                response = self.queue_client.get_messages(
                    queue_id=self.queue_id,
                    channel_filter=self.channel_id,
                    visibility_in_seconds=self.visibility_timeout,
                    timeout_in_seconds=self.get_messages_timeout,
                    limit=self.message_limit,
                )

                messages = response.data.messages

                if not messages:
                    logger.info("No messages received. Waiting...")
                    continue

                msgs_received += len(messages)

                for message in messages:
                    logger.info("Received message: %s", message.content)

                    # here we do processing of the message
                    json_msg = json.loads(message.content)

                    msg = self.process_message(json_msg)

                    received_msgs_list.append(msg)

                    # Delete the message after processing
                    # remove from the list of expected providers
                    if msg["sender_id"] in expected_sender_list:
                        expected_sender_list.remove(msg["sender_id"])
                        logger.info(
                            "Provider %s removed from expected list", msg["sender_id"]
                        )

                    self.queue_client.delete_message(
                        queue_id=self.queue_id, message_receipt=message.receipt
                    )

            except Exception as e:
                logger.error("An error occurred in queue_listener.listen: %s", e)
                break

        logger.info("Listener has completed the wait loop.")
        logger.info("Total messages received: %d", msgs_received)

        return received_msgs_list

    @abstractmethod
    def process_message(self, payload: dict):
        """
        Process the message payload.
        Args:
            payload (dict): The message payload to process.
        """
        # Here you can implement the logic to process the message
        # For example, you can print the payload or perform some action based on its content
