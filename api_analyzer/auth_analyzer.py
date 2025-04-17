"""
身份驗證分析器 - 分析 API 中的身份驗證機制和安全實踐。
"""
import ast
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any

from utils.file_operations import read_file


class AuthAnalyzer:
    """分析 API 中的身份驗證機制和安全實踐。"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化身份驗證分析器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.auth_methods = []
        self.security_issues = []
        
    def analyze_auth_methods(self) -> List[Dict[str, Any]]:
        """
        分析專案中使用的身份驗證方法
        
        Returns:
            身份驗證方法資訊的列表
        """
        if not self.framework:
            from .endpoint_analyzer import EndpointAnalyzer
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
        
        # 根據框架選擇適當的分析方法
        if self.framework == 'django':
            self._analyze_django_auth()
        elif self.framework == 'flask':
            self._analyze_flask_auth()
        elif self.framework == 'fastapi':
            self._analyze_fastapi_auth()
        
        # 通用分析方法
        self._analyze_generic_auth()
        
        return self.auth_methods
    
    def _analyze_django_auth(self) -> None:
        """分析 Django 身份驗證方法"""
        # 搜尋 settings.py 檔案以找到身份驗證配置
        settings_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'settings.py':
                    settings_files.append(os.path.join(root, file))
        
        for settings_file in settings_files:
            content = read_file(settings_file)
            
            # 檢查 Django REST Framework 身份驗證配置
            if 'REST_FRAMEWORK' in content and 'DEFAULT_AUTHENTICATION_CLASSES' in content:
                try:
                    tree = ast.parse(content)
                    
                    # 尋找 REST_FRAMEWORK 設定
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Assign):
                            for target in node.targets:
                                if isinstance(target, ast.Name) and target.id == 'REST_FRAMEWORK':
                                    if isinstance(node.value, ast.Dict):
                                        # 尋找 DEFAULT_AUTHENTICATION_CLASSES
                                        for key, value in zip(node.value.keys, node.value.values):
                                            if isinstance(key, ast.Constant) and key.value == 'DEFAULT_AUTHENTICATION_CLASSES':
                                                if isinstance(value, ast.List):
                                                    # 提取身份驗證類列表
                                                    auth_classes = []
                                                    for elt in value.elts:
                                                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                                            auth_classes.append(elt.value)
                                                    
                                                    if auth_classes:
                                                        self.auth_methods.append({
                                                            'type': 'django_rest_framework',
                                                            'classes': auth_classes,
                                                            'file': settings_file,
                                                            'framework': 'django'
                                                        })
                except SyntaxError:
                    continue
        
        # 檢查 Django 視圖裝飾器
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 尋找身份驗證裝飾器
                    if any(decorator in content for decorator in ['@login_required', '@permission_required', '@user_passes_test']):
                        try:
                            tree = ast.parse(content)
                            
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    auth_decorators = []
                                    
                                    for decorator in node.decorator_list:
                                        decorator_name = None
                                        
                                        if isinstance(decorator, ast.Name):
                                            decorator_name = decorator.id
                                        elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                                            decorator_name = decorator.func.id
                                        
                                        if decorator_name in ['login_required', 'permission_required', 'user_passes_test']:
                                            auth_decorators.append(decorator_name)
                                    
                                    if auth_decorators:
                                        self.auth_methods.append({
                                            'type': 'django_decorator',
                                            'function': node.name,
                                            'decorators': auth_decorators,
                                            'file': file_path,
                                            'line': node.lineno,
                                            'framework': 'django'
                                        })
                        except SyntaxError:
                            continue
    
    def _analyze_flask_auth(self) -> None:
        """分析 Flask 身份驗證方法"""
        # 尋找常見的 Flask 身份驗證套件
        auth_packages = ['flask_login', 'flask_security', 'flask_jwt', 'flask_jwt_extended']
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查導入
                    import_found = False
                    auth_package = None
                    
                    for package in auth_packages:
                        if f"import {package}" in content or f"from {package}" in content:
                            import_found = True
                            auth_package = package
                            break
                    
                    if import_found:
                        # 分析使用方式
                        try:
                            tree = ast.parse(content)
                            
                            # 檢查 Flask-Login
                            if auth_package == 'flask_login':
                                # 尋找 @login_required 裝飾器
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.FunctionDef):
                                        for decorator in node.decorator_list:
                                            if (isinstance(decorator, ast.Name) and decorator.id == 'login_required') or \
                                               (isinstance(decorator, ast.Call) and 
                                                isinstance(decorator.func, ast.Name) and 
                                                decorator.func.id == 'login_required'):
                                                self.auth_methods.append({
                                                    'type': 'flask_login',
                                                    'function': node.name,
                                                    'file': file_path,
                                                    'line': node.lineno,
                                                    'framework': 'flask'
                                                })
                            
                            # 檢查 Flask-JWT
                            elif auth_package in ['flask_jwt', 'flask_jwt_extended']:
                                # 尋找 jwt_required 裝飾器
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.FunctionDef):
                                        for decorator in node.decorator_list:
                                            if (isinstance(decorator, ast.Name) and 'jwt_required' in decorator.id) or \
                                               (isinstance(decorator, ast.Call) and 
                                                isinstance(decorator.func, ast.Name) and 
                                                'jwt_required' in decorator.func.id):
                                                self.auth_methods.append({
                                                    'type': auth_package,
                                                    'function': node.name,
                                                    'file': file_path,
                                                    'line': node.lineno,
                                                    'framework': 'flask'
                                                })
                            
                        except SyntaxError:
                            continue
    
    def _analyze_fastapi_auth(self) -> None:
        """分析 FastAPI 身份驗證方法"""
        # 尋找 FastAPI 安全依賴項
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查 OAuth2PasswordBearer 和其他安全相關導入
                    security_imports = [
                        'OAuth2PasswordBearer', 'OAuth2AuthorizationCodeBearer', 'HTTPBearer', 
                        'HTTPBasic', 'SecurityScopes', 'APIKeyCookie', 'APIKeyHeader', 'APIKeyQuery'
                    ]
                    
                    if any(security_import in content for security_import in security_imports) or 'fastapi.security' in content:
                        try:
                            tree = ast.parse(content)
                            
                            # 尋找安全方案初始化
                            security_schemes = []
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                                    call_func = node.value.func
                                    if isinstance(call_func, ast.Name) and call_func.id in security_imports:
                                        for target in node.targets:
                                            if isinstance(target, ast.Name):
                                                security_schemes.append({
                                                    'name': target.id,
                                                    'type': call_func.id,
                                                    'line': node.lineno
                                                })
                            
                            # 尋找使用安全依賴項的端點
                            for node in ast.walk(tree):
                                if isinstance(node, ast.FunctionDef):
                                    # 檢查函數參數是否包含安全依賴項
                                    for arg in node.args.args:
                                        arg_name = arg.arg
                                        # 檢查參數是否使用了之前定義的安全方案
                                        for scheme in security_schemes:
                                            if arg_name == scheme['name'] or (
                                                arg.annotation and isinstance(arg.annotation, ast.Name) and
                                                arg.annotation.id == scheme['name']
                                            ):
                                                self.auth_methods.append({
                                                    'type': 'fastapi_security',
                                                    'scheme': scheme['type'],
                                                    'function': node.name,
                                                    'file': file_path,
                                                    'line': node.lineno,
                                                    'framework': 'fastapi'
                                                })
                        except SyntaxError:
                            continue
    
    def _analyze_generic_auth(self) -> None:
        """分析通用身份驗證方法（使用啟發式方法）"""
        # 尋找與身份驗證相關的關鍵字
        auth_keywords = ['auth', 'login', 'jwt', 'token', 'oauth', 'password', 'security']
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否已經通過特定框架分析找到此文件的身份驗證方法
                    already_analyzed = any(method['file'] == file_path for method in self.auth_methods)
                    if already_analyzed:
                        continue
                    
                    # 檢查關鍵字
                    if not any(keyword in content.lower() for keyword in auth_keywords):
                        continue
                    
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找可能是身份驗證函數的函數
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                func_name = node.name.lower()
                                # 檢查函數名中是否包含身份驗證關鍵字
                                if any(keyword in func_name for keyword in auth_keywords):
                                    self.auth_methods.append({
                                        'type': 'potential_auth_function',
                                        'function': node.name,
                                        'file': file_path,
                                        'line': node.lineno,
                                        'framework': 'unknown',
                                        'confidence': 'low'  # 表示這是一個啟發式檢測
                                    })
                        
                        # 尋找可能是身份驗證檢查的類別
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                class_name = node.name.lower()
                                # 檢查類名中是否包含身份驗證關鍵字
                                if any(keyword in class_name for keyword in auth_keywords):
                                    self.auth_methods.append({
                                        'type': 'potential_auth_class',
                                        'class': node.name,
                                        'file': file_path,
                                        'line': node.lineno,
                                        'framework': 'unknown',
                                        'confidence': 'low'  # 表示這是一個啟發式檢測
                                    })
                    except SyntaxError:
                        continue
    
    def identify_security_issues(self) -> List[Dict[str, Any]]:
        """
        識別身份驗證和授權相關的安全問題
        
        Returns:
            安全問題列表
        """
        # 首先分析身份驗證方法
        if not self.auth_methods:
            self.analyze_auth_methods()
        
        # 尋找常見安全問題
        self._identify_hardcoded_secrets()
        self._identify_missing_auth()
        self._identify_insecure_settings()
        
        return self.security_issues
    
    def _identify_hardcoded_secrets(self) -> None:
        """識別程式碼中的硬編碼機密"""
        # 定義可能包含機密的變數名
        secret_var_names = ['password', 'secret', 'key', 'token', 'api_key', 'apikey', 'private']
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找可能包含機密的變數賦值
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                for target in node.targets:
                                    if isinstance(target, ast.Name):
                                        var_name = target.id.lower()
                                        if any(secret_name in var_name for secret_name in secret_var_names):
                                            # 檢查是否是一個有潛在風險的硬編碼值（不是空字符串或明顯的非機密）
                                            value = node.value.value
                                            if value and len(value) > 5 and not value.isspace():
                                                self.security_issues.append({
                                                    'type': 'hardcoded_secret',
                                                    'variable': target.id,
                                                    'file': file_path,
                                                    'line': node.lineno,
                                                    'severity': 'high',
                                                    'description': f"可能的硬編碼機密: 變數名 '{target.id}' 包含一個字符串值"
                                                })
                    except SyntaxError:
                        continue
    
    def _identify_missing_auth(self) -> None:
        """識別可能缺少身份驗證的 API 端點"""
        from .endpoint_analyzer import EndpointAnalyzer
        
        # 獲取所有端點
        endpoint_analyzer = EndpointAnalyzer(self.project_path)
        endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 檢查每個端點是否有身份驗證
        for endpoint in endpoints:
            endpoint_file = endpoint.get('file', '')
            
            # 跳過明顯不需要身份驗證的端點（如公開 API）
            path = endpoint.get('path', '')
            if 'public' in path or 'docs' in path or 'schema' in path or 'swagger' in path:
                continue
            
            # 檢查此文件中是否有身份驗證方法
            auth_for_file = any(method['file'] == endpoint_file for method in self.auth_methods)
            
            # 如果是 Django REST 框架，檢查是否在設置中設定了全局身份驗證
            has_global_auth = any(method['type'] == 'django_rest_framework' for method in self.auth_methods)
            
            # 如果這個端點似乎沒有身份驗證
            if not auth_for_file and not has_global_auth:
                self.security_issues.append({
                    'type': 'missing_auth',
                    'endpoint': endpoint.get('path', 'unknown'),
                    'method': endpoint.get('method', 'unknown'),
                    'file': endpoint_file,
                    'line': endpoint.get('line', 0),
                    'severity': 'medium',
                    'description': f"可能缺少身份驗證: 找不到用於端點 '{endpoint.get('path', 'unknown')}' 的身份驗證機制"
                })
    
    def _identify_insecure_settings(self) -> None:
        """識別不安全的安全設置"""
        if self.framework == 'django':
            # 尋找 Django 設置文件
            for root, _, files in os.walk(self.project_path):
                for file in files:
                    if file == 'settings.py':
                        file_path = os.path.join(root, file)
                        content = read_file(file_path)
                        
                        # 檢查不安全設置
                        if 'DEBUG = True' in content:
                            self.security_issues.append({
                                'type': 'insecure_setting',
                                'setting': 'DEBUG',
                                'file': file_path,
                                'severity': 'medium',
                                'description': "生產環境不應啟用調試模式，這可能泄露敏感信息"
                            })
                        
                        # 檢查是否使用不安全的雜湊演算法
                        if 'PASSWORD_HASHERS' in content:
                            try:
                                tree = ast.parse(content)
                                
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.Assign):
                                        for target in node.targets:
                                            if isinstance(target, ast.Name) and target.id == 'PASSWORD_HASHERS':
                                                if isinstance(node.value, ast.List):
                                                    for elt in node.value.elts:
                                                        if isinstance(elt, ast.Constant) and 'MD5' in elt.value:
                                                            self.security_issues.append({
                                                                'type': 'insecure_setting',
                                                                'setting': 'PASSWORD_HASHERS',
                                                                'file': file_path,
                                                                'line': node.lineno,
                                                                'severity': 'high',
                                                                'description': "使用了不安全的密碼雜湊演算法 (MD5)"
                                                            })
                            except SyntaxError:
                                continue
        
        elif self.framework == 'flask':
            # 尋找 Flask 設置
            for root, _, files in os.walk(self.project_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        content = read_file(file_path)
                        
                        # 檢查不安全的 Flask 設置
                        if 'app.config' in content and 'SECRET_KEY' in content:
                            try:
                                tree = ast.parse(content)
                                
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                                        for target in node.targets:
                                            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Attribute):
                                                if target.value.attr == 'config' and isinstance(target.slice, ast.Constant):
                                                    if target.slice.value == 'SECRET_KEY' and len(node.value.value) < 16:
                                                        self.security_issues.append({
                                                            'type': 'insecure_setting',
                                                            'setting': 'SECRET_KEY',
                                                            'file': file_path,
                                                            'line': node.lineno,
                                                            'severity': 'high',
                                                            'description': "使用了不夠強大的 SECRET_KEY (太短或太簡單)"
                                                        })
                            except SyntaxError:
                                continue