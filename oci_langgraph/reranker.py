"""
File name: reranker.py
Author: Luigi Saetta
Date last modified: 2025-03-31
Python Version: 3.11

Description:
    This module implements filtering and reranking documents
    returned by Similarity Search, using a LLM

Usage:
    Import this module into other scripts to use its functions.

    It expects two fields in the input state:
        - standalone_question: The user query to be reranked.
        - retriever_docs: A list of documents to be reranked.
        user_request = input.get("standalone_question", "")
        retriever_docs = input.get("retriever_docs", [])

License:
    This code is released under the MIT License.

Notes:
    This is a part of a demo showing how to implement an advanced
    RAG solution as a LangGraph agent.

Warnings:
    This module is in development, may change in future versions.
"""

import os

# Import traceback for better error logging
import traceback
from langchain_core.messages import HumanMessage
from langchain.prompts import PromptTemplate


from .agent_base import AgentBase
from .oci_genai_models import get_llm
from .utils import extract_json_from_text

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")


class Reranker(AgentBase):
    """
    Implements a reranker using a LLM
    This class is responsible for reranking documents based on their relevance
    to a given user query. It uses a large language model (LLM) to evaluate
    the relevance of text chunks and returns a sorted list of relevant chunks.
    """

    def __init__(
        self,
        agent_name: str,
        compartment_id: str,
        auth_type="API_KEY",
        model_id="meta.llama-3.3-70b-instruct",
        service_endpoint="https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com",
        top_k: int = 10,
        **kwargs,
    ):
        """
        Initialize the Reranker with the given configuration.

        Args:
        -----------
        agent_name: The name of the agent.
        compartment_id: The compartment ID for OCI.
        auth_type: The authentication type (default is API_KEY).
        model_id: The model ID for the LLM (default is meta.llama-3.3-70b-instruct).
        service_endpoint: The service endpoint for the LLM (default is OCI endpoint).
        top_k: The number of top documents to consider (default is 10).
        name: The name of the span (default is "Reranker").
        temperature: The temperature for the LLM (default is 0.0).
        max_tokens: The maximum number of tokens for the LLM (default is 2048).
        """
        super().__init__(agent_name, kwargs.get("name", "Reranker"))

        self.compartment_id = compartment_id
        self.auth_type = auth_type
        self.model_id = model_id
        self.service_endpoint = service_endpoint
        self.top_k = top_k

        self.name = kwargs.get("name", "Reranker")
        self.temperature = kwargs.get("temperature", 0.0)
        self.max_tokens = kwargs.get("max_tokens", 2048)

        self.reranker_template = """
        You are an intelligent ranking assistant. Your task is to rank and filter text chunks 
        based on their relevance to a given user query. You will receive:

        1. A user query.
        2. A list of text chunks.

        Your goal is to:
        - Rank the text chunks in order of relevance to the user query.
        - Remove any text chunks that are completely irrelevant to the query.

        ### Instructions:
        - Assign a **relevance score** to each chunk based on how well it answers or relates to the query.
        - Return only the **top-ranked** chunks, filtering out those that are completely irrelevant.
        - The output should be a **sorted list** of relevant chunks, from most to least relevant.
        - Return only the JSON, don't add other text.
        - Don't return the text of the chunk, only the index and the score.

        ### Input Format:
        User Query:
        {query}

        Text Chunks (list indexed from 0):
        {chunks}

        ### **Output Format:**
        Return a **JSON object** with the following format:
        ```json
        {{
        "ranked_chunks": [
            {{"index": 0, "score": X.X}},
            {{"index": 2, "score": Y.Y}},
            ...
        ]
        }}
        ```
        Where:
        - "index" is the original position of the chunk in the input list. Index starts from 0.
        - "score" is the relevance score (higher is better).

        Ensure that only relevant chunks are included in the output. If no chunk is relevant, return an empty list.

        """

    def generate_refs(self, docs: list):
        """
        Returns a list of reference dictionaries used in the reranker.
        """
        return [
            {"source": doc.metadata["source"], "page": doc.metadata["page_label"]}
            for doc in docs
        ]

    def get_reranked_docs(self, llm, query, retriever_docs):
        """
        Rerank documents using LLM based on user request.

        query: the search query (can be reformulated)
        retriever_docs: list of Langchain Documents
        """
        # Prepare chunk texts
        chunks = [doc.page_content for doc in retriever_docs]

        _prompt = PromptTemplate(
            input_variables=["query", "chunks"],
            template=self.reranker_template,
        ).format(query=query, chunks=chunks)

        messages = [HumanMessage(content=_prompt)]

        reranker_output = llm.invoke(messages).content

        # Extract ranking order
        json_dict = extract_json_from_text(reranker_output)

        if DEBUG:
            self.info(json_dict.get("ranked_chunks", "No ranked chunks found."))

        # Get indexes and sort documents
        # added < TOP_K (hallucinations ?)
        indexes = [
            chunk["index"]
            for chunk in json_dict.get("ranked_chunks", [])
            if chunk["index"] < self.top_k
        ]

        return [retriever_docs[i] for i in indexes]

    def handle_invoke(self, input, config=None, **kwargs):
        """
        Implements reranking logic.

        input: The agent state.
        """
        user_request = input.get("standalone_question", "")
        retriever_docs = input.get("retriever_docs", [])
        error = None

        if DEBUG:
            self.info("Reranker input state: %s", input)

        try:
            if retriever_docs:
                # there is something to rerank!
                llm = get_llm(
                    auth_type=self.auth_type,
                    model_id=self.model_id,
                    service_endpoint=self.service_endpoint,
                    compartment_id=self.compartment_id,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                # rerank documents
                reranked_docs = self.get_reranked_docs(
                    llm, user_request, retriever_docs
                )
            else:
                reranked_docs = []

        except Exception as e:
            self.error("Error in reranker: %s", e)
            self.debug(traceback.format_exc())
            error = str(e)
            # Fallback to original documents
            reranked_docs = retriever_docs

        # Get reference citations
        citations = self.generate_refs(reranked_docs)

        return {"reranker_docs": reranked_docs, "citations": citations, "error": error}

    def set_reranker_template(self, reranker_template: str):
        """
        Set the reranker template.
        """
        self.reranker_template = reranker_template
