from typing import Dict, List
import yaml
import json

class OpenAPIParser:
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self.spec = self._load_spec()

    def _load_spec(self) -> Dict:
        with open(self.spec_path, 'r') as f:
            if self.spec_path.endswith('.yaml') or self.spec_path.endswith('.yml'):
                return yaml.safe_load(f)
            elif self.spec_path.endswith('.json'):
                return json.load(f)
            else:
                raise ValueError("Unsupported file format")

    def get_endpoints(self) -> List[Dict]:
        endpoints = []
        for path, methods in self.spec.get('paths', {}).items():
            for method, details in methods.items():
                endpoints.append({
                    'path': path,
                    'method': method.upper(),
                    'parameters': details.get('parameters', []),
                    'responses': details.get('responses', {})
                })
        return endpoints

    def get_schemas(self) -> Dict:
        return self.spec.get('components', {}).get('schemas', {})
