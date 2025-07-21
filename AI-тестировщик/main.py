#!/usr/bin/env python3
"""
Главный модуль RAG-системы для генерации Java-тестов
"""

import os
import logging
from pathlib import Path
from typing import Dict

# Инициализация логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/rag_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Импорт компонентов проекта
from core.rag_service import RAGService
from core.testing_agent import TestingAgent
from core.openapi_parser import OpenAPIParser
from utils.file_utils import FileUtils
from configs import get_settings

def load_config() -> Dict:
    """Загрузка конфигурации"""
    settings = get_settings()
    return {
        'gigachat_creds': settings.GIGACHAT_CREDENTIALS,
        'input_dir': settings.INPUT_DATA_DIR,
        'output_dir': settings.OUTPUT_DIR,
        'model_name': settings.GIGACHAT_MODEL
    }

def initialize_services(config: Dict) -> tuple[RAGService, TestingAgent]:
    """Инициализация основных сервисов"""
    logger.info("Инициализация RAG сервиса...")
    rag = RAGService(
        auth_token=config['gigachat_creds'],
        model_name=config['model_name']
    )
    
    logger.info("Инициализация Testing Agent...")
    agent = TestingAgent(
        rag_service=rag,
        java_sources_dir=config['input_dir']
    )
    
    return rag, agent

def process_pdf_document(agent: TestingAgent, pdf_path: str) -> Dict:
    """Обработка PDF документа и генерация тестов"""
    logger.info(f"Обработка PDF документа: {pdf_path}")
    
    # Пример генерации теста
    test_code = agent.rag.generate_java_test_with_javadoc(
        context="Тестирование математических операций",
        class_description="Класс для тестирования базовых математических операций",
        method_descriptions={
            "testAddition": "Проверка корректности операции сложения",
            "testDivision": "Проверка обработки деления на ноль"
        }
    )
    
    # Сохранение результата
    output_path = os.path.join(config['output_dir'], "generated", "MathTests.java")
    FileUtils.write_file(test_code, output_path)
    
    return {
        'status': 'success',
        'generated_file': output_path,
        'test_methods': ['testAddition', 'testDivision']
    }

def process_test_cases(agent: TestingAgent, json_path: str) -> Dict:
    """Обработка тест-кейсов из JSON файла"""
    logger.info(f"Загрузка тест-кейсов из: {json_path}")
    
    test_cases = FileUtils.read_json(json_path)
    if not test_cases:
        raise ValueError("Не удалось загрузить тест-кейсы")
    
    results = []
    for case in test_cases:
        logger.info(f"Обработка тест-кейса: {case.get('name')}")
        
        generated = agent.generate_test_with_docs(
            class_desc=case.get('class_description'),
            method_descs=case.get('methods', {})
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{case['name']}.java"
        )
        
        FileUtils.write_file(generated['code'], output_path)
        results.append({
            'test_case': case['name'],
            'file_path': output_path
        })
    
    return {'results': results}

def analyze_java_tests(agent: TestingAgent, java_dir: str) -> Dict:
    """Анализ существующих Java-тестов"""
    logger.info(f"Анализ Java-тестов в директории: {java_dir}")
    
    java_files = list(Path(java_dir).glob('**/*.java'))
    if not java_files:
        raise ValueError("Java-файлы не найдены")
    
    analysis_results = []
    for java_file in java_files:
        metadata = FileUtils.extract_java_metadata(str(java_file))
        analysis_results.append({
            'file': str(java_file),
            'methods': metadata.get('methods', []),
            'class': metadata.get('class_name')
        })
    
    report_path = os.path.join(config['output_dir'], "analysis_report.json")
    FileUtils.write_json(analysis_results, report_path)
    
    return {
        'report_path': report_path,
        'analyzed_files': len(java_files)
    }

