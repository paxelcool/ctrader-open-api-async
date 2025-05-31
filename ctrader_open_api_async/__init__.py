"""Async/await версия cTrader Open API библиотеки."""

from . import messages
from .auth import AsyncAuth
from .client import AsyncClient
from .endpoints import EndPoints
from .protobuf import Protobuf
from .tcp_protocol import AsyncTcpProtocol

__author__ = "AsyncIO Port"
__email__ = "async@ctrader.com"
__version__ = "2.0.0"

__all__ = [
    "AsyncClient",
    "Protobuf",
    "AsyncTcpProtocol",
    "AsyncAuth",
    "EndPoints",
    "messages",
]
