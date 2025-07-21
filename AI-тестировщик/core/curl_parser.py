import re
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs
import json

class CurlParser:
    @staticmethod
    def parse_curl(curl_command: str) -> Dict:
        """
        Разбор cURL команды на составляющие
        
        :param curl_command: Строка с cURL командой
        :return: Словарь с разобранными компонентами
        """
        result = {
            'method': 'GET',
            'url': '',
            'headers': {},
            'data': None,
            'params': {},
            'valid': False
        }

        try:
            # Извлечение метода
            method_match = re.search(r'-X\s+(\w+)', curl_command)
            if method_match:
                result['method'] = method_match.group(1).upper()

            # Извлечение URL
            url_match = re.search(r"curl\s+['\"]([^'\"]+)['\"]", curl_command) or \
                       re.search(r'curl\s+([^\s]+)', curl_command)
            if url_match:
                result['url'] = url_match.group(1)
                # Парсинг query параметров
                parsed = urlparse(result['url'])
                result['params'] = parse_qs(parsed.query)
            else:
                raise ValueError("URL not found in cURL command")

            # Извлечение заголовков
            headers = re.findall(r"-H\s+['\"]([^'\"]+)['\"]", curl_command)
            for header in headers:
                key, value = header.split(':', 1)
                result['headers'][key.strip()] = value.strip()

            # Извлечение тела запроса
            data_match = re.search(r"--data-raw\s+['\"]([^'\"]+)['\"]", curl_command) or \
                        re.search(r"-d\s+['\"]([^'\"]+)['\"]", curl_command)
            if data_match:
                try:
                    result['data'] = json.loads(data_match.group(1))
                except json.JSONDecodeError:
                    result['data'] = data_match.group(1)

            result['valid'] = True
            return result

        except Exception as e:
            result['error'] = str(e)
            return result

    @staticmethod
    def generate_test_description(curl_data: Dict) -> str:
        """
        Генерация описания теста на основе разобранного cURL
        
        :param curl_data: Результат работы parse_curl
        :return: Текстовое описание для генерации теста
        """
        if not curl_data.get('valid'):
            raise ValueError("Invalid cURL data")
            
        desc = f"API тест для {curl_data['method']} запроса\n"
        desc += f"URL: {curl_data['url']}\n"
        
        if curl_data['headers']:
            desc += "Заголовки:\n"
            for k, v in curl_data['headers'].items():
                desc += f"- {k}: {v}\n"
                
        if curl_data['data']:
            desc += "Тело запроса:\n"
            desc += json.dumps(curl_data['data'], indent=2) + "\n"
            
        if curl_data['params']:
            desc += "Query параметры:\n"
            for k, v in curl_data['params'].items():
                desc += f"- {k}: {', '.join(v)}\n"
                
        return desc
