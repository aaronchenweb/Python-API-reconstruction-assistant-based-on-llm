"""
OpenAPI 分析器 - 分析和生成 OpenAPI 規範
"""
import ast
import os
import re
import json
from typing import Dict, List, Set, Tuple, Optional, Any

from utils.file_operations import read_file, write_file
from .endpoint_analyzer import EndpointAnalyzer
from .schema_extractor import SchemaExtractor


class OpenAPIAnalyzer:
    """分析和生成 OpenAPI 規範"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化 OpenAPI 分析器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.openapi_spec = None
        self.existing_spec = None
        
    def find_existing_spec(self) -> Optional[Dict[str, Any]]:
        """
        尋找專案中現有的 OpenAPI 規範
        
        Returns:
            如果找到則返回 OpenAPI 規範，否則返回 None
        """
        # 尋找常見的 OpenAPI 規範檔案
        spec_files = ['openapi.json', 'swagger.json', 'api-docs.json', 'openapi.yaml', 'swagger.yaml']
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.lower() in spec_files:
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    try:
                        if file.endswith('.json'):
                            spec = json.loads(content)
                            # 簡單驗證是否是 OpenAPI 規範
                            if 'openapi' in spec or 'swagger' in spec:
                                self.existing_spec = spec
                                return spec
                        elif file.endswith('.yaml') or file.endswith('.yml'):
                            try:
                                import yaml
                                spec = yaml.safe_load(content)
                                # 簡單驗證是否是 OpenAPI 規範
                                if 'openapi' in spec or 'swagger' in spec:
                                    self.existing_spec = spec
                                    return spec
                            except ImportError:
                                # 如果 yaml 模塊不可用，則嘗試使用簡單的正則表達式
                                if re.search(r'openapi:|swagger:', content):
                                    # 返回未解析的內容
                                    return {'raw_content': content, 'format': 'yaml'}
                    except Exception:
                        continue
        
        return None
    
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """
        從專案中生成 OpenAPI 規範
        
        Returns:
            OpenAPI 規範字典
        """
        # 檢查是否已有現有的規範
        if self.existing_spec:
            return self.existing_spec
        
        # 如果框架未知，先檢測
        if not self.framework:
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
        
        # 初始化基本 OpenAPI 結構
        openapi_spec = {
            'openapi': '3.0.0',
            'info': {
                'title': os.path.basename(self.project_path) + ' API',
                'version': '1.0.0',
                'description': 'API documentation generated by Python API Reconstruction Assistant'
            },
            'paths': {},
            'components': {
                'schemas': {}
            }
        }
        
        # 分析端點
        endpoint_analyzer = EndpointAnalyzer(self.project_path)
        endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 分析數據模型
        schema_extractor = SchemaExtractor(self.project_path, self.framework)
        models = schema_extractor.extract_models()
        
        # 根據框架選擇適當的處理方法
        if self.framework == 'fastapi':
            # FastAPI 通常已有內建的 OpenAPI 支援
            self._process_fastapi_endpoints(endpoints, openapi_spec)
        elif self.framework == 'django':
            self._process_django_endpoints(endpoints, models, openapi_spec)
        elif self.framework == 'flask':
            self._process_flask_endpoints(endpoints, models, openapi_spec)
        
        # 處理模型/結構
        self._process_models(models, openapi_spec)
        
        self.openapi_spec = openapi_spec
        return openapi_spec
    
    def _process_fastapi_endpoints(self, endpoints: List[Dict[str, Any]], openapi_spec: Dict[str, Any]) -> None:
        """
        處理 FastAPI 端點以生成 OpenAPI 路徑
        
        Args:
            endpoints: 端點列表
            openapi_spec: OpenAPI 規範字典
        """
        for endpoint in endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET').lower()
            view_name = endpoint.get('view', '')
            file_path = endpoint.get('file', '')
            
            if not path:
                continue
            
            # 確保路徑以斜槓開頭
            if not path.startswith('/'):
                path = '/' + path
            
            # 初始化路徑條目
            if path not in openapi_spec['paths']:
                openapi_spec['paths'][path] = {}
            
            # 檢查是否有 Pydantic 模型
            response_model = endpoint.get('response_model', None)
            
            # 獲取函數文檔字符串
            docstring = self._get_function_docstring(file_path, view_name)
            
            # 建立操作對象
            operation = {
                'operationId': view_name,
                'summary': self._extract_summary_from_docstring(docstring),
                'description': docstring
            }
            
            # 如果有回應模型，則添加到回應
            if response_model:
                operation['responses'] = {
                    '200': {
                        'description': 'Successful response',
                        'content': {
                            'application/json': {
                                'schema': {
                                    '$ref': f'#/components/schemas/{response_model}'
                                }
                            }
                        }
                    }
                }
            else:
                operation['responses'] = {
                    '200': {
                        'description': 'Successful response'
                    }
                }
            
            # 添加操作到路徑
            openapi_spec['paths'][path][method] = operation
    
    def _process_django_endpoints(self, endpoints: List[Dict[str, Any]], models: List[Dict[str, Any]], openapi_spec: Dict[str, Any]) -> None:
        """
        處理 Django 端點以生成 OpenAPI 路徑
        
        Args:
            endpoints: 端點列表
            models: 模型列表
            openapi_spec: OpenAPI 規範字典
        """
        for endpoint in endpoints:
            path = endpoint.get('path', '')
            view_name = endpoint.get('view', '')
            file_path = endpoint.get('file', '')
            
            if not path:
                continue
            
            # 將 Django 路徑格式轉換為 OpenAPI 路徑格式
            # 例如，將 'users/<int:user_id>/' 轉換為 '/users/{user_id}'
            openapi_path = re.sub(r'<int:([^>]+)>', r'{\1}', path)
            openapi_path = re.sub(r'<str:([^>]+)>', r'{\1}', openapi_path)
            openapi_path = re.sub(r'<uuid:([^>]+)>', r'{\1}', openapi_path)
            openapi_path = re.sub(r'<([^>]+)>', r'{\1}', openapi_path)
            
            # 確保路徑以斜槓開頭且不以斜槓結尾
            if not openapi_path.startswith('/'):
                openapi_path = '/' + openapi_path
            if openapi_path.endswith('/') and len(openapi_path) > 1:
                openapi_path = openapi_path[:-1]
            
            # 初始化路徑條目
            if openapi_path not in openapi_spec['paths']:
                openapi_spec['paths'][openapi_path] = {}
            
            # 獲取視圖文檔字符串
            docstring = self._get_function_or_class_docstring(file_path, view_name)
            
            # 確定 HTTP 方法
            # 對於 Django，我們需要檢查視圖類型
            if '.' in view_name:
                # 可能是基於類的視圖，如 MyView.as_view()
                class_name = view_name.split('.')[0]
                view_detail = self._get_class_detail(file_path, class_name)
                
                if view_detail:
                    # 檢查視圖類中的方法
                    http_methods = []
                    for method in ['get', 'post', 'put', 'patch', 'delete']:
                        if method in view_detail.get('methods', []):
                            http_methods.append(method)
                    
                    if not http_methods:
                        http_methods = ['get']  # 默認至少支援 GET
                    
                    for method in http_methods:
                        # 建立操作對象
                        operation = {
                            'operationId': f"{class_name}_{method}",
                            'summary': self._extract_summary_from_docstring(docstring),
                            'description': docstring,
                            'responses': {
                                '200': {
                                    'description': 'Successful response'
                                }
                            }
                        }
                        
                        # 提取參數
                        operation['parameters'] = self._extract_path_parameters(openapi_path)
                        
                        # 添加操作到路徑
                        openapi_spec['paths'][openapi_path][method] = operation
            else:
                # 函數視圖，默認支援 GET
                operation = {
                    'operationId': view_name,
                    'summary': self._extract_summary_from_docstring(docstring),
                    'description': docstring,
                    'responses': {
                        '200': {
                            'description': 'Successful response'
                        }
                    }
                }
                
                # 提取參數
                operation['parameters'] = self._extract_path_parameters(openapi_path)
                
                # 添加操作到路徑
                openapi_spec['paths'][openapi_path]['get'] = operation
    
    def _process_flask_endpoints(self, endpoints: List[Dict[str, Any]], models: List[Dict[str, Any]], openapi_spec: Dict[str, Any]) -> None:
        """
        處理 Flask 端點以生成 OpenAPI 路徑
        
        Args:
            endpoints: 端點列表
            models: 模型列表
            openapi_spec: OpenAPI 規範字典
        """
        for endpoint in endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET').lower()
            view_name = endpoint.get('view', '')
            file_path = endpoint.get('file', '')
            
            if not path:
                continue
            
            # 將 Flask 路徑格式轉換為 OpenAPI 路徑格式
            # 例如，將 '/users/<user_id>' 轉換為 '/users/{user_id}'
            openapi_path = re.sub(r'<([^>]+)>', r'{\1}', path)
            
            # 處理類型指定，例如 '<int:user_id>' -> '{user_id}'
            openapi_path = re.sub(r'<int:([^>]+)>', r'{\1}', openapi_path)
            openapi_path = re.sub(r'<string:([^>]+)>', r'{\1}', openapi_path)
            openapi_path = re.sub(r'<float:([^>]+)>', r'{\1}', openapi_path)
            
            # 確保路徑以斜槓開頭
            if not openapi_path.startswith('/'):
                openapi_path = '/' + openapi_path
            
            # 初始化路徑條目
            if openapi_path not in openapi_spec['paths']:
                openapi_spec['paths'][openapi_path] = {}
            
            # 獲取函數文檔字符串
            docstring = self._get_function_docstring(file_path, view_name)
            
            # 建立操作對象
            operation = {
                'operationId': view_name,
                'summary': self._extract_summary_from_docstring(docstring),
                'description': docstring,
                'responses': {
                    '200': {
                        'description': 'Successful response'
                    }
                }
            }
            
            # 提取參數
            operation['parameters'] = self._extract_path_parameters(openapi_path)
            
            # 添加操作到路徑
            openapi_spec['paths'][openapi_path][method] = operation
    
    def _process_models(self, models: List[Dict[str, Any]], openapi_spec: Dict[str, Any]) -> None:
        """
        處理數據模型以生成 OpenAPI 結構
        
        Args:
            models: 模型列表
            openapi_spec: OpenAPI 規範字典
        """
        for model in models:
            model_name = model.get('name', '')
            model_type = model.get('type', '')
            fields = model.get('fields', [])
            
            if not model_name or not fields:
                continue
            
            # 創建結構對象
            schema = {
                'type': 'object',
                'properties': {}
            }
            
            # 必需屬性列表
            required = []
            
            # 處理欄位
            for field in fields:
                field_name = field.get('name', '')
                field_type = field.get('type', '')
                
                if not field_name:
                    continue
                
                # 映射欄位類型到 OpenAPI 類型
                openapi_type = 'string'  # 默認類型
                
                if field_type:
                    openapi_type = self._map_field_type_to_openapi(field_type)
                
                # 添加屬性
                schema['properties'][field_name] = {
                    'type': openapi_type
                }
                
                # 檢查是否為必需欄位
                if model_type == 'django.model' and any(arg.get('name') == 'null' and arg.get('value') is False for arg in field.get('args', [])):
                    required.append(field_name)
                elif model_type == 'pydantic.model' and field.get('default') is None:
                    required.append(field_name)
            
            # 如果有必需屬性，則添加到結構中
            if required:
                schema['required'] = required
            
            # 添加結構到組件
            openapi_spec['components']['schemas'][model_name] = schema
    
    def _map_field_type_to_openapi(self, field_type: str) -> str:
        """
        將欄位類型映射到 OpenAPI 類型
        
        Args:
            field_type: 欄位類型
            
        Returns:
            OpenAPI 類型
        """
        # Django 欄位類型映射
        django_type_map = {
            'CharField': 'string',
            'TextField': 'string',
            'EmailField': 'string',
            'URLField': 'string',
            'SlugField': 'string',
            'IntegerField': 'integer',
            'PositiveIntegerField': 'integer',
            'BigIntegerField': 'integer',
            'FloatField': 'number',
            'DecimalField': 'number',
            'BooleanField': 'boolean',
            'NullBooleanField': 'boolean',
            'DateField': 'string',
            'DateTimeField': 'string',
            'TimeField': 'string',
            'FileField': 'string',
            'ImageField': 'string',
            'JSONField': 'object',
            'UUIDField': 'string'
        }
        
        # SQLAlchemy 欄位類型映射
        sqlalchemy_type_map = {
            'String': 'string',
            'Integer': 'integer',
            'BigInteger': 'integer',
            'Float': 'number',
            'Numeric': 'number',
            'Boolean': 'boolean',
            'Date': 'string',
            'DateTime': 'string',
            'Time': 'string',
            'JSON': 'object',
            'LargeBinary': 'string'
        }
        
        # Python/Pydantic 類型映射
        python_type_map = {
            'str': 'string',
            'int': 'integer',
            'float': 'number',
            'bool': 'boolean',
            'dict': 'object',
            'list': 'array',
            'tuple': 'array',
            'set': 'array',
            'bytes': 'string',
            'datetime': 'string',
            'date': 'string',
            'time': 'string',
            'uuid': 'string'
        }
        
        # 檢查類型映射
        if field_type in django_type_map:
            return django_type_map[field_type]
        elif field_type in sqlalchemy_type_map:
            return sqlalchemy_type_map[field_type]
        elif field_type in python_type_map:
            return python_type_map[field_type]
        
        # 處理可能的泛型類型
        if field_type.startswith('List[') or field_type.startswith('list['):
            return 'array'
        elif field_type.startswith('Dict[') or field_type.startswith('dict['):
            return 'object'
        
        # 默認返回字符串類型
        return 'string'
    
    def _get_function_docstring(self, file_path: str, function_name: str) -> str:
        """
        從文件中獲取函數的文檔字符串
        
        Args:
            file_path: 文件路徑
            function_name: 函數名
            
        Returns:
            函數的文檔字符串
        """
        try:
            content = read_file(file_path)
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    return ast.get_docstring(node) or ""
        except Exception:
            pass
        
        return ""
    
    def _get_function_or_class_docstring(self, file_path: str, name: str) -> str:
        """
        從文件中獲取函數或類的文檔字符串
        
        Args:
            file_path: 文件路徑
            name: 函數或類名
            
        Returns:
            函數或類的文檔字符串
        """
        try:
            content = read_file(file_path)
            tree = ast.parse(content)
            
            # 處理類方法情況，如 'MyClass.my_method'
            if '.' in name:
                class_name, method_name = name.split('.', 1)
                
                # 如果有括號，如 'as_view()'，則移除
                if '(' in method_name:
                    method_name = method_name.split('(')[0]
                
                # 尋找類
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == class_name:
                        # 尋找方法
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef) and item.name == method_name:
                                return ast.get_docstring(item) or ast.get_docstring(node) or ""
                        
                        # 如果沒有找到特定方法，則返回類文檔
                        return ast.get_docstring(node) or ""
            else:
                # 尋找函數或類
                for node in ast.walk(tree):
                    if (isinstance(node, ast.FunctionDef) and node.name == name) or \
                       (isinstance(node, ast.ClassDef) and node.name == name):
                        return ast.get_docstring(node) or ""
        except Exception:
            pass
        
        return ""
    
    def _get_class_detail(self, file_path: str, class_name: str) -> Optional[Dict[str, Any]]:
        """
        從文件中獲取類的詳細信息
        
        Args:
            file_path: 文件路徑
            class_name: 類名
            
        Returns:
            包含類詳細信息的字典，如果未找到則為 None
        """
        try:
            content = read_file(file_path)
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # 收集類方法
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                    
                    return {
                        'name': class_name,
                        'methods': methods,
                        'docstring': ast.get_docstring(node) or ""
                    }
        except Exception:
            pass
        
        return None
    
    def _extract_path_parameters(self, path: str) -> List[Dict[str, Any]]:
        """
        從路徑中提取參數
        
        Args:
            path: API 路徑
            
        Returns:
            參數列表
        """
        parameters = []
        
        # 使用正則表達式尋找路徑參數
        path_params = re.findall(r'\{([^}]+)\}', path)
        
        for param in path_params:
            parameters.append({
                'name': param,
                'in': 'path',
                'required': True,
                'schema': {
                    'type': 'string'
                }
            })
        
        return parameters
    
    def _extract_summary_from_docstring(self, docstring: str) -> str:
        """
        從文檔字符串中提取摘要
        
        Args:
            docstring: 文檔字符串
            
        Returns:
            摘要
        """
        if not docstring:
            return ""
        
        # 獲取第一行作為摘要
        lines = docstring.strip().split('\n')
        return lines[0].strip()
    
    def save_openapi_spec(self, output_path: Optional[str] = None) -> str:
        """
        保存 OpenAPI 規範到文件
        
        Args:
            output_path: 輸出文件路徑，如果為 None，則使用預設路徑
            
        Returns:
            保存的文件路徑
        """
        if not self.openapi_spec:
            self.generate_openapi_spec()
        
        if not output_path:
            output_path = os.path.join(self.project_path, 'openapi.json')
        
        # 寫入 JSON 文件
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.openapi_spec, f, indent=2)
        
        return output_path