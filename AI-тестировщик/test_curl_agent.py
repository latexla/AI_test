import os
import subprocess
import logging
from pathlib import Path
from core.rag_service import RAGService
from core.testing_agent import TestingAgent
from configs import get_settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_java_test(test_path: str) -> bool:
    """Валидация сгенерированного Java теста"""
    try:
        # Компиляция теста
        # Формируем абсолютные пути к JAR файлам
        junit_jar = str(Path("junit-4.13.2.jar").absolute())
        hamcrest_jar = str(Path("hamcrest-core-1.3.jar").absolute())
        
        compile_result = subprocess.run(
            ["javac", "-cp", f"{junit_jar};{hamcrest_jar};.", test_path],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if compile_result.returncode != 0:
            logger.error(f"Ошибка компиляции:\n{compile_result.stderr}")
            return False

        # Запуск теста
        class_name = Path(test_path).stem
        test_result = subprocess.run(
            ["java", "-cp", "junit-4.13.2.jar:hamcrest-core-1.3.jar:.", 
             "org.junit.runner.JUnitCore", class_name],
            capture_output=True,
            text=True
        )

        if test_result.returncode == 0:
            logger.info("Тест успешно прошел валидацию")
            return True
        else:
            logger.error(f"Ошибка выполнения теста:\n{test_result.stdout}")
            return False

    except Exception as e:
        logger.error(f"Ошибка валидации теста: {str(e)}")
        return False

def main():
    try:
        # Пример cURL запроса
        curl_example = '''curl -X GET "https://jsonplaceholder.typicode.com/users/1" \
-H "Accept: application/json"'''

        logger.info("Инициализация сервисов...")
        settings = get_settings()
        rag = RAGService(
            auth_token=settings.GIGACHAT_CREDENTIALS,
            model_name=settings.GIGACHAT_MODEL
        )
        
        # Загрузка тестовых документов
        logger.info("Загрузка тестовых документов...")
        java_files = list(Path("input").glob("*.java"))
        if not java_files:
            logger.warning("Не найдены Java файлы в input/")
        else:
            rag.load_and_process_documents([str(f) for f in java_files])
        
        agent = TestingAgent(rag, "output/generated")

        logger.info("Генерация теста из cURL...")
        result = agent.generate_api_test_from_curl(curl_example)
        
        if result['status'] == 'success':
            logger.info(f"Тест сохранен в: {result['file_path']}")
            print("\nСгенерированный тест:")
            print(result['code'])
            
            # Валидация теста
            logger.info("Запуск валидации теста...")
            if validate_java_test(result['file_path']):
                logger.info("Тест валиден и работает корректно")
            else:
                logger.warning("Тест содержит ошибки")
        else:
            logger.error(f"Ошибка генерации: {result['error']}")

    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}")

if __name__ == "__main__":
    main()
