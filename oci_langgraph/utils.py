"""
Utils for OCI LangGraph
This module provides utility functions for the OCI LangGraph framework.
Author: L. Saetta
Date: 2025-05-01
Python Version: 3.11
License: MIT
"""

import os
import re
import json
import logging
import oci

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")


def get_console_logger():
    """
    To get a logger to print on console
    """
    logger = logging.getLogger("ConsoleLogger")

    # to avoid duplication of logging
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.propagate = False

    return logger


def extract_json_from_text(text):
    """
    Extracts JSON content from a given text and returns it as a Python dictionary.

    Args:
        text (str): The input text containing JSON content.

    Returns:
        dict: Parsed JSON data.
    """
    try:
        # Use regex to extract JSON content (contained between {})
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)
            return json.loads(json_content)

        # If no JSON content is found, raise an error
        raise ValueError("No JSON content found in the text.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}") from e


def remove_triple_backtics(input_text: str) -> str:
    """
    Remove triple backtics from a string containing python code
    """
    _text = input_text.replace("```python", "")
    _text = _text.replace("```", "")
    return _text


def get_security_config_and_signer(auth_type):
    """
    Get the security config and signer based on the authentication type.
    Args:
        auth_type (str): The authentication type to use. Options are:
            - "API_KEY": Uses API key authentication (default).
            - "INSTANCE_PRINCIPAL": Uses instance principal authentication.
    Returns:
        tuple: A tuple containing the config and signer.
    """
    logger = get_console_logger()

    if auth_type == "API_KEY":
        config = oci.config.from_file()
        signer = None

        if DEBUG:
            logger.info("Queue client, using API_KEY...")
            logger.debug("Config: %s", config)
    elif auth_type == "INSTANCE_PRINCIPAL":
        # set the signer to use instance principal
        config = {}
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()

        if DEBUG:
            logger.info("Queue client, using INSTANCE_PRINCIPAL...")
            logger.debug("Config: %s", config)
            logger.debug("Signer: %s", signer)
    else:
        raise ValueError(
            "Unsupported authentication type. Use 'API_KEY' or 'INSTANCE_PRINCIPAL'."
        )
    return config, signer
