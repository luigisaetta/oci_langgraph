"""
OCI Queue base

to avoid repeated code, this class is used as a base for all OCI Queue classes
"""

from oci.queue import QueueClient
from .utils import get_security_config_and_signer


class QueueBase:
    """
    OCI Queue base
    """

    def __init__(
        self,
        queue_ocid: str,
        service_endpoint: str,
        auth_type: str = "API_KEY",
        **kwargs,
    ):
        """
        Initialize the OCI Queue base class

        Args:
            queue_ocid (str): OCID of the OCI Queue.
            service_endpoint (str): The service endpoint URL for the OCI Queue.
            auth_type (str): The authentication type to use. Options are:
                - "API_KEY": Uses API key authentication (default).
                - "INSTANCE_PRINCIPAL": Uses instance principal authentication.
            kwargs: Optional parameters for additional configuration.
        """
        config, signer = get_security_config_and_signer(auth_type)

        self.auth_type = auth_type
        self.queue_ocid = queue_ocid
        self.service_endpoint = service_endpoint

        if config:
            self.queue_client = QueueClient(
                config=config, service_endpoint=self.service_endpoint
            )
        else:
            self.queue_client = QueueClient(
                # Empty config for instance principal
                config={},
                signer=signer,
                service_endpoint=self.service_endpoint,
            )

    def get_auth_type(self):
        """
        Get the authentication type used for the queue client.

        Returns:
            str: The authentication type.
        """
        return self.auth_type
