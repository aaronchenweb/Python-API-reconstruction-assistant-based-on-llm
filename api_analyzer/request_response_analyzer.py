"""
請求/回應分析器 - 分析 API 請求和回應的處理方式
"""
import ast
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any

from utils.file_operations import read_file
from .endpoint_analyzer import EndpointAnalyzer


class RequestResponseAnalyzer:
    """分析 API 請求和回應的處理方式"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化請求/回應分析器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.endpoints = []
        self.request_handlers = []
        self.response_handlers = []
        
    def analyze_request_handling(self) -> List[Dict[str, Any]]:
        """
        分析專案中的請求處理模式
        
        Returns:
            請求處理信息列表
        """
        if not self.framework:
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
            self.endpoints = endpoint_analyzer.analyze_endpoints()
        elif not self.endpoints:
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 根據框架選擇適當的分析方法
        if self.framework == 'django':
            self._analyze_django_requests()
        elif self.framework == 'flask':
            self._analyze_flask_requests()
        elif self.framework == 'fastapi':
            self._analyze_fastapi_requests()
        
        return self.request_handlers
    
    def analyze_response_handling(self) -> List[Dict[str, Any]]:
        """
        分析專案中的回應處理模式
        
        Returns:
            回應處理信息列表
        """
        if not self.framework:
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
            self.endpoints = endpoint_analyzer.analyze_endpoints()
        elif not self.endpoints:
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 根據框架選擇適當的分析方法
        if self.framework == 'django':
            self._analyze_django_responses()
        elif self.framework == 'flask':
            self._analyze_flask_responses()
        elif self.framework == 'fastapi':
            self._analyze_fastapi_responses()
        
        return self.response_handlers
    
    def _analyze_django_requests(self) -> None:
        """分析 Django 請求處理"""
        for endpoint in self.endpoints:
            file_path = endpoint.get('file', '')
            view_name = endpoint.get('view', '')
            
            if not file_path or not view_name:
                continue
            
            try:
                content = read_file(file_path)
                tree = ast.parse(content)
                
                # 尋找視圖函數或類
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == view_name:
                        # 分析函數參數
                        request_param = None
                        for arg in node.args.args:
                            if arg.arg == 'request':
                                request_param = 'request'
                            
                        # 尋找請求處理代碼
                        request_access_methods = []
                        
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Attribute) and isinstance(subnode.value, ast.Name):
                                if subnode.value.id == request_param:
                                    request_access_methods.append(subnode.attr)
                        
                        # 如果找到請求處理
                        if request_access_methods:
                            self.request_handlers.append({
                                'endpoint': endpoint.get('path', ''),
                                'view': view_name,
                                'file': file_path,
                                'line': node.lineno,
                                'type': 'function_view',
                                'methods': list(set(request_access_methods)),
                                'framework': 'django'
                            })
                    
                    elif isinstance(node, ast.ClassDef):
                        # 檢查是否是視圖類
                        for method in node.body:
                            if isinstance(method, ast.FunctionDef) and method.name in ['get', 'post', 'put', 'delete', 'patch']:
                                # 分析方法參數
                                request_param = None
                                for arg in method.args.args:
                                    if arg.arg == 'request':
                                        request_param = 'request'
                                    elif arg.arg == 'self':
                                        continue
                                
                                # 尋找請求處理代碼
                                request_access_methods = []
                                
                                for subnode in ast.walk(method):
                                    if isinstance(subnode, ast.Attribute) and isinstance(subnode.value, ast.Name):
                                        if subnode.value.id == request_param:
                                            request_access_methods.append(subnode.attr)
                                
                                # 如果找到請求處理
                                if request_access_methods:
                                    self.request_handlers.append({
                                        'endpoint': endpoint.get('path', ''),
                                        'view': f"{node.name}.{method.name}",
                                        'file': file_path,
                                        'line': method.lineno,
                                        'type': 'class_view',
                                        'methods': list(set(request_access_methods)),
                                        'http_method': method.name.upper(),
                                        'framework': 'django'
                                    })
            except Exception:
                continue
    
    def _analyze_django_responses(self) -> None:
        """分析 Django 回應處理"""
        # 搜尋 Django 回應類型
        response_types = [
            'HttpResponse', 'JsonResponse', 'HttpResponseRedirect', 
            'HttpResponsePermanentRedirect', 'HttpResponseBadRequest', 
            'HttpResponseForbidden', 'HttpResponseNotFound', 
            'HttpResponseNotAllowed', 'HttpResponseServerError',
            'render', 'redirect'
        ]
        
        for endpoint in self.endpoints:
            file_path = endpoint.get('file', '')
            view_name = endpoint.get('view', '')
            
            if not file_path or not view_name:
                continue
            
            try:
                content = read_file(file_path)
                
                # 檢查引入
                imports_responses = any(f"import {resp}" in content or f"from django.http import {resp}" in content for resp in response_types)
                
                if not imports_responses:
                    continue
                
                tree = ast.parse(content)
                
                # 分析視圖函數或方法
                for node in ast.walk(tree):
                    # 函數視圖
                    if isinstance(node, ast.FunctionDef) and node.name == view_name:
                        # 尋找回應創建
                        responses = self._find_django_responses(node, response_types)
                        
                        if responses:
                            self.response_handlers.append({
                                'endpoint': endpoint.get('path', ''),
                                'view': view_name,
                                'file': file_path,
                                'line': node.lineno,
                                'type': 'function_view',
                                'responses': responses,
                                'framework': 'django'
                            })
                    
                    # 基於類的視圖
                    elif isinstance(node, ast.ClassDef):
                        # 檢查視圖方法
                        for method in node.body:
                            if isinstance(method, ast.FunctionDef) and method.name in ['get', 'post', 'put', 'delete', 'patch']:
                                # 尋找回應創建
                                responses = self._find_django_responses(method, response_types)
                                
                                if responses:
                                    self.response_handlers.append({
                                        'endpoint': endpoint.get('path', ''),
                                        'view': f"{node.name}.{method.name}",
                                        'file': file_path,
                                        'line': method.lineno,
                                        'type': 'class_view',
                                        'http_method': method.name.upper(),
                                        'responses': responses,
                                        'framework': 'django'
                                    })
            except Exception:
                continue
    
    def _find_django_responses(self, node: ast.AST, response_types: List[str]) -> List[Dict[str, Any]]:
        """
        在 AST 節點中尋找 Django 回應
        
        Args:
            node: 要搜尋的 AST 節點
            response_types: 回應類型列表
            
        Returns:
            找到的回應列表
        """
        responses = []
        
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Call):
                response_type = None
                
                # 直接函數調用
                if isinstance(subnode.func, ast.Name) and subnode.func.id in response_types:
                    response_type = subnode.func.id
                # 導入的屬性
                elif isinstance(subnode.func, ast.Attribute) and subnode.func.attr in response_types:
                    response_type = subnode.func.attr
                
                if response_type:
                    # 檢查響應內容
                    content_type = None
                    status_code = None
                    
                    # 檢查關鍵字參數
                    for keyword in subnode.keywords:
                        if keyword.arg == 'content_type' and isinstance(keyword.value, ast.Constant):
                            content_type = keyword.value.value
                        elif keyword.arg == 'status' and isinstance(keyword.value, ast.Constant):
                            status_code = keyword.value.value
                    
                    responses.append({
                        'type': response_type,
                        'content_type': content_type,
                        'status_code': status_code,
                        'line': subnode.lineno
                    })
        
        return responses
    
    def _analyze_flask_requests(self) -> None:
        """分析 Flask 請求處理"""
        for endpoint in self.endpoints:
            file_path = endpoint.get('file', '')
            view_name = endpoint.get('view', '')
            
            if not file_path or not view_name:
                continue
            
            try:
                content = read_file(file_path)
                
                # 檢查是否使用了 request 對象
                if 'request.' not in content and 'request,' not in content:
                    continue
                
                tree = ast.parse(content)
                
                # 尋找視圖函數
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == view_name:
                        # 尋找請求處理代碼
                        request_access_methods = []
                        
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Attribute) and isinstance(subnode.value, ast.Name):
                                if subnode.value.id == 'request':
                                    request_access_methods.append(subnode.attr)
                        
                        # 如果找到請求處理
                        if request_access_methods:
                            self.request_handlers.append({
                                'endpoint': endpoint.get('path', ''),
                                'view': view_name,
                                'file': file_path,
                                'line': node.lineno,
                                'type': 'flask_view',
                                'methods': list(set(request_access_methods)),
                                'framework': 'flask'
                            })
            except Exception:
                continue
    
    def _analyze_flask_responses(self) -> None:
        """分析 Flask 回應處理"""
        # 搜尋 Flask 回應類型
        response_types = [
            'jsonify', 'render_template', 'make_response', 
            'redirect', 'send_file', 'Response'
        ]
        
        for endpoint in self.endpoints:
            file_path = endpoint.get('file', '')
            view_name = endpoint.get('view', '')
            
            if not file_path or not view_name:
                continue
            
            try:
                content = read_file(file_path)
                
                # 檢查是否可能有響應
                if not any(resp in content for resp in response_types):
                    continue
                
                tree = ast.parse(content)
                
                # 尋找視圖函數
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == view_name:
                        # 尋找回應創建
                        responses = []
                        
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Call):
                                response_type = None
                                
                                # 直接函數調用
                                if isinstance(subnode.func, ast.Name) and subnode.func.id in response_types:
                                    response_type = subnode.func.id
                                # 導入的屬性
                                elif isinstance(subnode.func, ast.Attribute) and subnode.func.attr in response_types:
                                    response_type = subnode.func.attr
                                
                                if response_type:
                                    # 檢查狀態碼
                                    status_code = None
                                    
                                    # 檢查關鍵字參數
                                    for keyword in subnode.keywords:
                                        if keyword.arg in ['status_code', 'code'] and isinstance(keyword.value, ast.Constant):
                                            status_code = keyword.value.value
                                    
                                    responses.append({
                                        'type': response_type,
                                        'status_code': status_code,
                                        'line': subnode.lineno
                                    })
                        
                        if responses:
                            self.response_handlers.append({
                                'endpoint': endpoint.get('path', ''),
                                'view': view_name,
                                'file': file_path,
                                'line': node.lineno,
                                'type': 'flask_view',
                                'responses': responses,
                                'framework': 'flask'
                            })
            except Exception:
                continue
    
    def _analyze_fastapi_requests(self) -> None:
        """分析 FastAPI 請求處理"""
        for endpoint in self.endpoints:
            file_path = endpoint.get('file', '')
            view_name = endpoint.get('view', '')
            
            if not file_path or not view_name:
                continue
            
            try:
                content = read_file(file_path)
                tree = ast.parse(content)
                
                # 尋找端點函數
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == view_name:
                        # 分析參數
                        param_types = []
                        
                        for arg in node.args.args:
                            arg_name = arg.arg
                            arg_type = None
                            
                            # 嘗試獲取類型註解
                            if arg.annotation:
                                if isinstance(arg.annotation, ast.Name):
                                    arg_type = arg.annotation.id
                                elif isinstance(arg.annotation, ast.Attribute):
                                    if isinstance(arg.annotation.value, ast.Name):
                                        arg_type = f"{arg.annotation.value.id}.{arg.annotation.attr}"
                            
                            param_types.append({
                                'name': arg_name,
                                'type': arg_type
                            })
                        
                        # 檢查是否有依賴項參數（請求體、查詢參數等）
                        pydantic_models = []
                        query_params = []
                        path_params = []
                        body_params = []
                        
                        for param in param_types:
                            if param['type']:
                                if 'Query' in param['type']:
                                    query_params.append(param['name'])
                                elif 'Path' in param['type']:
                                    path_params.append(param['name'])
                                elif 'Body' in param['type']:
                                    body_params.append(param['name'])
                                elif param['type'] not in ['str', 'int', 'float', 'bool', 'dict', 'list']:
                                    # 可能是 Pydantic 模型
                                    pydantic_models.append(param['name'])
                        
                        self.request_handlers.append({
                            'endpoint': endpoint.get('path', ''),
                            'view': view_name,
                            'file': file_path,
                            'line': node.lineno,
                            'type': 'fastapi_endpoint',
                            'params': param_types,
                            'query_params': query_params,
                            'path_params': path_params,
                            'body_params': body_params,
                            'pydantic_models': pydantic_models,
                            'framework': 'fastapi'
                        })
            except Exception:
                continue
    
    def _analyze_fastapi_responses(self) -> None:
        """分析 FastAPI 回應處理"""
        for endpoint in self.endpoints:
            file_path = endpoint.get('file', '')
            view_name = endpoint.get('view', '')
            
            if not file_path or not view_name:
                continue
            
            try:
                content = read_file(file_path)
                tree = ast.parse(content)
                
                # 尋找端點函數
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == view_name:
                        # 檢查回應模型
                        response_model = None
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                                # 尋找 response_model 參數
                                for keyword in decorator.keywords:
                                    if keyword.arg == 'response_model' and isinstance(keyword.value, ast.Name):
                                        response_model = keyword.value.id
                        
                        # 分析回傳值
                        return_types = []
                        
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Return):
                                # 檢查返回類型
                                if isinstance(subnode.value, ast.Dict):
                                    return_types.append('dict')
                                elif isinstance(subnode.value, ast.Call):
                                    if isinstance(subnode.value.func, ast.Name):
                                        return_types.append(subnode.value.func.id)
                                    elif isinstance(subnode.value.func, ast.Attribute):
                                        return_types.append(subnode.value.func.attr)
                        
                        self.response_handlers.append({
                            'endpoint': endpoint.get('path', ''),
                            'view': view_name,
                            'file': file_path,
                            'line': node.lineno,
                            'type': 'fastapi_endpoint',
                            'response_model': response_model,
                            'return_types': return_types,
                            'framework': 'fastapi'
                        })
            except Exception:
                continue
    
    def get_request_response_metrics(self) -> Dict[str, Any]:
        """
        計算請求和回應處理的指標
        
        Returns:
            包含請求/回應指標的字典
        """
        # 確保先運行分析
        if not self.request_handlers:
            self.analyze_request_handling()
        
        if not self.response_handlers:
            self.analyze_response_handling()
        
        # 請求處理統計
        request_methods = {}
        for handler in self.request_handlers:
            for method in handler.get('methods', []):
                request_methods[method] = request_methods.get(method, 0) + 1
        
        # 回應處理統計
        response_types = {}
        for handler in self.response_handlers:
            for response in handler.get('responses', []):
                response_type = response.get('type')
                if response_type:
                    response_types[response_type] = response_types.get(response_type, 0) + 1
        
        # 計算每個端點的指標
        endpoints_with_both = []
        endpoints_missing_request = []
        endpoints_missing_response = []
        
        all_endpoints = {endpoint.get('path', ''): endpoint for endpoint in self.endpoints}
        request_paths = {handler.get('endpoint', ''): handler for handler in self.request_handlers}
        response_paths = {handler.get('endpoint', ''): handler for handler in self.response_handlers}
        
        for path, endpoint in all_endpoints.items():
            has_request = path in request_paths
            has_response = path in response_paths
            
            if has_request and has_response:
                endpoints_with_both.append(path)
            elif has_request and not has_response:
                endpoints_missing_response.append(path)
            elif not has_request and has_response:
                endpoints_missing_request.append(path)
        
        return {
            'total_endpoints': len(self.endpoints),
            'endpoints_with_request_handling': len(self.request_handlers),
            'endpoints_with_response_handling': len(self.response_handlers),
            'request_methods_distribution': request_methods,
            'response_types_distribution': response_types,
            'endpoints_with_both': len(endpoints_with_both),
            'endpoints_missing_request': len(endpoints_missing_request),
            'endpoints_missing_response': len(endpoints_missing_response),
            'framework': self.framework
        }