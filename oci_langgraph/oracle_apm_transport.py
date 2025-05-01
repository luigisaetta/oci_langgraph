"""
File name: trasnport.py
Author: Luigi Saetta
Date last modified: 2025-05-01
Python Version: 3.11

Description:
    This code provide the http transport support for integration with OCI APM.
    It must be used on where we start the trace, at the beginning

Usage:
    Import this module into other scripts to use its functions.
    Example:
       ...


License:
    This code is released under the MIT License.

Warnings:
    This module is in development, may change in future versions.
"""

import requests
from .utils import get_console_logger

logger = get_console_logger()


class APMTransport:
    """
    A class to send encoded Zipkin span data to OCI APM.
    """

    def __init__(
        self,
        base_url: str,
        public_key: str,
        content_type: str = "application/json",
        enable_tracing: bool = True,
    ):
        """
        Initializes the transport with necessary config.

        :param base_url: Base URL of the APM service.
        :param public_key: Public key for authenticating the request.
        :param content_type: MIME type for the request.
        :param enable_tracing: Flag to enable or disable tracing.
        """
        self.base_url = base_url
        self.public_key = public_key
        self.content_type = content_type
        self.enable_tracing = enable_tracing

    def http_transport(self, encoded_span: bytes):
        """
        Sends encoded tracing data to OCI APM.

        :param encoded_span: The encoded span data to send.
        :return: requests.Response or None
        """
        if not self.enable_tracing:
            logger.info("Tracing is disabled. No data sent to APM.")
            return None

        if not self.base_url:
            raise ValueError("APM base URL is not configured")
        if not self.public_key:
            raise ValueError("APM public key is missing")

        apm_url = (
            f"{self.base_url}/observations/public-span?"
            f"dataFormat=zipkin&dataFormatVersion=2&dataKey={self.public_key}"
        )

        try:
            response = requests.post(
                apm_url,
                data=encoded_span,
                headers={"Content-Type": self.content_type},
                timeout=30,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error("Failed to send span to APM: %s", str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error in APMTransport.send: %s", str(e))
            return None

    def is_tracing_enabled(self):
        """
        Check if tracing is enabled.

        :return: True if tracing is enabled, False otherwise.
        """
        return self.enable_tracing
