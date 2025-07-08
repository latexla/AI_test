# core/utils/file_utils.py
import os
import json
import logging
from pathlib import Path
from typing import Union, Optional, List, Dict, Any
import shutil

logger = logging.getLogger(__name__)

class FileUtils:
    """
    Утилиты для работы с файлами:
    - Чтение/запись Java-файлов
    - Обработка JSON (тест-кейсы, конфиги)
    - Управление директориями
    - Валидация путей
    """

    @staticmethod
    def read_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> Optional[str]:
        """
        Безопасное чтение файла с обработкой ошибок
        
        Args:
            file_path: Путь к файлу
            encoding: Кодировка файла
            
        Returns:
            Содержимое файла или None при ошибке
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            logger.error(f"File read error {file_path}: {str(e)}")
            return None

    @staticmethod
    def write_file(
        content: str,
        file_path: Union[str, Path],
        encoding: str = 'utf-8',
        overwrite: bool = True
    ) -> bool:
        """
        Безопасная запись в файл
        
        Args:
            content: Данные для записи
            file_path: Путь назначения
            encoding: Кодировка файла
            overwrite: Перезаписывать существующий файл
            
        Returns:
            True если запись успешна
        """
        try:
            path = Path(file_path)
            if path.exists() and not overwrite:
                logger.warning(f"File already exists {file_path}")
                return False
                
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"File write error {file_path}: {str(e)}")
            return False

    @staticmethod
    def read_json(file_path: Union[str, Path]) -> Optional[Union[Dict, List]]:
        """
        Чтение JSON файла
        
        Args:
            file_path: Путь к JSON-файлу
            
        Returns:
            Данные из файла или None при ошибке
        """
        content = FileUtils.read_file(file_path)
        if content is None:
            return None
            
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON {file_path}: {str(e)}")
            return None

    @staticmethod
    def write_json(
        data: Union[Dict, List],
        file_path: Union[str, Path],
        indent: int = 4,
        ensure_ascii: bool = False
    ) -> bool:
        """
        Запись данных в JSON файл
        
        Args:
            data: Данные для записи
            file_path: Путь назначения
            indent: Отступы в файле
            ensure_ascii: Экранирование non-ASCII символов
            
        Returns:
            True если запись успешна
        """
        try:
            json_str = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
            return FileUtils.write_file(json_str, file_path)
        except Exception as e:
            logger.error(f"JSON write error {file_path}: {str(e)}")
            return False

    @staticmethod
    def prepare_java_file_path(
        output_dir: Union[str, Path],
        package: Optional[str] = None,
        class_name: Optional[str] = None,
        content: Optional[str] = None
    ) -> Path:
        """
        Формирует корректный путь для Java-файла на основе package и class_name
        
        Args:
            output_dir: Базовая директория
            package: Пакет из Java-файла (например 'com.example.tests')
            class_name: Имя класса (если не указано, будет извлечено из content)
            content: Исходный код Java-файла
            
        Returns:
            Полный путь для сохранения
        """
        path = Path(output_dir)
        
        # Добавляем package в путь
        if package:
            package_path = package.replace('.', '/')
            path = path / package_path
            
        # Определяем имя файла
        if class_name:
            filename = f"{class_name}.java"
        elif content:
            class_name = FileUtils.extract_java_class_name(content)
            filename = f"{class_name}.java" if class_name else "GeneratedTest.java"
        else:
            filename = "GeneratedTest.java"
            
        return path / filename

    @staticmethod
    def extract_java_class_name(content: str) -> Optional[str]:
        """
        Извлекает имя класса из Java-кода
        
        Args:
            content: Исходный код Java-файла
            
        Returns:
            Имя класса или None если не найдено
        """
        match = re.search(r'class\s+(\w+)', content)
        return match.group(1) if match else None

    @staticmethod
    def clean_directory(dir_path: Union[str, Path]) -> bool:
        """
        Очистка директории (удаление всех файлов)
        
        Args:
            dir_path: Путь к директории
            
        Returns:
            True если операция успешна
        """
        try:
            path = Path(dir_path)
            if path.exists():
                shutil.rmtree(path)
            path.mkdir(parents=True)
            return True
        except Exception as e:
            logger.error(f"Directory clean error {dir_path}: {str(e)}")
            return False