"""Тесты для AsyncClient."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ctrader_open_api_async import AsyncClient, EndPoints
from ctrader_open_api_async.messages.OpenApiCommonMessages_pb2 import ProtoMessage
from ctrader_open_api_async.messages.OpenApiMessages_pb2 import (
    ProtoOAApplicationAuthReq,
)


class TestAsyncClient:
    """Тесты для класса AsyncClient."""

    @pytest.fixture
    def client(self):
        """Создает экземпляр клиента для тестов."""
        return AsyncClient(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT)

    def test_client_initialization(self, client):
        """Тест инициализации клиента."""
        assert client.host == EndPoints.PROTOBUF_DEMO_HOST
        assert client.port == EndPoints.PROTOBUF_PORT
        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_start_service_success(self, client):
        """Тест успешного запуска сервиса."""
        with patch.object(client, "protocol", None):
            with patch(
                "ctrader_open_api_async.client.AsyncTcpProtocol"
            ) as mock_protocol_class:
                mock_protocol = AsyncMock()
                mock_protocol_class.return_value = mock_protocol

                await client.start_service()

                assert client._running is True
                mock_protocol.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_service_already_running(self, client):
        """Тест запуска уже запущенного сервиса."""
        client._running = True

        await client.start_service()

        # Должен просто вернуться без действий
        assert client._running is True

    @pytest.mark.asyncio
    async def test_stop_service(self, client):
        """Тест остановки сервиса."""
        # Имитируем запущенное состояние
        client._running = True
        client.protocol = AsyncMock()

        await client.stop_service()

        assert client._running is False
        assert client.protocol is None

    @pytest.mark.asyncio
    async def test_send_not_connected(self, client):
        """Тест отправки сообщения без подключения."""
        request = ProtoOAApplicationAuthReq()

        with pytest.raises(ConnectionError, match="Клиент не подключен"):
            await client.send(request)

    @pytest.mark.asyncio
    async def test_send_success(self, client):
        """Тест успешной отправки сообщения."""
        # Имитируем подключенное состояние
        client.is_connected = True
        client.protocol = AsyncMock()

        # Создаем мок ответа
        mock_response = ProtoMessage()
        mock_response.clientMsgId = "test-id"

        # Имитируем получение ответа
        async def mock_send(message, client_msg_id=None):
            # Симулируем получение ответа через callback
            await client._on_message_received(mock_response)

        client.protocol.send = mock_send

        request = ProtoOAApplicationAuthReq()
        response = await client.send(request, client_msg_id="test-id")

        assert response == mock_response

    def test_callback_setters(self, client):
        """Тест установки callback функций."""

        def dummy_callback():
            pass

        client.set_connected_callback(dummy_callback)
        client.set_disconnected_callback(dummy_callback)
        client.set_message_received_callback(dummy_callback)

        assert client._connected_callback == dummy_callback
        assert client._disconnected_callback == dummy_callback
        assert client._message_received_callback == dummy_callback

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Тест использования как контекстного менеджера."""
        with patch.object(client, "start_service") as mock_start:
            with patch.object(client, "stop_service") as mock_stop:
                async with client:
                    pass

                mock_start.assert_called_once()
                mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_application_auth_req(self, client):
        """Тест отправки запроса аутентификации приложения."""
        client.is_connected = True
        client.protocol = AsyncMock()

        # Мокаем метод send
        mock_response = ProtoMessage()
        with patch.object(client, "send", return_value=mock_response) as mock_send:
            response = await client.send_application_auth_req(
                "client_id", "client_secret"
            )

            assert response == mock_response
            mock_send.assert_called_once()
            # Проверяем, что первый аргумент - это protobuf объект с правильными данными
            args, kwargs = mock_send.call_args
            request = args[0]
            assert isinstance(request, ProtoOAApplicationAuthReq)
            assert request.clientId == "client_id"
            assert request.clientSecret == "client_secret"


class TestClientIntegration:
    """Интеграционные тесты (требуют реального подключения)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_connection(self):
        """Тест реального подключения к demo серверу."""
        client = AsyncClient(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT)

        try:
            await client.start_service()
            # Даем время на подключение
            await asyncio.sleep(1)
            assert client.is_connected is True
        except Exception as e:
            pytest.skip(f"Не удалось подключиться к demo серверу: {e}")
        finally:
            if client._running:
                await client.stop_service()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_auth_request(self):
        """Тест аутентификации (требует реальных учетных данных)."""
        # Этот тест пропускается, если нет учетных данных
        pytest.skip("Требует реальных учетных данных для тестирования")


# Конфигурация pytest для интеграционных тестов
def pytest_configure(config):
    """Конфигурация pytest."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require network)"
    )