def process_openapi_spec(agent: TestingAgent, spec_path: str) -> Dict:
    """Обработка OpenAPI спецификации и генерация тестов"""
    logger.info(f"Обработка OpenAPI спецификации: {spec_path}")
    
    parser = OpenAPIParser(spec_path)
    endpoints = parser.get_endpoints()
    
    results = []
    for endpoint in endpoints:
        test_code = agent.generate_test_with_docs(
            class_desc=f"Тесты для {endpoint['method']} {endpoint['path']}",
            method_descs={
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Success": 
                    f"Проверка успешного сценария для {endpoint['method']} {endpoint['path']}",
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Error":
                    f"Проверка ошибочного сценария для {endpoint['method']} {endpoint['path']}"
            }
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{endpoint['method']}_{endpoint['path'].replace('/', '_')}_Tests.java"
        )
        
        FileUtils.write_file(test_code['code'], output_path)
        results.append({
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'file_path': output_path
        })
    
    return {'results': results}

def main():
    try:
        global config
        config = load_config()
        
        # Создаем необходимые директории
        os.makedirs(os.path.join(config['output_dir'], "generated"), exist_ok=True)
        
        # Инициализация сервисов
        rag, agent = initialize_services(config)
        
        # Пример обработки PDF
        pdf_result = process_pdf_document(
            agent,
            os.path.join(config['input_dir'], "documents/math.pdf")
        )
        logger.info(f"PDF обработка завершена: {pdf_result}")
        
        # Пример обработки JSON тест-кейсов
        json_result = process_test_cases(
            agent,
            os.path.join(config['input_dir'], "test_cases.json")
        )
        logger.info(f"Обработано тест-кейсов: {len(json_result['results'])}")
        
        # Пример анализа Java-файлов
        analysis_result = analyze_java_tests(
            agent,
            os.path.join(config['input_dir'], "java_tests")
        )
        logger.info(f"Сгенерирован отчет: {analysis_result['report_path']}")

        # Пример обработки OpenAPI спецификации
        openapi_result = process_openapi_spec(
            agent,
            os.path.join(config['input_dir'], "api_spec/openapi.yaml")
        )
        logger.info(f"Сгенерировано тестов для API: {len(openapi_result['results'])}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
    return {'results': results}

def analyze_java_tests(agent: TestingAgent, java_dir: str) -> Dict:
    """Анализ существующих Java-тестов"""
    logger.info(f"Анализ Java-тестов в директории: {java_dir}")
    
    java_files = list(Path(java_dir).glob('**/*.java'))
    if not java_files:
        raise ValueError("Java-файлы не найдены")
    
    analysis_results = []
    for java_file in java_files:
        metadata = FileUtils.extract_java_metadata(str(java_file))
        analysis_results.append({
            'file': str(java_file),
            'methods': metadata.get('methods', []),
            'class': metadata.get('class_name')
        })
    
    report_path = os.path.join(config['output_dir'], "analysis_report.json")
    FileUtils.write_json(analysis_results, report_path)
    
    return {
        'report_path': report_path,
        'analyzed_files': len(java_files)
    }

def process_openapi_spec(agent: TestingAgent, spec_path: str) -> Dict:
    """Обработка OpenAPI спецификации и генерация тестов"""
    logger.info(f"Обработка OpenAPI спецификации: {spec_path}")
    
    parser = OpenAPIParser(spec_path)
    endpoints = parser.get_endpoints()
    
    results = []
    for endpoint in endpoints:
        test_code = agent.generate_test_with_docs(
            class_desc=f"Тесты для {endpoint['method']} {endpoint['path']}",
            method_descs={
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Success": 
                    f"Проверка успешного сценария для {endpoint['method']} {endpoint['path']}",
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Error":
                    f"Проверка ошибочного сценария для {endpoint['method']} {endpoint['path']}"
            }
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{endpoint['method']}_{endpoint['path'].replace('/', '_')}_Tests.java"
        )
        
        FileUtils.write_file(test_code['code'], output_path)
        results.append({
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'file_path': output_path
        })
    
    return {'results': results}

def main():
    try:
        global config
        config = load_config()
        
        # Создаем необходимые директории
        os.makedirs(os.path.join(config['output_dir'], "generated"), exist_ok=True)
        
        # Инициализация сервисов
        rag, agent = initialize_services(config)
        
        # Пример обработки PDF
        pdf_result = process_pdf_document(
            agent,
            os.path.join(config['input_dir'], "documents/math.pdf")
        )
        logger.info(f"PDF обработка завершена: {pdf_result}")
        
        # Пример обработки JSON тест-кейсов
        json_result = process_test_cases(
            agent,
            os.path.join(config['input_dir'], "test_cases.json")
        )
        logger.info(f"Обработано тест-кейсов: {len(json_result['results'])}")
        
        # Пример анализа Java-файлов
        analysis_result = analyze_java_tests(
            agent,
            os.path.join(config['input_dir'], "java_tests")
        )
        logger.info(f"Сгенерирован отчет: {analysis_result['report_path']}")

        # Пример обработки OpenAPI спецификации
        openapi_result = process_openapi_spec(
            agent,
            os.path.join(config['input_dir'], "api_spec/openapi.yaml")
        )
        logger.info(f"Сгенерировано тестов для API: {len(openapi_result['results'])}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
    return {'results': results}

def analyze_java_tests(agent: TestingAgent, java_dir: str) -> Dict:
    """Анализ существующих Java-тестов"""
    logger.info(f"Анализ Java-тестов в директории: {java_dir}")
    
    java_files = list(Path(java_dir).glob('**/*.java'))
    if not java_files:
        raise ValueError("Java-файлы не найдены")
    
    analysis_results = []
    for java_file in java_files:
        metadata = FileUtils.extract_java_metadata(str(java_file))
        analysis_results.append({
            'file': str(java_file),
            'methods': metadata.get('methods', []),
            'class': metadata.get('class_name')
        })
    
    report_path = os.path.join(config['output_dir'], "analysis_report.json")
    FileUtils.write_json(analysis_results, report_path)
    
    return {
        'report_path': report_path,
        'analyzed_files': len(java_files)
    }

def process_openapi_spec(agent: TestingAgent, spec_path: str) -> Dict:
    """Обработка OpenAPI спецификации и генерация тестов"""
    logger.info(f"Обработка OpenAPI спецификации: {spec_path}")
    
    parser = OpenAPIParser(spec_path)
    endpoints = parser.get_endpoints()
    
    results = []
    for endpoint in endpoints:
        test_code = agent.generate_test_with_docs(
            class_desc=f"Тесты для {endpoint['method']} {endpoint['path']}",
            method_descs={
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Success": 
                    f"Проверка успешного сценария для {endpoint['method']} {endpoint['path']}",
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Error":
                    f"Проверка ошибочного сценария для {endpoint['method']} {endpoint['path']}"
            }
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{endpoint['method']}_{endpoint['path'].replace('/', '_')}_Tests.java"
        )
        
        FileUtils.write_file(test_code['code'], output_path)
        results.append({
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'file_path': output_path
        })
    
    return {'results': results}

def main():
    try:
        global config
        config = load_config()
        
        # Создаем необходимые директории
        os.makedirs(os.path.join(config['output_dir'], "generated"), exist_ok=True)
        
        # Инициализация сервисов
        rag, agent = initialize_services(config)
        
        # Пример обработки PDF
        pdf_result = process_pdf_document(
            agent,
            os.path.join(config['input_dir'], "documents/math.pdf")
        )
        logger.info(f"PDF обработка завершена: {pdf_result}")
        
        # Пример обработки JSON тест-кейсов
        json_result = process_test_cases(
            agent,
            os.path.join(config['input_dir'], "test_cases.json")
        )
        logger.info(f"Обработано тест-кейсов: {len(json_result['results'])}")
        
        # Пример анализа Java-файлов
        analysis_result = analyze_java_tests(
            agent,
            os.path.join(config['input_dir'], "java_tests")
        )
        logger.info(f"Сгенерирован отчет: {analysis_result['report_path']}")

        # Пример обработки OpenAPI спецификации
        openapi_result = process_openapi_spec(
            agent,
            os.path.join(config['input_dir'], "api_spec/openapi.yaml")
        )
        logger.info(f"Сгенерировано тестов для API: {len(openapi_result['results'])}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
    return {'results': results}

def analyze_java_tests(agent: TestingAgent, java_dir: str) -> Dict:
    """Анализ существующих Java-тестов"""
    logger.info(f"Анализ Java-тестов в директории: {java_dir}")
    
    java_files = list(Path(java_dir).glob('**/*.java'))
    if not java_files:
        raise ValueError("Java-файлы не найдены")
    
    analysis_results = []
    for java_file in java_files:
        metadata = FileUtils.extract_java_metadata(str(java_file))
        analysis_results.append({
            'file': str(java_file),
            'methods': metadata.get('methods', []),
            'class': metadata.get('class_name')
        })
    
    report_path = os.path.join(config['output_dir'], "analysis_report.json")
    FileUtils.write_json(analysis_results, report_path)
    
    return {
        'report_path': report_path,
        'analyzed_files': len(java_files)
    }

def process_openapi_spec(agent: TestingAgent, spec_path: str) -> Dict:
    """Обработка OpenAPI спецификации и генерация тестов"""
    logger.info(f"Обработка OpenAPI спецификации: {spec_path}")
    
    parser = OpenAPIParser(spec_path)
    endpoints = parser.get_endpoints()
    
    results = []
    for endpoint in endpoints:
        test_code = agent.generate_test_with_docs(
            class_desc=f"Тесты для {endpoint['method']} {endpoint['path']}",
            method_descs={
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Success": 
                    f"Проверка успешного сценария для {endpoint['method']} {endpoint['path']}",
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Error":
                    f"Проверка ошибочного сценария для {endpoint['method']} {endpoint['path']}"
            }
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{endpoint['method']}_{endpoint['path'].replace('/', '_')}_Tests.java"
        )
        
        FileUtils.write_file(test_code['code'], output_path)
        results.append({
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'file_path': output_path
        })
    
    return {'results': results}

def main():
    try:
        global config
        config = load_config()
        
        # Создаем необходимые директории
        os.makedirs(os.path.join(config['output_dir'], "generated"), exist_ok=True)
        
        # Инициализация сервисов
        rag, agent = initialize_services(config)
        
        # Пример обработки PDF
        pdf_result = process_pdf_document(
            agent,
            os.path.join(config['input_dir'], "documents/math.pdf")
        )
        logger.info(f"PDF обработка завершена: {pdf_result}")
        
        # Пример обработки JSON тест-кейсов
        json_result = process_test_cases(
            agent,
            os.path.join(config['input_dir'], "test_cases.json")
        )
        logger.info(f"Обработано тест-кейсов: {len(json_result['results'])}")
        
        # Пример анализа Java-файлов
        analysis_result = analyze_java_tests(
            agent,
            os.path.join(config['input_dir'], "java_tests")
        )
        logger.info(f"Сгенерирован отчет: {analysis_result['report_path']}")

        # Пример обработки OpenAPI спецификации
        openapi_result = process_openapi_spec(
            agent,
            os.path.join(config['input_dir'], "api_spec/openapi.yaml")
        )
        logger.info(f"Сгенерировано тестов для API: {len(openapi_result['results'])}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
    return {'results': results}

def analyze_java_tests(agent: TestingAgent, java_dir: str) -> Dict:
    """Анализ существующих Java-тестов"""
    logger.info(f"Анализ Java-тестов в директории: {java_dir}")
    
    java_files = list(Path(java_dir).glob('**/*.java'))
    if not java_files:
        raise ValueError("Java-файлы не найдены")
    
    analysis_results = []
    for java_file in java_files:
        metadata = FileUtils.extract_java_metadata(str(java_file))
        analysis_results.append({
            'file': str(java_file),
            'methods': metadata.get('methods', []),
            'class': metadata.get('class_name')
        })
    
    report_path = os.path.join(config['output_dir'], "analysis_report.json")
    FileUtils.write_json(analysis_results, report_path)
    
    return {
        'report_path': report_path,
        'analyzed_files': len(java_files)
    }

def process_openapi_spec(agent: TestingAgent, spec_path: str) -> Dict:
    """Обработка OpenAPI спецификации и генерация тестов"""
    logger.info(f"Обработка OpenAPI спецификации: {spec_path}")
    
    parser = OpenAPIParser(spec_path)
    endpoints = parser.get_endpoints()
    
    results = []
    for endpoint in endpoints:
        test_code = agent.generate_test_with_docs(
            class_desc=f"Тесты для {endpoint['method']} {endpoint['path']}",
            method_descs={
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Success": 
                    f"Проверка успешного сценария для {endpoint['method']} {endpoint['path']}",
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Error":
                    f"Проверка ошибочного сценария для {endpoint['method']} {endpoint['path']}"
            }
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{endpoint['method']}_{endpoint['path'].replace('/', '_')}_Tests.java"
        )
        
        FileUtils.write_file(test_code['code'], output_path)
        results.append({
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'file_path': output_path
        })
    
    return {'results': results}

def main():
    try:
        global config
        config = load_config()
        
        # Создаем необходимые директории
        os.makedirs(os.path.join(config['output_dir'], "generated"), exist_ok=True)
        
        # Инициализация сервисов
        rag, agent = initialize_services(config)
        
        # Пример обработки PDF
        pdf_result = process_pdf_document(
            agent,
            os.path.join(config['input_dir'], "documents/math.pdf")
        )
        logger.info(f"PDF обработка завершена: {pdf_result}")
        
        # Пример обработки JSON тест-кейсов
        json_result = process_test_cases(
            agent,
            os.path.join(config['input_dir'], "test_cases.json")
        )
        logger.info(f"Обработано тест-кейсов: {len(json_result['results'])}")
        
        # Пример анализа Java-файлов
        analysis_result = analyze_java_tests(
            agent,
            os.path.join(config['input_dir'], "java_tests")
        )
        logger.info(f"Сгенерирован отчет: {analysis_result['report_path']}")

        # Пример обработки OpenAPI спецификации
        openapi_result = process_openapi_spec(
            agent,
            os.path.join(config['input_dir'], "api_spec/openapi.yaml")
        )
        logger.info(f"Сгенерировано тестов для API: {len(openapi_result['results'])}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
    return {'results': results}

def analyze_java_tests(agent: TestingAgent, java_dir: str) -> Dict:
    """Анализ существующих Java-тестов"""
    logger.info(f"Анализ Java-тестов в директории: {java_dir}")
    
    java_files = list(Path(java_dir).glob('**/*.java'))
    if not java_files:
        raise ValueError("Java-файлы не найдены")
    
    analysis_results = []
    for java_file in java_files:
        metadata = FileUtils.extract_java_metadata(str(java_file))
        analysis_results.append({
            'file': str(java_file),
            'methods': metadata.get('methods', []),
            'class': metadata.get('class_name')
        })
    
    report_path = os.path.join(config['output_dir'], "analysis_report.json")
    FileUtils.write_json(analysis_results, report_path)
    
    return {
        'report_path': report_path,
        'analyzed_files': len(java_files)
    }

def process_openapi_spec(agent: TestingAgent, spec_path: str) -> Dict:
    """Обработка OpenAPI спецификации и генерация тестов"""
    logger.info(f"Обработка OpenAPI спецификации: {spec_path}")
    
    parser = OpenAPIParser(spec_path)
    endpoints = parser.get_endpoints()
    
    results = []
    for endpoint in endpoints:
        test_code = agent.generate_test_with_docs(
            class_desc=f"Тесты для {endpoint['method']} {endpoint['path']}",
            method_descs={
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Success": 
                    f"Проверка успешного сценария для {endpoint['method']} {endpoint['path']}",
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Error":
                    f"Проверка ошибочного сценария для {endpoint['method']} {endpoint['path']}"
            }
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{endpoint['method']}_{endpoint['path'].replace('/', '_')}_Tests.java"
        )
        
        FileUtils.write_file(test_code['code'], output_path)
        results.append({
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'file_path': output_path
        })
    
    return {'results': results}

def main():
    try:
        global config
        config = load_config()
        
        # Создаем необходимые директории
        os.makedirs(os.path.join(config['output_dir'], "generated"), exist_ok=True)
        
        # Инициализация сервисов
        rag, agent = initialize_services(config)
        
        # Пример обработки PDF
        pdf_result = process_pdf_document(
            agent,
            os.path.join(config['input_dir'], "documents/math.pdf")
        )
        logger.info(f"PDF обработка завершена: {pdf_result}")
        
        # Пример обработки JSON тест-кейсов
        json_result = process_test_cases(
            agent,
            os.path.join(config['input_dir'], "test_cases.json")
        )
        logger.info(f"Обработано тест-кейсов: {len(json_result['results'])}")
        
        # Пример анализа Java-файлов
        analysis_result = analyze_java_tests(
            agent,
            os.path.join(config['input_dir'], "java_tests")
        )
        logger.info(f"Сгенерирован отчет: {analysis_result['report_path']}")

        # Пример обработки OpenAPI спецификации
        openapi_result = process_openapi_spec(
            agent,
            os.path.join(config['input_dir'], "api_spec/openapi.yaml")
        )
        logger.info(f"Сгенерировано тестов для API: {len(openapi_result['results'])}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
    return {'results': results}

def analyze_java_tests(agent: TestingAgent, java_dir: str) -> Dict:
    """Анализ существующих Java-тестов"""
    logger.info(f"Анализ Java-тестов в директории: {java_dir}")
    
    java_files = list(Path(java_dir).glob('**/*.java'))
    if not java_files:
        raise ValueError("Java-файлы не найдены")
    
    analysis_results = []
    for java_file in java_files:
        metadata = FileUtils.extract_java_metadata(str(java_file))
        analysis_results.append({
            'file': str(java_file),
            'methods': metadata.get('methods', []),
            'class': metadata.get('class_name')
        })
    
    report_path = os.path.join(config['output_dir'], "analysis_report.json")
    FileUtils.write_json(analysis_results, report_path)
    
    return {
        'report_path': report_path,
        'analyzed_files': len(java_files)
    }

def process_openapi_spec(agent: TestingAgent, spec_path: str) -> Dict:
    """Обработка OpenAPI спецификации и генерация тестов"""
    logger.info(f"Обработка OpenAPI спецификации: {spec_path}")
    
    parser = OpenAPIParser(spec_path)
    endpoints = parser.get_endpoints()
    
    results = []
    for endpoint in endpoints:
        test_code = agent.generate_test_with_docs(
            class_desc=f"Тесты для {endpoint['method']} {endpoint['path']}",
            method_descs={
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Success": 
                    f"Проверка успешного сценария для {endpoint['method']} {endpoint['path']}",
                f"test{endpoint['method']}{endpoint['path'].replace('/', '_')}Error":
                    f"Проверка ошибочного сценария для {endpoint['method']} {endpoint['path']}"
            }
        )
        
        output_path = os.path.join(
            config['output_dir'],
            "generated",
            f"{endpoint['method']}_{endpoint['path'].replace('/', '_')}_Tests.java"
        )
        
        FileUtils.write_file(test_code['code'], output_path)
        results.append({
            'endpoint': f"{endpoint['method']} {endpoint['path']}",
            'file_path': output_path
        })
    
    return {'results': results}

def main():
    try:
        global config
        config = load_config()
        
        # Создаем необходимые директории
        os.makedirs(os.path.join(config['output_dir'], "generated"), exist_ok=True)
        
        # Инициализация сервисов
        rag, agent = initialize_services(config)
        
        # Пример обработки PDF
        pdf_result = process_pdf_document(
            agent,
            os.path.join(config['input_dir'], "documents/math.pdf")
        )
        logger.info(f"PDF обработка завершена: {pdf_result}")
        
        # Пример обработки JSON тест-кейсов
        json_result = process_test_cases(
            agent,
            os.path.join(config['input_dir'], "test_cases.json")
        )
        logger.info(f"Обработано тест-кейсов: {len(json_result['results'])}")
        
        # Пример анализа Java-файлов
        analysis_result = analyze_java_tests(
            agent,
            os.path.join(config['input_dir'], "java_tests")
        )
        logger.info(f"Сгенерирован отчет: {analysis_result['report_path']}")

        # Пример обработки OpenAPI спецификации
        openapi_result = process_openapi_spec(
            agent,
            os.path.join(config['input_dir'], "api_spec/openapi.yaml")
        )
        logger.info(f"Сгенерировано тестов для API: {len(openapi_result['results'])}")
        
    except Exception as e:
        logger.error(f"Ошибка выполнения: {str(e)}", exc_info=True)
        exit(1)

if __name__ == "__main__":
    main()
