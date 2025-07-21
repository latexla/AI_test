import re
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from .curl_parser import CurlParser

class JavaTestHandler:
    @staticmethod
    def parse_java_file(file_path: str) -> Dict:
        """Извлечение метаданных из Java-теста"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {
            'package': re.search(r'package\s+([^;]+);', content).group(1) if re.search(r'package\s+([^;]+);', content) else None,
            'imports': re.findall(r'import\s+([^;]+);', content),
            'test_class': re.search(r'class\s+(\w+)', content).group(1),
            'test_methods': re.findall(r'@Test\s+public\s+void\s+(\w+)', content)
        }

    @staticmethod
    def save_java_test(test_code: str, output_dir: str, base_name: str = "GeneratedTest") -> str:
        """
        Сохранение сгенерированного теста в .java файл
        :param test_code: Строка с Java-кодом
        :param output_dir: Папка для сохранения
        :param base_name: Базовое имя файла
        :return: Путь к сохраненному файлу
        """
        Path(output_dir).mkdir(exist_ok=True)
        
        # Извлекаем имя класса из кода
        class_match = re.search(r'class\s+(\w+)', test_code)
        file_name = f"{class_match.group(1) if class_match else base_name}.java"
        file_path = Path(output_dir) / file_name
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        return str(file_path)
    
class TestingAgent:
    def __init__(self, rag_service, sources_dir: str):
        self.rag = rag_service
        self.java_handler = JavaTestHandler()
        self.curl_parser = CurlParser()
        self.sources_dir = sources_dir

    def load_java_examples(self) -> List[Dict]:
        """Загрузка примеров тестов для контекста RAG"""
        examples = []
        for file in Path(self.sources_dir).glob('*Test.java'):
            with open(file, 'r', encoding='utf-8') as f:
                examples.append({
                    'file_name': file.name,
                    'content': f.read()
                })
        return examples

    def generate_new_test(self, requirements: str) -> Dict:
        """Генерация нового теста на основе требований"""
        examples = self.load_java_examples()
        context = "\n".join([ex['content'] for ex in examples[:3]])  # Берем 3 примера
        
        generated_code = self.rag.generate_java_test(
            context=context,
            prompt=f"Сгенерируй JUnit тест со следующими требованиями:\n{requirements}"
        )
        
        # Пост-обработка кода
        generated_code = self._fix_code_formatting(generated_code)
        
        # Сохранение
        saved_path = self.java_handler.save_java_test(
            test_code=generated_code,
            output_dir=os.path.join(self.sources_dir, "generated")
        )
        
        return {
            'status': 'success',
            'file_path': saved_path,
            'code': generated_code
        }

    @staticmethod
    def _fix_code_formatting(code: str) -> str:
        """Исправление частых проблем в сгенерированном коде"""
        # Удаление Markdown-обрамления (если есть)
        if code.startswith("```"):
            lang = code[3:code.find('\n')]
            code = code[code.find('\n')+1:]
            if code.endswith("```"):
                code = code[:-3]
        return code.strip()

    def generate_api_test_from_curl(self, curl_command: str, framework: str = "java") -> Dict:
        """
        Генерация API теста из cURL команды
        
        :param curl_command: cURL команда
        :param framework: Фреймворк для теста (java/python)
        :return: Результат генерации теста
        """
        # Разбор cURL
        curl_data = self.curl_parser.parse_curl(curl_command)
        if not curl_data['valid']:
            return {
                'status': 'error',
                'error': curl_data.get('error', 'Invalid cURL command')
            }

        # Генерация описания для RAG
        test_desc = self.curl_parser.generate_test_description(curl_data)
        
        # Генерация теста
        if framework == "java":
            return self._generate_java_api_test(test_desc)
        elif framework == "python":
            return self._generate_python_api_test(test_desc)
        else:
            return {
                'status': 'error',
                'error': f'Unsupported framework: {framework}'
            }

    def _generate_java_api_test(self, test_desc: str) -> Dict:
        """Генерация Java API теста"""
        prompt = f"""Сгенерируй JUnit тест для API на основе следующего описания:
{test_desc}
Включи проверки:
- Статус код ответа
- Структуру JSON ответа
- Время выполнения запроса"""
        
        generated_code = self.rag.generate_java_test(prompt=prompt)
        generated_code = self._fix_code_formatting(generated_code)
        
        saved_path = self.java_handler.save_java_test(
            test_code=generated_code,
            output_dir=os.path.join(self.sources_dir, "generated")
        )
        
        return {
            'status': 'success',
            'file_path': saved_path,
            'code': generated_code
        }

    def _generate_python_api_test(self, test_desc: str) -> Dict:
        """Генерация Python API теста"""
        prompt = f"""Сгенерируй pytest тест для API на основе следующего описания:
{test_desc}
Включи проверки:
- Статус код ответа
- Структуру JSON ответа
- Время выполнения запроса
Используй библиотеку requests"""
        
        # TODO: Реализовать после добавления PythonTestHandler
        return {
            'status': 'error',
            'error': 'Python tests not implemented yet'
        }
    def generate_test_with_docs(
        self,
        class_desc: str,
        method_descs: Dict[str, str],
        examples_count: int = 3
    ) -> Dict:
        """
        Генерация теста с документацией
        
        :param class_desc: Описание класса
        :param method_descs: {"methodName": "описание"}
        :param examples_count: Сколько примеров использовать из базы
        :return: {"code": str, "metadata": Dict}
        """
        # Получаем примеры из базы знаний
        docs = self.rag.vector_store.similarity_search(
            query=class_desc,
            k=examples_count
        )
        
        # Генерация кода
        java_code = self.rag.generate_java_test_with_javadoc(
            context=docs,
            class_description=class_desc,
            method_descriptions=method_descs
        )
        
        # Валидация Javadoc
        validated_code = self._validate_javadoc(java_code)
        
        return {
            "code": validated_code,
            "metadata": self._extract_metadata(validated_code)
        }

    @staticmethod
    def _validate_javadoc(code: str) -> str:
        """Проверка структуры Javadoc"""
        # Проверяем наличие обязательных тегов
        required_tags = ["@author", "@version"]
        for tag in required_tags:
            if tag not in code:
                code = code.replace("/**", f"/**\n * {tag} Generated")
        return code
