"""
FastAPI 分析器 - 提供 FastAPI 專案專門的分析功能
"""
import ast
import os
import re
import json
from typing import Dict, List, Set, Tuple, Optional, Any

from code_analyzer.ast_parser import analyze_python_file
from utils.file_operations import read_file
from api_analyzer.endpoint_analyzer import EndpointAnalyzer


class FastAPIAnalyzer:
    """提供 FastAPI 專案專門的分析功能"""
    
    def __init__(self, project_path: str):
        """
        初始化 FastAPI 分析器
        
        Args:
            project_path: FastAPI 專案的路徑
        """
        self.project_path = project_path
        self.project_structure = None
        
    def detect_project_structure(self) -> Dict[str, Any]:
        """
        檢測 FastAPI 專案結構
        
        Returns:
            包含專案結構資訊的字典
        """
        # 初始化結構資訊
        structure = {
            'app_file': None,
            'app_variables': [],
            'routers': [],
            'schemas_dir': None,
            'models_dir': None,
            'uses_dependency_injection': False,
            'uses_pydantic': False,
            'uses_sqlalchemy': False,
            'uses_middleware': False
        }
        
        # 查找主應用文件（main.py 或 app.py）
        app_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file in ['main.py', 'app.py'] or file == '__init__.py':
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    if 'fastapi' in content.lower():
                        app_files.append(file_path)
        
        if app_files:
            # 使用第一個找到的應用文件
            structure['app_file'] = app_files[0]
            
            # 分析應用文件
            content = read_file(structure['app_file'])
            
            # 檢查是否使用 Pydantic
            structure['uses_pydantic'] = 'pydantic' in content
            
            # 檢查是否使用 SQLAlchemy
            structure['uses_sqlalchemy'] = 'sqlalchemy' in content
            
            # 檢查是否使用中間件
            structure['uses_middleware'] = 'middleware' in content
            
            try:
                tree = ast.parse(content)
                
                # 尋找 FastAPI 應用實例
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Name) and node.value.func.id == 'FastAPI':
                                    structure['app_variables'].append(target.id)
                
                # 尋找路由器
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'APIRouter':
                                    structure['routers'].append({
                                        'name': target.id,
                                        'line': node.lineno
                                    })
                
                # 檢查依賴注入
                structure['uses_dependency_injection'] = 'Depends' in content
            except SyntaxError:
                pass
        
        # 查找模式和模型目錄
        for root, dirs, _ in os.walk(self.project_path):
            for directory in dirs:
                if directory.lower() == 'schemas' or directory.lower() == 'schema':
                    structure['schemas_dir'] = os.path.join(root, directory)
                elif directory.lower() == 'models' or directory.lower() == 'model':
                    structure['models_dir'] = os.path.join(root, directory)
        
        self.project_structure = structure
        return structure
    
    def analyze_endpoints(self) -> List[Dict[str, Any]]:
        """
        分析 FastAPI 端點
        
        Returns:
            包含端點資訊的列表
        """
        # 使用 EndpointAnalyzer 獲取端點
        endpoint_analyzer = EndpointAnalyzer(self.project_path)
        endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 過濾 FastAPI 端點
        fastapi_endpoints = [endpoint for endpoint in endpoints if endpoint.get('framework') == 'fastapi']
        
        # 豐富端點詳情
        for endpoint in fastapi_endpoints:
            file_path = endpoint.get('file', '')
            view_name = endpoint.get('view', '')
            
            if file_path and view_name:
                # 獲取更多端點詳情
                self._enrich_endpoint_details(endpoint, file_path, view_name)
        
        return fastapi_endpoints
    
    def _enrich_endpoint_details(self, endpoint: Dict[str, Any], file_path: str, view_name: str) -> None:
        """
        豐富端點詳情
        
        Args:
            endpoint: 端點字典
            file_path: 文件路徑
            view_name: 視圖函數名
        """
        try:
            content = read_file(file_path)
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == view_name:
                    # 提取函數參數
                    params = []
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
                        
                        params.append({
                            'name': arg_name,
                            'type': arg_type
                        })
                    
                    endpoint['params'] = params
                    
                    # 提取回應模型
                    response_model = None
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            # 尋找 response_model 參數
                            for keyword in decorator.keywords:
                                if keyword.arg == 'response_model' and isinstance(keyword.value, ast.Name):
                                    response_model = keyword.value.id
                    
                    if response_model:
                        endpoint['response_model'] = response_model
                    
                    # 提取文檔字符串
                    docstring = ast.get_docstring(node) or ""
                    endpoint['docstring'] = docstring
                    # 提取依賴項
                    dependencies = []
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Name) and subnode.func.id == 'Depends':
                            if subnode.args and isinstance(subnode.args[0], ast.Name):
                                dependencies.append(subnode.args[0].id)
                    
                    if dependencies:
                        endpoint['dependencies'] = dependencies
                    
                    break
        except Exception:
            pass
    
    def analyze_pydantic_models(self) -> List[Dict[str, Any]]:
        """
        分析 Pydantic 數據模型
        
        Returns:
            包含 Pydantic 模型資訊的列表
        """
        models = []
        
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 模式目錄
        schemas_dir = self.project_structure.get('schemas_dir')
        if schemas_dir:
            # 分析 schemas 目錄中的所有 Python 文件
            for root, _, files in os.walk(schemas_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        self._extract_pydantic_models(file_path, models)
        
        # 查找其他可能包含 Pydantic 模型的文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # 跳過已處理的 schemas 目錄
                    if schemas_dir and file_path.startswith(schemas_dir):
                        continue
                    
                    # 檢查文件是否使用 Pydantic
                    content = read_file(file_path)
                    if 'pydantic' in content and 'BaseModel' in content:
                        self._extract_pydantic_models(file_path, models)
        
        return models
    
    def _extract_pydantic_models(self, file_path: str, models: List[Dict[str, Any]]) -> None:
        """
        從文件中提取 Pydantic 模型
        
        Args:
            file_path: 文件路徑
            models: 模型列表
        """
        try:
            content = read_file(file_path)
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # 檢查基類是否包含 BaseModel
                    is_pydantic_model = False
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == 'BaseModel':
                            is_pydantic_model = True
                        elif isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                            if base.value.id == 'pydantic' and base.attr == 'BaseModel':
                                is_pydantic_model = True
                    
                    if is_pydantic_model:
                        # 提取欄位
                        fields = []
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                field_name = item.target.id
                                field_type = None
                                
                                # 提取類型註解
                                if item.annotation:
                                    if isinstance(item.annotation, ast.Name):
                                        field_type = item.annotation.id
                                    elif isinstance(item.annotation, ast.Subscript):
                                        if isinstance(item.annotation.value, ast.Name):
                                            field_type = f"{item.annotation.value.id}[...]"
                                
                                # 提取默認值
                                default_value = None
                                if item.value:
                                    if isinstance(item.value, ast.Constant):
                                        default_value = item.value.value
                                    elif isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                                        default_value = f"{item.value.func.id}(...)"
                                
                                fields.append({
                                    'name': field_name,
                                    'type': field_type,
                                    'default': default_value,
                                    'line': item.lineno
                                })
                        
                        # 提取配置
                        config = {}
                        for item in node.body:
                            if isinstance(item, ast.ClassDef) and item.name == 'Config':
                                for config_item in item.body:
                                    if isinstance(config_item, ast.Assign):
                                        for target in config_item.targets:
                                            if isinstance(target, ast.Name):
                                                config_name = target.id
                                                
                                                # 提取配置值
                                                if isinstance(config_item.value, ast.Constant):
                                                    config[config_name] = config_item.value.value
                                                elif isinstance(config_item.value, ast.List):
                                                    config[config_name] = [
                                                        elt.value if isinstance(elt, ast.Constant) else None
                                                        for elt in config_item.value.elts
                                                    ]
                        
                        models.append({
                            'name': node.name,
                            'file': file_path,
                            'line': node.lineno,
                            'fields': fields,
                            'config': config,
                            'docstring': ast.get_docstring(node) or ""
                        })
        except SyntaxError:
            pass
    
    def analyze_dependencies(self) -> List[Dict[str, Any]]:
        """
        分析 FastAPI 依賴注入
        
        Returns:
            包含依賴項資訊的列表
        """
        dependencies = []
        
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 忽略如果專案不使用依賴注入
        if not self.project_structure.get('uses_dependency_injection', False):
            return dependencies
        
        # 尋找可能包含依賴項函數的文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否使用 Depends
                    if 'Depends' not in content:
                        continue
                    
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找函數和類方法
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                # 檢查這個函數是否被用作依賴項
                                used_as_dependency = False
                                
                                # 檢查函數參數是否包含注入
                                has_injected_params = False
                                for arg in node.args.args:
                                    if arg.annotation and isinstance(arg.annotation, ast.Call):
                                        if isinstance(arg.annotation.func, ast.Name) and arg.annotation.func.id == 'Depends':
                                            has_injected_params = True
                                
                                # 尋找使用此函數的 Depends 調用
                                for subnode in ast.walk(tree):
                                    if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Name) and subnode.func.id == 'Depends':
                                        if subnode.args and isinstance(subnode.args[0], ast.Name) and subnode.args[0].id == node.name:
                                            used_as_dependency = True
                                
                                if used_as_dependency or has_injected_params:
                                    # 提取函數參數
                                    params = []
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
                                        
                                        params.append({
                                            'name': arg_name,
                                            'type': arg_type
                                        })
                                    
                                    dependencies.append({
                                        'name': node.name,
                                        'file': file_path,
                                        'line': node.lineno,
                                        'params': params,
                                        'used_as_dependency': used_as_dependency,
                                        'has_injected_params': has_injected_params,
                                        'docstring': ast.get_docstring(node) or ""
                                    })
                    except SyntaxError:
                        continue
        
        return dependencies
    
    def analyze_routers(self) -> List[Dict[str, Any]]:
        """
        分析 FastAPI 路由器
        
        Returns:
            包含路由器資訊的列表
        """
        routers = []
        
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 從專案結構中獲取路由器
        for router in self.project_structure.get('routers', []):
            router_name = router.get('name', '')
            
            if not router_name:
                continue
            
            # 尋找使用此路由器的端點
            endpoints = []
            all_endpoints = self.analyze_endpoints()
            
            for endpoint in all_endpoints:
                # 檢查端點是否屬於此路由器
                view_name = endpoint.get('view', '')
                file_path = endpoint.get('file', '')
                
                if file_path:
                    # 檢查文件中是否使用此路由器
                    content = read_file(file_path)
                    if f"{router_name}." in content:
                        endpoints.append(endpoint)
            
            # 獲取路由器的前綴
            prefix = None
            
            # 尋找路由器定義
            app_file = self.project_structure.get('app_file')
            if app_file:
                content = read_file(app_file)
                
                # 尋找路由器包含的語句
                include_pattern = rf'{re.escape(router_name)}.*?include_router\('
                include_match = re.search(include_pattern, content, re.DOTALL)
                
                if include_match:
                    # 尋找 prefix 參數
                    prefix_pattern = r'prefix\s*=\s*[\'"]([^\'"]*)[\'"]'
                    prefix_match = re.search(prefix_pattern, include_match.group(0))
                    
                    if prefix_match:
                        prefix = prefix_match.group(1)
            
            routers.append({
                'name': router_name,
                'prefix': prefix,
                'endpoints_count': len(endpoints),
                'endpoints': endpoints
            })
        
        return routers
    
    def get_fastapi_metrics(self) -> Dict[str, Any]:
        """
        獲取 FastAPI 專案指標
        
        Returns:
            包含專案指標的字典
        """
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 分析端點
        endpoints = self.analyze_endpoints()
        
        # 分析 Pydantic 模型
        models = self.analyze_pydantic_models()
        
        # 分析依賴項
        dependencies = self.analyze_dependencies()
        
        # 分析路由器
        routers = self.analyze_routers()
        
        # 計算指標
        return {
            'endpoints_count': len(endpoints),
            'pydantic_models_count': len(models),
            'dependencies_count': len(dependencies),
            'routers_count': len(routers),
            'uses_pydantic': self.project_structure.get('uses_pydantic', False),
            'uses_sqlalchemy': self.project_structure.get('uses_sqlalchemy', False),
            'uses_dependency_injection': self.project_structure.get('uses_dependency_injection', False),
            'uses_middleware': self.project_structure.get('uses_middleware', False),
            'path_operations_distribution': self._calculate_path_operations_distribution(endpoints)
        }
    
    def _calculate_path_operations_distribution(self, endpoints: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        計算端點的 HTTP 方法分布
        
        Args:
            endpoints: 端點列表
            
        Returns:
            HTTP 方法分布的字典
        """
        distribution = {}
        
        for endpoint in endpoints:
            method = endpoint.get('method', 'GET')
            distribution[method] = distribution.get(method, 0) + 1
        
        return distribution