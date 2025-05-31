"""Асинхронный TCP протокол для cTrader API."""

import asyncio
import logging
import ssl
import struct
from collections import deque
from datetime import datetime
from typing import Any, Callable, Deque, Optional, Tuple

# Импортируем Protobuf сообщения
try:
    from .messages.OpenApiCommonMessages_pb2 import ProtoHeartbeatEvent, ProtoMessage

    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False

logger = logging.getLogger(__name__)


class AsyncTcpProtocol:
    """Асинхронный TCP протокол для cTrader API."""

    MAX_LENGTH = 15000000  # Максимальная длина сообщения

    def __init__(self, host: str, port: int, messages_per_second: int = 5):
        """Инициализация протокола.

        Args:
            host: Хост для подключения
            port: Порт для подключения
            ssl_context: SSL контекст (если None, создается автоматически)
            messages_per_second: Количество сообщений в секунду
        """
        if not PROTOBUF_AVAILABLE:
            raise ImportError("Для работы требуется библиотека ctrader-open-api")

        self.host = host
        self.port = port
        self.ssl_context = self._create_ssl_context()
        self.messages_per_second = messages_per_second

        # Соединение
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected = False

        # Очередь отправки сообщений
        self._send_queue: Deque[Tuple[Optional[Callable], bytes]] = deque()
        self._send_task: Optional[asyncio.Task] = None
        self._last_send_time: Optional[datetime] = None

        # Буфер для получения данных
        self._receive_buffer = b""

        # Обработчики событий
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_message_received: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Создает SSL контекст для безопасного соединения."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    async def connect(self) -> None:
        """Устанавливает соединение с сервером."""
        try:
            logger.info(f"Подключение к {self.host}:{self.port} с SSL")

            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port, ssl=self.ssl_context
            )

            self.is_connected = True
            logger.info("SSL соединение установлено")

            # Запускаем задачи
            asyncio.create_task(self._message_receiver())
            self._send_task = asyncio.create_task(self._message_sender())

            # Вызываем обработчик подключения
            if self.on_connected:
                await self._safe_call(self.on_connected)

        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            await self._handle_error(e)
            raise

    async def disconnect(self) -> None:
        """Закрывает соединение с сервером."""
        self.is_connected = False

        # Останавливаем задачу отправки
        if self._send_task and not self._send_task.done():
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass

        # Закрываем соединение
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
            self.reader = None

        # Вызываем обработчик отключения
        if self.on_disconnected:
            await self._safe_call(self.on_disconnected, "Manual disconnect")

        logger.info("Соединение закрыто")

    async def send(
        self,
        message: Any,
        instant: bool = False,
        client_msg_id: Optional[str] = None,
        is_canceled: Optional[Callable] = None,
    ) -> None:
        """Отправляет сообщение серверу.

        Args:
            message: Сообщение для отправки
            instant: Отправить немедленно (для heartbeat)
            client_msg_id: ID клиентского сообщения
            is_canceled: Функция проверки отмены
        """
        if not self.is_connected:
            raise ConnectionError("Соединение не установлено")

        data = await self._serialize_message(message, client_msg_id)

        if instant:
            await self._send_data(data)
            self._last_send_time = datetime.now()
        else:
            self._send_queue.append((is_canceled, data))

    async def heartbeat(self) -> None:
        """Отправляет heartbeat сообщение."""
        heartbeat_msg = ProtoHeartbeatEvent()
        await self.send(heartbeat_msg, instant=True)

    async def _serialize_message(
        self, message: Any, client_msg_id: Optional[str] = None
    ) -> bytes:
        """Сериализует сообщение в байты."""
        data = b""

        if isinstance(message, ProtoMessage):
            data = message.SerializeToString()
        elif isinstance(message, bytes):
            data = message
        elif hasattr(message, "SerializeToString") and hasattr(message, "payloadType"):
            # Это Protobuf сообщение
            proto_msg = ProtoMessage()
            proto_msg.payload = message.SerializeToString()
            proto_msg.payloadType = message.payloadType
            if client_msg_id:
                proto_msg.clientMsgId = client_msg_id
            data = proto_msg.SerializeToString()
        else:
            raise ValueError(f"Неподдерживаемый тип сообщения: {type(message)}")

        return data

    async def _send_data(self, data: bytes) -> None:
        """Отправляет данные по TCP соединению."""
        if not self.writer:
            raise ConnectionError("Writer не инициализирован")

        # Отправляем длину сообщения (4 байта в big-endian формате)
        length = struct.pack(">I", len(data))
        self.writer.write(length + data)
        await self.writer.drain()

        logger.debug(f"Отправлено сообщение {len(data)} байт")

    async def _message_sender(self) -> None:
        """Задача для отправки сообщений из очереди."""
        try:
            while self.is_connected:
                await asyncio.sleep(1.0 / self.messages_per_second)

                if not self._send_queue:
                    # Проверяем, нужно ли отправить heartbeat
                    if (
                        self._last_send_time is None
                        or (datetime.now() - self._last_send_time).total_seconds() > 20
                    ):
                        await self.heartbeat()
                    continue

                # Отправляем сообщения из очереди
                messages_to_send = min(len(self._send_queue), self.messages_per_second)

                for _ in range(messages_to_send):
                    if not self._send_queue:
                        break

                    is_canceled, data = self._send_queue.popleft()

                    # Проверяем, не отменено ли сообщение
                    if is_canceled and is_canceled():
                        continue

                    await self._send_data(data)

                self._last_send_time = datetime.now()

        except asyncio.CancelledError:
            logger.debug("Задача отправки сообщений отменена")
        except Exception as e:
            logger.error(f"Ошибка в задаче отправки: {e}")
            await self._handle_error(e)

    async def _message_receiver(self) -> None:
        """Задача для получения сообщений."""
        try:
            while self.is_connected and self.reader:
                # Читаем длину сообщения (4 байта в big-endian формате)
                length_data = await self._read_exact(4)
                if not length_data:
                    logger.warning("Соединение закрыто сервером")
                    break

                message_length = struct.unpack(">I", length_data)[0]
                logger.debug(f"Ожидается сообщение длиной {message_length} байт")

                # Проверяем разумность длины сообщения
                if message_length > self.MAX_LENGTH:
                    logger.error(f"Слишком большое сообщение: {message_length} байт")
                    break

                # Читаем само сообщение полностью
                message_data = await self._read_exact(message_length)
                if not message_data:
                    logger.warning("Не удалось прочитать данные сообщения")
                    break

                logger.debug(f"Получено сообщение {len(message_data)} байт")

                # Обрабатываем сообщение
                await self._process_message(message_data)

        except asyncio.CancelledError:
            logger.debug("Задача получения сообщений отменена")
        except Exception as e:
            logger.error(f"Ошибка в задаче получения: {e}")
            await self._handle_error(e)
        finally:
            self.is_connected = False

    async def _read_exact(self, size: int) -> bytes:
        """Читает точно указанное количество байт."""
        if not self.reader:
            return b""

        data = b""
        while len(data) < size:
            chunk = await self.reader.read(size - len(data))
            if not chunk:
                # Соединение закрыто
                return b""
            data += chunk
        return data

    async def _process_message(self, data: bytes) -> None:
        """Обрабатывает полученное сообщение."""
        try:
            # Парсим базовое сообщение
            msg = ProtoMessage()
            msg.ParseFromString(data)

            logger.debug(f"Получено сообщение типа {msg.payloadType}")

            # Обрабатываем heartbeat автоматически
            if msg.payloadType == ProtoHeartbeatEvent().payloadType:
                logger.debug("Получен heartbeat, отправляем ответ")
                await self.heartbeat()
                return

            # Вызываем обработчик сообщений
            if self.on_message_received:
                await self._safe_call(self.on_message_received, msg)

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await self._handle_error(e)

    async def _safe_call(self, callback: Callable, *args) -> None:
        """Безопасно вызывает callback функцию."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"Ошибка в callback: {e}")
            await self._handle_error(e)

    async def _handle_error(self, error: Exception) -> None:
        """Обрабатывает ошибки."""
        if self.on_error:
            await self._safe_call(self.on_error, error)

    def set_connected_callback(self, callback: Callable) -> None:
        """Устанавливает обработчик подключения."""
        self.on_connected = callback

    def set_disconnected_callback(self, callback: Callable) -> None:
        """Устанавливает обработчик отключения."""
        self.on_disconnected = callback

    def set_message_received_callback(self, callback: Callable) -> None:
        """Устанавливает обработчик получения сообщений."""
        self.on_message_received = callback

    def set_error_callback(self, callback: Callable) -> None:
        """Устанавливает обработчик ошибок."""
        self.on_error = callback

    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход."""
        await self.disconnect()
