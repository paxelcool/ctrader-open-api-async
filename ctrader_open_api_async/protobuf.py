"""Модуль для работы с Protocol Buffers сообщениями."""

import re
from typing import Dict, Type, Any, Optional


class Protobuf:
    """Класс для работы с Protobuf сообщениями cTrader API."""
    
    _protos: Dict[int, Type] = {}
    _names: Dict[str, int] = {}
    _abbr_names: Dict[str, int] = {}

    @classmethod
    def populate(cls) -> Dict[int, Type]:
        """Заполняет внутренние словари доступными Protobuf сообщениями."""
        if cls._protos:
            return cls._protos
            
        try:
            # Импортируем сообщения из локальной папки messages
            from .messages import OpenApiCommonMessages_pb2 as o1
            from .messages import OpenApiMessages_pb2 as o2

            for name in dir(o1) + dir(o2):
                if not name.startswith("Proto"):
                    continue

                m = o1 if hasattr(o1, name) else o2
                klass = getattr(m, name)
                
                # Проверяем, что это действительно Protobuf класс
                if hasattr(klass, 'payloadType'):
                    payload_type = klass().payloadType
                    cls._protos[payload_type] = klass
                    cls._names[klass.__name__] = payload_type
                    
                    # Создаем сокращенное имя
                    abbr_name = re.sub(r'^Proto(OA)?(.*)', r'\2', klass.__name__)
                    cls._abbr_names[abbr_name] = payload_type
                    
        except ImportError as e:
            raise ImportError(
                "Не удалось импортировать Protobuf сообщения. "
                "Убедитесь, что файлы messages находятся в правильной папке"
            ) from e
            
        return cls._protos

    @classmethod
    def get(cls, payload: Any, fail: bool = True, **params) -> Optional[Any]:
        """Получает экземпляр Protobuf сообщения по типу или имени."""
        if not cls._protos:
            cls.populate()

        # Если передан числовой тип
        if isinstance(payload, int) and payload in cls._protos:
            return cls._protos[payload](**params)

        # Если передана строка - ищем по имени
        if isinstance(payload, str):
            for d in [cls._names, cls._abbr_names]:
                if payload in d:
                    payload_type = d[payload]
                    return cls._protos[payload_type](**params)

        if fail:
            raise IndexError(f"Неверный тип сообщения: {payload}")
        return None

    @classmethod
    def get_type(cls, payload: Any, **params) -> int:
        """Получает тип Protobuf сообщения."""
        proto = cls.get(payload, **params)
        return proto.payloadType

    @classmethod
    def extract(cls, message: Any) -> Any:
        """Извлекает содержимое из ProtoMessage."""
        if not cls._protos:
            cls.populate()
            
        if message.payloadType not in cls._protos:
            raise ValueError(f"Неизвестный тип сообщения: {message.payloadType}")
            
        payload_class = cls._protos[message.payloadType]
        payload = payload_class()
        payload.ParseFromString(message.payload)
        return payload

    @classmethod
    def get_all_types(cls) -> Dict[int, Type]:
        """Возвращает все доступные типы сообщений."""
        if not cls._protos:
            cls.populate()
        return cls._protos.copy()

    @classmethod
    def get_message_name(cls, payload_type: int) -> Optional[str]:
        """Получает имя сообщения по его типу."""
        if not cls._protos:
            cls.populate()
            
        if payload_type in cls._protos:
            return cls._protos[payload_type].__name__
        return None 