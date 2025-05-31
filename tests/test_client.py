"""Тесты для AsyncClient."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ctrader_open_api_async import AsyncClient, EndPoints
from ctrader_open_api_async.messages.OpenApiCommonMessages_pb2 import *
from ctrader_open_api_async.messages.OpenApiMessages_pb2 import *


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
    async def test_connect_success(self, client):
        """Тест успешного подключения."""
        with patch.object(client, '_create_connection') as mock_connect:
            mock_connect.return_value = AsyncMock()
            
            await client.connect()
            
            assert client.is_connected is True
            mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_failure(self, client):
        """Тест неудачного подключения."""
        with patch.object(client, '_create_connection') as mock_connect:
            mock_connect.side_effect = ConnectionError("Connection failed")
            
            with pytest.raises(ConnectionError):
                await client.connect()
            
            assert client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect(self, client):
        """Тест отключения."""
        # Имитируем подключенное состояние
        client.is_connected = True
        client._writer = AsyncMock()
        
        await client.disconnect()
        
        assert client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_send_request_not_connected(self, client):
        """Тест отправки запроса без подключения."""
        request = ProtoOAApplicationAuthReq()
        
        with pytest.raises(ConnectionError, match="Not connected"):
            await client.send_request(request)
    
    @pytest.mark.asyncio
    async def test_send_request_success(self, client):
        """Тест успешной отправки запроса."""
        # Имитируем подключенное состояние
        client.is_connected = True
        client._writer = AsyncMock()
        
        # Создаем мок ответа
        mock_response = ProtoOAApplicationAuthRes()
        
        with patch.object(client, '_wait_for_response') as mock_wait:
            mock_wait.return_value = mock_response
            
            request = ProtoOAApplicationAuthReq()
            response = await client.send_request(request)
            
            assert response == mock_response
            client._writer.write.assert_called_once()
    
    def test_message_type_mapping(self, client):
        """Тест маппинга типов сообщений."""
        # Проверяем, что маппинг содержит основные типы
        assert ProtoOAPayloadType.PROTO_OA_APPLICATION_AUTH_REQ in client._message_type_mapping
        assert ProtoOAPayloadType.PROTO_OA_APPLICATION_AUTH_RES in client._message_type_mapping
    
    @pytest.mark.asyncio
    async def test_message_stream(self, client):
        """Тест потока сообщений."""
        # Имитируем подключенное состояние
        client.is_connected = True
        
        # Создаем мок сообщений
        mock_messages = [
            MagicMock(payloadType=ProtoOAPayloadType.PROTO_OA_SPOT_EVENT),
            MagicMock(payloadType=ProtoOAPayloadType.PROTO_OA_EXECUTION_EVENT),
        ]
        
        async def mock_message_generator():
            for msg in mock_messages:
                yield msg
        
        with patch.object(client, '_read_messages') as mock_read:
            mock_read.return_value = mock_message_generator()
            
            messages = []
            async for message in client.message_stream():
                messages.append(message)
                if len(messages) >= 2:
                    break
            
            assert len(messages) == 2
            assert messages[0].payloadType == ProtoOAPayloadType.PROTO_OA_SPOT_EVENT
            assert messages[1].payloadType == ProtoOAPayloadType.PROTO_OA_EXECUTION_EVENT


class TestClientIntegration:
    """Интеграционные тесты (требуют реального подключения)."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_connection(self):
        """Тест реального подключения к demo серверу."""
        client = AsyncClient(EndPoints.PROTOBUF_DEMO_HOST, EndPoints.PROTOBUF_PORT)
        
        try:
            await client.connect()
            assert client.is_connected is True
        except Exception as e:
            pytest.skip(f"Не удалось подключиться к demo серверу: {e}")
        finally:
            if client.is_connected:
                await client.disconnect()
    
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