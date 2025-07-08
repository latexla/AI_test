import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

class Settings:
    """
    Класс для управления настройками проекта.
    Поддерживает загрузку из:
    - Переменных окружения (.env)
    - JSON-конфигов
    - Значений по умолчанию
    """
    
    def __init__(self):
        # Пути к данным
        self.INPUT_DATA_DIR = self._get_setting('INPUT_DATA_DIR', 'input_data')
        self.OUTPUT_DIR = self._get_setting('OUTPUT_DIR', 'output')
        
        # Настройки GigaChat API
        self.GIGACHAT_CREDENTIALS = self._get_required('GIGACHAT_CREDENTIALS')
        self.GIGACHAT_MODEL = self._get_setting('GIGACHAT_MODEL', 'GigaChat')
        
        # Настройки логирования
        self.LOG_LEVEL = self._get_setting('LOG_LEVEL', 'INFO')
        self.LOG_FILE = self._get_setting('LOG_FILE', 'logs/app.log')
        
        # Дополнительные параметры
        self.TEST_MODE = self._get_bool('TEST_MODE', False)
        self.MAX_FILE_SIZE_MB = self._get_int('MAX_FILE_SIZE_MB', 10)
        
        # Загрузка кастомных настроек из JSON
        self._load_custom_config()
    
    def _get_setting(self, key: str, default: Any = None) -> Any:
        """Получение значения с fallback на default"""
        return os.getenv(key, default)
    
    def _get_required(self, key: str) -> str:
        """Получение обязательного параметра"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Требуется переменная окружения: {key}")
        return value
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Парсинг булевых значений"""
        val = os.getenv(key, str(default)).lower()
        return val in ('true', '1', 't', 'y', 'yes')
    
    def _get_int(self, key: str, default: int) -> int:
        """Парсинг целых чисел"""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def _load_custom_config(self) -> None:
        """Загрузка дополнительных настроек из JSON"""
        config_path = Path(self.INPUT_DATA_DIR) / 'config.json'
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                for key, value in custom_config.items():
                    setattr(self, key, value)
            except Exception as e:
                print(f"Ошибка загрузки config.json: {e}")
    
    def get_rag_parameters(self) -> Dict[str, Any]:
        """Параметры для инициализации RAG"""
        return {
            'auth_token': self.GIGACHAT_CREDENTIALS,
            'model_name': self.GIGACHAT_MODEL,
            'chunk_size': 500,
            'chunk_overlap': 100
        }

# Глобальный экземпляр настроек
SETTINGS = Settings()

def get_settings() -> Settings:
    """Функция для получения актуальных настроек"""
    return SETTINGS

def reload_settings() -> None:
    """Перезагрузка настроек (для тестов)"""
    global SETTINGS
    SETTINGS = Settings()