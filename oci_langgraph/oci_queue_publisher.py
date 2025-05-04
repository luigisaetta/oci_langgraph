"""
Email Enqueuer Module

Author: L. Saetta

This module defines the `QueuePublisher` class, responsible for enqueuing messages
to an OCI (Oracle Cloud Infrastructure) outbound message queue. It's typically used
to queue outbound emails for various providers by placing a message into the queue.

License: MIT
"""

import json
from oci.queue import QueueClient
from oci.queue.models import PutMessagesDetails, PutMessagesDetailsEntry
from .utils import get_console_logger, get_security_config_and_signer

logger = get_console_logger()


class QueuePublisher:
    """
    A class to publish messages to an OCI outbound queue.

    This is typically used in email workflows to queue a message for each
    email partner, allowing asynchronous and scalable dispatching.
    """

    def __init__(
        self, queue_ocid: str, service_endpoint: str, auth_type: str = "API_KEY"
    ):
        """
        Initialize the QueuePublisher with the given OCI queue configuration.

        Args:
            queue_ocid (str): OCID of the OCI queue.
            service_endpoint (str): The endpoint URL of the OCI queue service.
            auth_type (str): The authentication type to use. Options are:
                - "API_KEY": Uses API key authentication (default).
                - "INSTANCE_PRINCIPAL": Uses instance principal authentication.
        """
        config, signer = get_security_config_and_signer(auth_type)

        self.queue_ocid = queue_ocid
        self.service_endpoint = service_endpoint

        if config:
            self.queue_client = QueueClient(
                config=config, service_endpoint=self.service_endpoint
            )
        else:
            self.queue_client = QueueClient(
                config={},  # Empty config for instance principal
                signer=signer,
                service_endpoint=self.service_endpoint,
            )

        logger.info("QueuePublisher initialized for queue OCID: %s", self.queue_ocid)

    def enqueue_message(self, payload: dict):
        """
        Enqueue a message to the configured OCI queue.

        Args:
            payload (dict): The message content to be enqueued. Must be JSON-serializable.

        Returns:
            oci.response.Response: The response object returned from the put_messages API call.
        """
        logger.debug("Preparing message for enqueue: %s", payload)

        try:
            # Prepare the message
            message_content = json.dumps(payload)
            message = PutMessagesDetailsEntry(content=message_content)
            put_messages_details = PutMessagesDetails(messages=[message])

            # Send the message to the queue
            logger.info("Sending message to queue: %s...", self.queue_ocid)

            response = self.queue_client.put_messages(
                queue_id=self.queue_ocid, put_messages_details=put_messages_details
            )

            logger.debug(
                "Message enqueued successfully with status code: %s", response.status
            )
            return response

        except Exception as e:
            logger.error("Failed to enqueue message: %s", str(e))
            raise
