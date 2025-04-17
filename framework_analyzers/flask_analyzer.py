"""
Flask 分析器 - 提供 Flask 專案專門的分析功能
"""
import ast
import os
import re
import json
from typing import Dict, List, Set, Tuple, Optional, Any

from code_analyzer.ast_parser import analyze_python_file
from utils.file_operations import read_file
from api_analyzer.endpoint_analyzer import EndpointAnalyzer


class FlaskAnalyzer:
    """提供 Flask 專案專門的分析功能"""
    
    def __init__(self, project_path: str):
        """
        初始化 Flask 分析器
        
        Args:
            project_path: Flask 專案的路徑
        """
        self.project_path = project_path
        self.project_structure = None
        
    def detect_project_structure(self) -> Dict[str, Any]:
        """
        檢測 Flask 專案結構
        
        Returns:
            包含專案結構資訊的字典
        """
        # 初始化結構資訊
        structure = {
            'app_file': None,
            'app_variables': [],
            'blueprints': [],
            'extensions': [],
            'templates_dir': None,
            'static_dir': None,
            'config_file': None,
            'is_factory_pattern': False,
            'is_blueprint_pattern': False
        }
        
        # 查找主應用文件（app.py 或 __init__.py）
        app_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'app.py' or (file == '__init__.py' and 'flask' in read_file(os.path.join(root, file)).lower()):
                    app_files.append(os.path.join(root, file))
        
        if app_files:
            # 使用第一個找到的應用文件
            structure['app_file'] = app_files[0]
            
            # 分析應用文件
            content = read_file(structure['app_file'])
            
            # 檢查是否使用工廠模式
            structure['is_factory_pattern'] = 'create_app' in content or 'make_app' in content or 'setup_app' in content
            
            try:
                tree = ast.parse(content)
                
                # 尋找 Flask 應用實例
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Flask':
                                    structure['app_variables'].append(target.id)
                
                # 尋找藍圖
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Blueprint':
                                    structure['blueprints'].append({
                                        'name': target.id,
                                        'line': node.lineno
                                    })
                                    structure['is_blueprint_pattern'] = True
                
                # 尋找擴展
                flask_extensions = ['SQLAlchemy', 'Migrate', 'Login', 'Mail', 'WTF', 'Security', 'Bcrypt', 'Cors', 'JWT']
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Name) and any(ext in node.value.func.id for ext in flask_extensions):
                                    structure['extensions'].append({
                                        'name': target.id,
                                        'type': node.value.func.id,
                                        'line': node.lineno
                                    })
            except SyntaxError:
                pass
        
        # 查找配置文件
        config_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'config.py' or file == 'settings.py':
                    config_files.append(os.path.join(root, file))
        
        if config_files:
            structure['config_file'] = config_files[0]
        
        # 查找模板和靜態文件目錄
        for root, dirs, _ in os.walk(self.project_path):
            for directory in dirs:
                if directory == 'templates':
                    structure['templates_dir'] = os.path.join(root, directory)
                elif directory == 'static':
                    structure['static_dir'] = os.path.join(root, directory)
        
        self.project_structure = structure
        return structure
    
    def analyze_routes(self) -> List[Dict[str, Any]]:
        """
        分析 Flask 路由
        
        Returns:
            包含路由資訊的列表
        """
        # 使用 EndpointAnalyzer 獲取端點
        endpoint_analyzer = EndpointAnalyzer(self.project_path)
        endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 過濾 Flask 端點
        flask_routes = [endpoint for endpoint in endpoints if endpoint.get('framework') == 'flask']
        
        # 提取路由詳情
        routes = []
        for route in flask_routes:
            route_info = {
                'path': route.get('path', ''),
                'view': route.get('view', ''),
                'method': route.get('method', 'GET'),
                'file': route.get('file', ''),
                'line': route.get('line', 0)
            }
            routes.append(route_info)
        
        return routes
    
    def analyze_view_functions(self) -> List[Dict[str, Any]]:
        """
        分析 Flask 視圖函數
        
        Returns:
            包含視圖函數資訊的列表
        """
        view_functions = []
        
        # 獲取路由先
        routes = self.analyze_routes()
        
        # 檢索視圖函數詳情
        for route in routes:
            view_name = route.get('view', '')
            file_path = route.get('file', '')
            
            if not view_name or not file_path:
                continue
            
            # 分析視圖函數
            try:
                content = read_file(file_path)
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == view_name:
                        # 提取函數參數
                        args = [arg.arg for arg in node.args.args]
                        
                        # 提取文檔字符串
                        docstring = ast.get_docstring(node) or ""
                        
                        # 檢查請求處理
                        uses_request = False
                        request_methods = []
                        
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Attribute) and isinstance(subnode.value, ast.Name):
                                if subnode.value.id == 'request':
                                    uses_request = True
                                    request_methods.append(subnode.attr)
                        
                        # 檢查是否返回 JSON
                        returns_json = False
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Call):
                                if isinstance(subnode.func, ast.Name) and subnode.func.id == 'jsonify':
                                    returns_json = True
                        
                        view_info = {
                            'name': view_name,
                            'file': file_path,
                            'line': node.lineno,
                            'args': args,
                            'docstring': docstring,
                            'uses_request': uses_request,
                            'request_methods': list(set(request_methods)),
                            'returns_json': returns_json,
                            'route': route.get('path', ''),
                            'http_method': route.get('method', 'GET')
                        }
                        view_functions.append(view_info)
                        break
            except Exception:
                continue
        
        return view_functions
    
    def analyze_blueprints(self) -> List[Dict[str, Any]]:
        """
        分析 Flask 藍圖
        
        Returns:
            包含藍圖資訊的列表
        """
        blueprints = []
        
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 查找藍圖定義文件
        blueprint_files = []
        
        if self.project_structure['app_file']:
            blueprint_files.append(self.project_structure['app_file'])
        
        # 查找其他可能包含藍圖的文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if file_path != self.project_structure.get('app_file'):
                        content = read_file(file_path)
                        if 'Blueprint(' in content:
                            blueprint_files.append(file_path)
        
        # 分析每個文件中的藍圖
        for file_path in blueprint_files:
            try:
                content = read_file(file_path)
                tree = ast.parse(content)
                
                # 尋找藍圖定義
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Name) and node.value.func.id == 'Blueprint':
                                    # 獲取藍圖名稱和 URL 前綴
                                    blueprint_name = target.id
                                    url_prefix = None
                                    
                                    # 檢查是否有 url_prefix 參數
                                    for keyword in node.value.keywords:
                                        if keyword.arg == 'url_prefix' and isinstance(keyword.value, ast.Constant):
                                            url_prefix = keyword.value.value
                                    
                                    # 獲取藍圖路由
                                    routes = []
                                    for route in self.analyze_routes():
                                        view_name = route.get('view', '')
                                        if '.' in view_name and view_name.split('.')[0] == blueprint_name:
                                            routes.append(route)
                                    
                                    blueprint_info = {
                                        'name': blueprint_name,
                                        'file': file_path,
                                        'line': node.lineno,
                                        'url_prefix': url_prefix,
                                        'routes_count': len(routes),
                                        'routes': routes
                                    }
                                    blueprints.append(blueprint_info)
            except SyntaxError:
                continue
        
        return blueprints
    
    def analyze_extensions(self) -> List[Dict[str, Any]]:
        """
        分析 Flask 擴展
        
        Returns:
            包含擴展資訊的列表
        """
        extensions = []
        
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 首先嘗試從使用模式中識別擴展
        known_extensions = {
            'SQLAlchemy': ['db', 'sqlalchemy', 'from flask_sqlalchemy'],
            'Migrate': ['migrate', 'from flask_migrate'],
            'Login': ['login', 'LoginManager', 'from flask_login'],
            'WTF': ['form', 'FlaskForm', 'from flask_wtf'],
            'Mail': ['mail', 'from flask_mail'],
            'JWT': ['jwt', 'from flask_jwt'],
            'Cors': ['cors', 'CORS', 'from flask_cors'],
            'Bcrypt': ['bcrypt', 'from flask_bcrypt'],
            'Session': ['session', 'Session', 'from flask_session'],
            'Marshmallow': ['ma', 'marshmallow', 'from flask_marshmallow'],
            'RestPlus': ['api', 'restplus', 'from flask_restplus'],
            'RestX': ['api', 'restx', 'from flask_restx']
        }
        
        # 尋找可能的擴展
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查已知擴展的導入模式
                    for ext_name, patterns in known_extensions.items():
                        if any(pattern in content for pattern in patterns):
                            # 尋找具體的擴展實例
                            try:
                                tree = ast.parse(content)
                                
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.Assign):
                                        for target in node.targets:
                                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                                call_name = ""
                                                
                                                if isinstance(node.value.func, ast.Name):
                                                    call_name = node.value.func.id
                                                elif isinstance(node.value.func, ast.Attribute):
                                                    if isinstance(node.value.func.value, ast.Name):
                                                        call_name = f"{node.value.func.value.id}.{node.value.func.attr}"
                                                
                                                # 檢查是否是目標擴展的實例化
                                                if any(pattern.lower() in call_name.lower() for pattern in patterns):
                                                    extensions.append({
                                                        'name': target.id,
                                                        'type': ext_name,
                                                        'file': file_path,
                                                        'line': node.lineno
                                                    })
                            except SyntaxError:
                                continue
        
        return extensions
    
    def get_flask_metrics(self) -> Dict[str, Any]:
        """
        獲取 Flask 專案指標
        
        Returns:
            包含專案指標的字典
        """
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 分析路由
        routes = self.analyze_routes()
        
        # 分析視圖函數
        view_functions = self.analyze_view_functions()
        
        # 分析藍圖
        blueprints = self.analyze_blueprints()
        
        # 分析擴展
        extensions = self.analyze_extensions()
        
        # 計算指標
        return {
            'routes_count': len(routes),
            'view_functions_count': len(view_functions),
            'blueprints_count': len(blueprints),
            'extensions_count': len(extensions),
            'uses_blueprints': len(blueprints) > 0,
            'uses_factory_pattern': self.project_structure.get('is_factory_pattern', False),
            'has_templates': self.project_structure.get('templates_dir') is not None,
            'has_static': self.project_structure.get('static_dir') is not None,
            'has_separate_config': self.project_structure.get('config_file') is not None,
            'json_routes_percentage': sum(1 for func in view_functions if func.get('returns_json', False)) / len(view_functions) * 100 if view_functions else 0
        }