"""
agent_base.py

Author: L. Saetta

AgentBase class provide a base class to implement a node in the LangGraph graph.
The framework will call the invoke() method.
This class implement the Template Method Design pattern.

License: Mit

"""

from abc import ABC, abstractmethod
from langchain_core.runnables import Runnable

# integration with OCI APM
from py_zipkin.zipkin import zipkin_span

from .utils import get_console_logger

logger = get_console_logger()


class AgentBase(Runnable, ABC):
    """
    AgentBase class provide a base class to implement a node in the LanGraph graph.
    """

    def __init__(self, agent_name: str, name: str):
        """
        Constructor of the AgentBase class.

        :param agent_name: the name of the agent
        :param name: the name of the step
        """
        self.agent_name = agent_name
        self.name = name

    def invoke(self, input, config=None, **kwargs):
        """
        Invoke the agent with the given input and configuration.

        :param input: The input to the agent.
        :param config: The configuration for the agent.
        :param kwargs: Additional arguments.
        :return: The output of the agent.
        """

        # this way you get automatically integration with OCI APM
        # to enable you need to configure it
        with zipkin_span(service_name=self.agent_name, span_name=self.name):
            return self.handle_invoke(input, config, **kwargs)

    @abstractmethod
    def handle_invoke(self, input, config=None, **kwargs):
        """
        Handle the invocation of the agent.
        This method must be implemented by subclasses.

        :param input: The input to the agent.
        :param config: The configuration for the agent.
        :param kwargs: Additional arguments.
        :return: The output of the agent.
        """
