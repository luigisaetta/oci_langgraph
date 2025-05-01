"""
Utils
"""

import re
import json
import logging


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
        raise ValueError(f"Invalid JSON format: {e}")


def remove_triple_backtics(input_text: str) -> str:
    """
    Remove triple backtics from a string
    """
    _text = input_text.replace("```python", "")
    _text = _text.replace("```", "")
    return _text
