"""
File name: oci_models.py
Author: Luigi Saetta
Date last modified: 2025-03-31
Python Version: 3.11

Description:
    This module enables easy access to OCI GenAI LLM.


Usage:
    Import this module into other scripts to use its functions.
    Example:
        from oci_models import get_llm

License:
    This code is released under the MIT License.

Notes:
    This is a part of a demo showing how to implement an advanced
    RAG solution as a LangGraph agent.

Warnings:
    This module is in development, may change in future versions.
"""

from langchain_community.chat_models import ChatOCIGenAI

from .utils import get_console_logger

logger = get_console_logger()


def get_llm(
    auth_type,
    model_id,
    service_endpoint,
    compartment_id,
    temperature=0.0,
    max_tokens=2048,
):
    """
    Initialize and return an instance of ChatOCIGenAI with the specified configuration.

    Returns:
        ChatOCIGenAI: An instance of the OCI GenAI language model.
    """
    llm = ChatOCIGenAI(
        auth_type=auth_type,
        model_id=model_id,
        service_endpoint=service_endpoint,
        compartment_id=compartment_id,
        is_stream=True,
        model_kwargs={
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )
    return llm
