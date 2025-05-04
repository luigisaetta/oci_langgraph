"""
Email dequeuer:

    - Dequeues emails from INBOUND queue
    - use channel_id as selector
"""

import time
import json
from abc import ABC, abstractmethod
from oci.queue import QueueClient

from .utils import get_console_logger, get_security_config_and_signer

logger = get_console_logger()


class QueueListener(ABC):
    """
    Reads from an INBOUND queue and processes messages
    """

    def __init__(
        self,
        queue_ocid: str,
        service_endpoint: str,
        auth_type: str = "API_KEY",
        channel_id: str = None,
        # introduced to handle additional params
        **kwargs,
    ):
        """
        Initializes the OCIQueueListener with the specified parameters.

        Args:
            queue_ocid (str): OCID of the OCI Queue.
            service_endpoint (str): The service endpoint URL for the OCI Queue.
            auth_type (str): The authentication type to use. Options are:
                - "API_KEY": Uses API key authentication (default).
                - "INSTANCE_PRINCIPAL": Uses instance principal authentication.
            channel_id (str): The channel ID to filter messages. Can be None

            kwargs: Optional parameters:
                - max_wait_time (int): Maximum time to wait for all messages in seconds
                  (default: 3600)
                - get_messages_timeout (int): Timeout in seconds for each get_messages call
                  (default: 10)
                - visibility_timeout (int): Time a message remains invisible after being read
                  (default: 30)
                - message_limit (int): Max number of messages per get_messages call (default: 5)
        """
        config, signer = get_security_config_and_signer(auth_type)

        self.queue_ocid = queue_ocid
        self.service_endpoint = service_endpoint

        self.channel_id = channel_id

        # Optional parameters with defaults
        self.max_wait_time = kwargs.get("max_wait_time", 3600)
        self.get_messages_timeout = kwargs.get("get_messages_timeout", 10)
        self.visibility_timeout = kwargs.get("visibility_timeout", 30)
        self.message_limit = kwargs.get("message_limit", 5)

        if config:
            logger.info("Queue client, using API_KEY...")
            self.queue_client = QueueClient(
                config=config, service_endpoint=self.service_endpoint
            )
        else:
            self.queue_client = QueueClient(
                config={},  # Empty config for instance principal
                signer=signer,
                service_endpoint=self.service_endpoint,
            )

    def listen(self):
        """
        Starts listening to the OCI Queue for messages.

        The method listens for messages until the specified max_wait_time is reached
        or until the method process_message returns NO_CONTINUE.

        For each retrieved message, it processes and deletes the message from the queue.
        """
        logger.info(
            "Started queue listener, max_wait_time %d (sec.)...", self.max_wait_time
        )

        # Start the listening loop
        start_time = time.time()
        msgs_received = 0

        received_msgs_list = []
        status = "CONTINUE"

        while ((time.time() - start_time) < self.max_wait_time) and (
            status == "CONTINUE"
        ):
            try:
                response = self.queue_client.get_messages(
                    queue_id=self.queue_ocid,
                    channel_filter=self.channel_id,
                    visibility_in_seconds=self.visibility_timeout,
                    timeout_in_seconds=self.get_messages_timeout,
                    limit=self.message_limit,
                )

                messages = response.data.messages

                if not messages:
                    logger.debug("No messages received. Waiting...")
                    continue

                msgs_received += len(messages)

                for message in messages:
                    logger.debug("Received message: %s", message.content)

                    # here we do processing of the message
                    json_msg = json.loads(message.content)
                    received_msgs_list.append(json_msg)

                    status = self.process_message(json_msg)

                    # Delete the message after processing
                    # remove from the list of expected providers
                    self.queue_client.delete_message(
                        queue_id=self.queue_ocid, message_receipt=message.receipt
                    )

            except Exception as e:
                logger.error("An error occurred in queue_listener.listen: %s", e)
                break

        logger.info("Listener has completed the wait loop.")
        logger.info("Total messages received: %d", msgs_received)

        return received_msgs_list

    @abstractmethod
    def process_message(self, payload: dict) -> str:
        """
        Process the message payload.

        This method should be implemented by subclasses to define the
        specific processing logic for the messages received from the queue.
        The method should return a status indicating whether to continue
        processing or not.
        The default implementation returns "CONTINUE".
        The status can be "CONTINUE" or "NO_CONTINUE".
        Args:
            payload (dict): The message payload to process.
        """
        # Here you can implement the logic to process the message
        # For example, you can print the payload or perform some action based on its content
        status = "CONTINUE"

        return status
