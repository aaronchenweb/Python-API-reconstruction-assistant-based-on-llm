"""
Django 分析器 - 提供 Django 專案專門的分析功能
"""
import ast
import os
import re
import json
from typing import Dict, List, Set, Tuple, Optional, Any

from code_analyzer.ast_parser import analyze_python_file
from utils.file_operations import read_file
from api_analyzer.endpoint_analyzer import EndpointAnalyzer


class DjangoAnalyzer:
    """提供 Django 專案專門的分析功能"""
    
    def __init__(self, project_path: str):
        """
        初始化 Django 分析器
        
        Args:
            project_path: Django 專案的路徑
        """
        self.project_path = project_path
        self.project_structure = None
        
    def detect_project_structure(self) -> Dict[str, Any]:
        """
        檢測 Django 專案結構
        
        Returns:
            包含專案結構資訊的字典
        """
        # 初始化結構資訊
        structure = {
            'has_manage_py': False,
            'settings_module': None,
            'apps': [],
            'urls': [],
            'middlewares': [],
            'templates_dir': None,
            'static_dir': None,
            'rest_framework': False,
            'admin_apps': []
        }
        
        # 檢查 manage.py
        manage_py_path = os.path.join(self.project_path, 'manage.py')
        if os.path.exists(manage_py_path):
            structure['has_manage_py'] = True
            
            # 嘗試從 manage.py 中獲取設置模組
            content = read_file(manage_py_path)
            settings_match = re.search(r'os.environ.setdefault\([\'"]DJANGO_SETTINGS_MODULE[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]\)', content)
            if settings_match:
                structure['settings_module'] = settings_match.group(1)
        
        # 尋找設置文件
        settings_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'settings.py':
                    settings_files.append(os.path.join(root, file))
        
        # 分析設置文件
        if settings_files:
            settings_file = settings_files[0]  # 使用第一個找到的設置文件
            
            content = read_file(settings_file)
            
            # 查找已安裝的應用
            installed_apps_match = re.search(r'INSTALLED_APPS\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
            if installed_apps_match:
                apps_str = installed_apps_match.group(1)
                # 提取應用名稱
                app_pattern = re.compile(r'[\'"]([^\'"]+)[\'"]')
                apps = app_pattern.findall(apps_str)
                structure['apps'] = apps
                
                # 檢查是否使用 Django REST Framework
                structure['rest_framework'] = 'rest_framework' in apps
                
                # 檢查 admin 應用
                structure['admin_apps'] = [app for app in apps if 'admin' in app.lower()]
            
            # 查找中間件
            middlewares_match = re.search(r'MIDDLEWARE(?:_CLASSES)?\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
            if middlewares_match:
                middlewares_str = middlewares_match.group(1)
                # 提取中間件名稱
                middleware_pattern = re.compile(r'[\'"]([^\'"]+)[\'"]')
                middlewares = middleware_pattern.findall(middlewares_str)
                structure['middlewares'] = middlewares
            
            # 查找模板目錄
            templates_match = re.search(r'TEMPLATES\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
            if templates_match:
                templates_str = templates_match.group(1)
                dirs_match = re.search(r'DIRS\s*:\s*\[([^\]]+)\]', templates_str, re.DOTALL)
                if dirs_match:
                    dirs_str = dirs_match.group(1)
                    # 提取目錄名
                    dir_pattern = re.compile(r'[\'"]([^\'"]+)[\'"]')
                    dirs = dir_pattern.findall(dirs_str)
                    if dirs:
                        structure['templates_dir'] = dirs
            
            # 查找靜態文件目錄
            static_match = re.search(r'STATIC_ROOT\s*=\s*[\'"]([^\'"]+)[\'"]', content)
            if static_match:
                structure['static_dir'] = static_match.group(1)
        
        # 查找 URL 配置文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'urls.py':
                    structure['urls'].append(os.path.join(root, file))
        
        self.project_structure = structure
        return structure
    
    def analyze_views(self) -> List[Dict[str, Any]]:
        """
        分析 Django 視圖
        
        Returns:
            包含視圖資訊的列表
        """
        views = []
        
        # 查找視圖文件
        view_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'views.py' or 'view' in file.lower():
                    view_files.append(os.path.join(root, file))
        
        # 分析每個視圖文件
        for file_path in view_files:
            content = read_file(file_path)
            
            try:
                tree = ast.parse(content)
                
                # 尋找函數視圖
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # 檢查是否是視圖函數
                        is_view = False
                        
                        # 檢查參數
                        for arg in node.args.args:
                            if arg.arg == 'request':
                                is_view = True
                                break
                        
                        # 檢查裝飾器
                        for decorator in node.decorator_list:
                            if isinstance(decorator, ast.Name) and decorator.id in ['login_required', 'permission_required']:
                                is_view = True
                            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id in ['login_required', 'permission_required']:
                                is_view = True
                        
                        if is_view:
                            view_info = {
                                'name': node.name,
                                'type': 'function_view',
                                'file': file_path,
                                'line': node.lineno,
                                'docstring': ast.get_docstring(node) or ""
                            }
                            views.append(view_info)
                
                # 尋找類視圖
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # 檢查基類是否包含視圖相關名稱
                        is_view_class = False
                        view_base_classes = []
                        
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                base_name = base.id
                                if 'View' in base_name:
                                    is_view_class = True
                                    view_base_classes.append(base_name)
                            elif isinstance(base, ast.Attribute):
                                if isinstance(base.value, ast.Name):
                                    base_name = f"{base.value.id}.{base.attr}"
                                    if 'View' in base.attr:
                                        is_view_class = True
                                        view_base_classes.append(base_name)
                        
                        if is_view_class:
                            # 收集類方法
                            methods = []
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    methods.append({
                                        'name': item.name,
                                        'docstring': ast.get_docstring(item) or ""
                                    })
                            
                            view_info = {
                                'name': node.name,
                                'type': 'class_view',
                                'base_classes': view_base_classes,
                                'methods': methods,
                                'file': file_path,
                                'line': node.lineno,
                                'docstring': ast.get_docstring(node) or ""
                            }
                            views.append(view_info)
            except SyntaxError:
                continue
        
        return views
    
    def analyze_drf_viewsets(self) -> List[Dict[str, Any]]:
        """
        分析 Django REST Framework ViewSets
        
        Returns:
            包含 ViewSet 資訊的列表
        """
        viewsets = []
        
        # 查找 ViewSet 文件
        viewset_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                # 常見的 ViewSet 文件名
                if file == 'viewsets.py' or file == 'views.py' or 'api' in file.lower():
                    viewset_files.append(os.path.join(root, file))
        
        # 分析每個文件
        for file_path in viewset_files:
            content = read_file(file_path)
            
            # 檢查是否使用 DRF
            if 'rest_framework' not in content:
                continue
                
            try:
                tree = ast.parse(content)
                
                # 尋找 ViewSet 類
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # 檢查基類是否包含 ViewSet
                        is_viewset = False
                        base_classes = []
                        
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                base_name = base.id
                                base_classes.append(base_name)
                                if 'ViewSet' in base_name or 'ModelViewSet' in base_name:
                                    is_viewset = True
                            elif isinstance(base, ast.Attribute):
                                if isinstance(base.value, ast.Name):
                                    base_name = f"{base.value.id}.{base.attr}"
                                    base_classes.append(base_name)
                                    if 'ViewSet' in base.attr or 'ModelViewSet' in base.attr:
                                        is_viewset = True
                        
                        if is_viewset:
                            # 尋找序列化器類
                            serializer_class = None
                            for item in node.body:
                                if isinstance(item, ast.Assign):
                                    for target in item.targets:
                                        if isinstance(target, ast.Name) and target.id == 'serializer_class':
                                            if isinstance(item.value, ast.Name):
                                                serializer_class = item.value.id
                            
                            # 收集 ViewSet 方法
                            methods = []
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef):
                                    methods.append({
                                        'name': item.name,
                                        'docstring': ast.get_docstring(item) or ""
                                    })
                            
                            viewset_info = {
                                'name': node.name,
                                'base_classes': base_classes,
                                'serializer_class': serializer_class,
                                'methods': methods,
                                'file': file_path,
                                'line': node.lineno,
                                'docstring': ast.get_docstring(node) or ""
                            }
                            viewsets.append(viewset_info)
            except SyntaxError:
                continue
        
        return viewsets
    
    def analyze_serializers(self) -> List[Dict[str, Any]]:
        """
        分析 Django REST Framework Serializers
        
        Returns:
            包含序列化器資訊的列表
        """
        serializers = []
        
        # 查找序列化器文件
        serializer_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'serializers.py' or 'serializer' in file.lower():
                    serializer_files.append(os.path.join(root, file))
        
        # 分析每個文件
        for file_path in serializer_files:
            content = read_file(file_path)
            
            # 檢查是否使用 DRF
            if 'rest_framework' not in content:
                continue
                
            try:
                tree = ast.parse(content)
                
                # 尋找序列化器類
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # 檢查基類是否包含 Serializer
                        is_serializer = False
                        base_classes = []
                        
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                base_name = base.id
                                base_classes.append(base_name)
                                if 'Serializer' in base_name:
                                    is_serializer = True
                            elif isinstance(base, ast.Attribute):
                                if isinstance(base.value, ast.Name):
                                    base_name = f"{base.value.id}.{base.attr}"
                                    base_classes.append(base_name)
                                    if 'Serializer' in base.attr:
                                        is_serializer = True
                        
                        if is_serializer:
                            # 提取欄位
                            fields = []
                            meta_info = {}
                            
                            for item in node.body:
                                # 提取欄位
                                if isinstance(item, ast.Assign):
                                    for target in item.targets:
                                        if isinstance(target, ast.Name):
                                            field_name = target.id
                                            
                                            # 檢查是否是序列化器欄位
                                            if isinstance(item.value, ast.Call):
                                                field_type = None
                                                
                                                if isinstance(item.value.func, ast.Name):
                                                    field_type = item.value.func.id
                                                elif isinstance(item.value.func, ast.Attribute):
                                                    if isinstance(item.value.func.value, ast.Name):
                                                        field_type = f"{item.value.func.value.id}.{item.value.func.attr}"
                                                
                                                if field_type and 'Field' in field_type:
                                                    fields.append({
                                                        'name': field_name,
                                                        'type': field_type,
                                                        'line': item.lineno
                                                    })
                                
                                # 提取 Meta 類
                                elif isinstance(item, ast.ClassDef) and item.name == 'Meta':
                                    for meta_item in item.body:
                                        if isinstance(meta_item, ast.Assign):
                                            for target in meta_item.targets:
                                                if isinstance(target, ast.Name):
                                                    meta_name = target.id
                                                    
                                                    # 處理 model
                                                    if meta_name == 'model' and isinstance(meta_item.value, ast.Name):
                                                        meta_info['model'] = meta_item.value.id
                                                    
                                                    # 處理 fields
                                                    elif meta_name == 'fields':
                                                        if isinstance(meta_item.value, ast.List):
                                                            meta_fields = []
                                                            for elt in meta_item.value.elts:
                                                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                                                    meta_fields.append(elt.value)
                                                            meta_info['fields'] = meta_fields
                                                        elif isinstance(meta_item.value, ast.Constant) and meta_item.value.value == '__all__':
                                                            meta_info['fields'] = '__all__'
                            
                            serializer_info = {
                                'name': node.name,
                                'base_classes': base_classes,
                                'fields': fields,
                                'meta': meta_info,
                                'file': file_path,
                                'line': node.lineno,
                                'docstring': ast.get_docstring(node) or ""
                            }
                            serializers.append(serializer_info)
            except SyntaxError:
                continue
        
        return serializers
    
    def get_django_metrics(self) -> Dict[str, Any]:
        """
        獲取 Django 專案指標
        
        Returns:
            包含專案指標的字典
        """
        # 確保已分析專案結構
        if not self.project_structure:
            self.detect_project_structure()
        
        # 分析 URL 模式
        url_patterns = self._analyze_url_patterns()
        
        # 分析視圖
        views = self.analyze_views()
        
        # 分析 ViewSets 和序列化器（如果使用 DRF）
        drf_used = self.project_structure.get('rest_framework', False)
        viewsets = []
        serializers = []
        
        if drf_used:
            viewsets = self.analyze_drf_viewsets()
            serializers = self.analyze_serializers()
        
        # 計算指標
        return {
            'apps_count': len(self.project_structure.get('apps', [])),
            'url_patterns_count': len(url_patterns),
            'views_count': len(views),
            'class_based_views_count': sum(1 for view in views if view.get('type') == 'class_view'),
            'function_based_views_count': sum(1 for view in views if view.get('type') == 'function_view'),
            'uses_drf': drf_used,
            'viewsets_count': len(viewsets),
            'serializers_count': len(serializers),
            'middleware_count': len(self.project_structure.get('middlewares', []))
        }
    
    def _analyze_url_patterns(self) -> List[Dict[str, Any]]:
        """
        分析 URL 模式
        
        Returns:
            包含 URL 模式信息的列表
        """
        url_patterns = []
        
        # 使用 EndpointAnalyzer 獲取端點
        endpoint_analyzer = EndpointAnalyzer(self.project_path)
        endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 將端點轉換為 URL 模式
        for endpoint in endpoints:
            if endpoint.get('framework') == 'django':
                pattern = {
                    'path': endpoint.get('path', ''),
                    'view': endpoint.get('view', ''),
                    'name': endpoint.get('name', ''),
                    'file': endpoint.get('file', '')
                }
                url_patterns.append(pattern)
        
        return url_patterns