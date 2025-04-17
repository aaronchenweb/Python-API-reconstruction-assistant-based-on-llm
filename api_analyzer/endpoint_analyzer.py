"""
端點分析器 - 分析 Web API 中的路由和端點。
支援 Django、Flask 和 FastAPI 應用程式的路由分析。
"""
import ast
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any

from code_analyzer.ast_parser import analyze_python_file
from utils.file_operations import read_file


class EndpointAnalyzer:
    """分析 Web API 中的路由和端點。"""
    
    def __init__(self, project_path: str):
        """
        初始化端點分析器
        
        Args:
            project_path: API 專案的路徑
        """
        self.project_path = project_path
        self.framework = None
        self.endpoints = []
        
    def detect_framework(self) -> str:
        """
        檢測專案使用的 web 框架
        
        Returns:
            檢測到的框架: 'django', 'flask', 'fastapi' 或 'unknown'
        """
        # 尋找關鍵檔案和導入
        has_django_files = os.path.exists(os.path.join(self.project_path, 'manage.py'))
        has_flask_files = self._find_imports_in_project('flask')
        has_fastapi_files = self._find_imports_in_project('fastapi')
        
        if has_django_files:
            self.framework = 'django'
        elif has_fastapi_files:
            self.framework = 'fastapi'
        elif has_flask_files:
            self.framework = 'flask'
        else:
            self.framework = 'unknown'
            
        return self.framework
    
    def _find_imports_in_project(self, module_name: str) -> bool:
        """
        在專案中尋找特定模組的導入
        
        Args:
            module_name: 要尋找的模組名稱
            
        Returns:
            如果找到導入則回傳 True，否則回傳 False
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 使用正則表達式尋找導入語句
                    pattern = rf'(import\s+{module_name}|from\s+{module_name}\s+import)'
                    if re.search(pattern, content):
                        return True
        
        return False
    
    def analyze_endpoints(self) -> List[Dict[str, Any]]:
        """
        分析 API 專案並識別所有端點
        
        Returns:
            端點資訊的列表
        """
        # 首先檢測框架
        if not self.framework:
            self.detect_framework()
        
        # 根據框架選擇分析方法
        if self.framework == 'django':
            self._analyze_django_endpoints()
        elif self.framework == 'flask':
            self._analyze_flask_endpoints()
        elif self.framework == 'fastapi':
            self._analyze_fastapi_endpoints()
        else:
            # 未知框架，嘗試一般分析
            self._analyze_generic_endpoints()
            
        return self.endpoints
    
    def _analyze_django_endpoints(self) -> None:
        """分析 Django 專案中的端點"""
        # 尋找 urls.py 檔案
        urls_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'urls.py':
                    urls_files.append(os.path.join(root, file))
        
        for url_file in urls_files:
            content = read_file(url_file)
            # 解析文件獲取AST
            try:
                tree = ast.parse(content)
                
                # 尋找 urlpatterns 列表
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == 'urlpatterns':
                                if isinstance(node.value, ast.List):
                                    self._extract_django_url_patterns(node.value, url_file)
            except SyntaxError:
                continue
    
    def _extract_django_url_patterns(self, url_list_node: ast.List, file_path: str) -> None:
        """
        從 Django urlpatterns 列表中提取端點
        
        Args:
            url_list_node: 包含 URL patterns 的 AST 節點
            file_path: 包含模式的文件的路徑
        """
        base_path = os.path.dirname(file_path)
        
        for element in url_list_node.elts:
            if isinstance(element, ast.Call):
                func_name = ""
                if isinstance(element.func, ast.Name):
                    func_name = element.func.id
                elif isinstance(element.func, ast.Attribute):
                    func_name = element.func.attr
                
                if func_name in ['path', 're_path', 'url']:
                    # 提取路徑和視圖
                    path_pattern = None
                    view_function = None
                    
                    # 獲取路徑模式 (第一個參數)
                    if element.args and len(element.args) > 0:
                        if isinstance(element.args[0], ast.Str):
                            path_pattern = element.args[0].s
                    
                    # 獲取視圖函數 (第二個參數)
                    if element.args and len(element.args) > 1:
                        view_arg = element.args[1]
                        if isinstance(view_arg, ast.Name):
                            view_function = view_arg.id
                        elif isinstance(view_arg, ast.Attribute):
                            if hasattr(view_arg.value, 'id'):
                                view_function = f"{view_arg.value.id}.{view_arg.attr}"
                        elif isinstance(view_arg, ast.Call) and isinstance(view_arg.func, ast.Name):
                            view_function = f"{view_arg.func.id}(...)"
                    
                    # 獲取名稱 (name 關鍵字參數)
                    endpoint_name = None
                    for keyword in element.keywords:
                        if keyword.arg == 'name' and isinstance(keyword.value, ast.Str):
                            endpoint_name = keyword.value.s
                    
                    # 添加端點到列表
                    if path_pattern:
                        self.endpoints.append({
                            'path': path_pattern,
                            'view': view_function,
                            'name': endpoint_name,
                            'framework': 'django',
                            'file': file_path,
                            'type': 'URL pattern'
                        })
                
                # 處理 include() 函數，可能包含嵌套的 URL 配置
                elif func_name == 'include':
                    # 這需要更複雜的遞迴分析
                    pass
    
    def _analyze_flask_endpoints(self) -> None:
        """分析 Flask 專案中的端點"""
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 查找 Flask app 並分析路由裝飾器
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找 Flask 應用程式實例
                        app_names = set()
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Assign):
                                for target in node.targets:
                                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                        call_func = node.value.func
                                        if (isinstance(call_func, ast.Name) and call_func.id == 'Flask') or \
                                           (isinstance(call_func, ast.Attribute) and call_func.attr == 'Flask'):
                                            app_names.add(target.id)
                        
                        # 尋找路由裝飾器
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                for decorator in node.decorator_list:
                                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                                        if decorator.func.attr == 'route' and isinstance(decorator.func.value, ast.Name):
                                            if decorator.func.value.id in app_names:
                                                # 獲取路由路徑
                                                if decorator.args and isinstance(decorator.args[0], ast.Str):
                                                    route_path = decorator.args[0].s
                                                    
                                                    # 獲取 HTTP 方法
                                                    methods = ['GET']  # 默認 GET
                                                    for keyword in decorator.keywords:
                                                        if keyword.arg == 'methods' and isinstance(keyword.value, ast.List):
                                                            methods = [m.s for m in keyword.value.elts if isinstance(m, ast.Str)]
                                                    
                                                    # 添加端點
                                                    for method in methods:
                                                        self.endpoints.append({
                                                            'path': route_path,
                                                            'view': node.name,
                                                            'method': method,
                                                            'framework': 'flask',
                                                            'file': file_path,
                                                            'line': node.lineno,
                                                            'type': 'Route decorator'
                                                        })
                    except SyntaxError:
                        continue
    
    def _analyze_fastapi_endpoints(self) -> None:
        """分析 FastAPI 專案中的端點"""
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 查找 FastAPI app 和路由裝飾器
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找 FastAPI 應用程式實例
                        app_names = set()
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Assign):
                                for target in node.targets:
                                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                        call_func = node.value.func
                                        if isinstance(call_func, ast.Name) and call_func.id == 'FastAPI':
                                            app_names.add(target.id)
                                        elif isinstance(call_func, ast.Attribute) and call_func.attr == 'APIRouter':
                                            app_names.add(target.id)
                        
                        # 尋找 HTTP 方法裝飾器
                        http_methods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                for decorator in node.decorator_list:
                                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                                        # 檢查是 app.get() 形式
                                        if decorator.func.attr.lower() in http_methods and isinstance(decorator.func.value, ast.Name):
                                            if decorator.func.value.id in app_names:
                                                # 獲取路由路徑
                                                if decorator.args and isinstance(decorator.args[0], ast.Str):
                                                    route_path = decorator.args[0].s
                                                    
                                                    # 獲取回應模型，如果有
                                                    response_model = None
                                                    for keyword in decorator.keywords:
                                                        if keyword.arg == 'response_model' and isinstance(keyword.value, ast.Name):
                                                            response_model = keyword.value.id
                                                    
                                                    # 添加端點
                                                    self.endpoints.append({
                                                        'path': route_path,
                                                        'view': node.name,
                                                        'method': decorator.func.attr.upper(),
                                                        'framework': 'fastapi',
                                                        'file': file_path,
                                                        'line': node.lineno,
                                                        'response_model': response_model,
                                                        'type': 'FastAPI endpoint'
                                                    })
                    except SyntaxError:
                        continue
    
    def _analyze_generic_endpoints(self) -> None:
        """嘗試通用方法來檢測 API 端點"""
        # 尋找帶有常見 API 相關名稱的函數和類
        api_keywords = ['api', 'endpoint', 'route', 'view', 'controller']
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    try:
                        result = analyze_python_file(content)
                        
                        # 檢查函數和類名稱中的 API 關鍵字
                        for func in result.get('functions', []):
                            if any(keyword in func['name'].lower() for keyword in api_keywords):
                                self.endpoints.append({
                                    'view': func['name'],
                                    'file': file_path,
                                    'line': func['line'],
                                    'framework': 'unknown',
                                    'type': 'Potential API function'
                                })
                        
                        for cls in result.get('classes', []):
                            if any(keyword in cls['name'].lower() for keyword in api_keywords):
                                self.endpoints.append({
                                    'class': cls['name'],
                                    'file': file_path,
                                    'line': cls['line'],
                                    'framework': 'unknown',
                                    'type': 'Potential API class'
                                })
                    except Exception:
                        continue
    
    def get_endpoint_metrics(self) -> Dict[str, Any]:
        """
        計算端點相關指標
        
        Returns:
            含有端點指標的字典
        """
        if not self.endpoints:
            self.analyze_endpoints()
            
        # 計算總端點數
        total_endpoints = len(self.endpoints)
        
        # 按 HTTP 方法分類
        methods = {}
        for endpoint in self.endpoints:
            method = endpoint.get('method', 'GET')
            methods[method] = methods.get(method, 0) + 1
        
        # 識別複雜端點（例如有多個參數的端點）
        complex_endpoints = []
        for endpoint in self.endpoints:
            path = endpoint.get('path', '')
            # 計算路徑中的參數數量
            param_count = path.count('{') + path.count('<')
            if param_count > 1:
                complex_endpoints.append({
                    'path': path,
                    'view': endpoint.get('view', ''),
                    'param_count': param_count
                })
        
        return {
            'total_endpoints': total_endpoints,
            'methods_distribution': methods,
            'complex_endpoints': complex_endpoints,
            'framework': self.framework
        }
    
    def find_endpoint_issues(self) -> List[Dict[str, Any]]:
        """
        識別端點中的潛在問題
        
        Returns:
            端點問題列表
        """
        issues = []
        
        if not self.endpoints:
            self.analyze_endpoints()
        
        # 檢查潛在的衝突路徑
        paths = {}
        for endpoint in self.endpoints:
            path = endpoint.get('path', '')
            method = endpoint.get('method', 'GET')
            
            # 將路徑標準化以檢測潛在衝突
            # 移除參數的具體名稱，留下結構
            normalized_path = re.sub(r'<[^>]+>', '<param>', path)
            normalized_path = re.sub(r'\{[^}]+\}', '{param}', normalized_path)
            
            key = f"{normalized_path}-{method}"
            if key in paths:
                issues.append({
                    'type': 'potential_path_conflict',
                    'description': f"潛在路徑衝突: {path} ({method})",
                    'endpoints': [paths[key], endpoint]
                })
            else:
                paths[key] = endpoint
        
        # 檢查非 RESTful 命名
        non_restful_words = ['get', 'post', 'put', 'delete', 'fetch', 'update', 'remove']
        for endpoint in self.endpoints:
            view_name = endpoint.get('view', '')
            if view_name:
                if any(word in view_name.lower() for word in non_restful_words):
                    method = endpoint.get('method', 'UNKNOWN')
                    # 檢查方法名稱是否與 HTTP 方法矛盾
                    if ('get' in view_name.lower() and method != 'GET') or \
                       ('post' in view_name.lower() and method != 'POST') or \
                       ('put' in view_name.lower() and method != 'PUT') or \
                       ('delete' in view_name.lower() and method != 'DELETE'):
                        issues.append({
                            'type': 'non_restful_naming',
                            'description': f"視圖名稱包含 HTTP 方法但與實際 HTTP 方法不符: {view_name} ({method})",
                            'endpoint': endpoint
                        })
        
        # 返回所有問題
        return issues