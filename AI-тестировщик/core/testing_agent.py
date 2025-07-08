import re
from pathlib import Path
from typing import List, Dict

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
    def __init__(self, rag_service, java_sources_dir: str):
        self.rag = rag_service
        self.java_handler = JavaTestHandler()
        self.sources_dir = java_sources_dir

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
        if code.startswith("```java"):
            code = code[7:-3] if code.endswith("```") else code[7:]
        return code.strip()
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