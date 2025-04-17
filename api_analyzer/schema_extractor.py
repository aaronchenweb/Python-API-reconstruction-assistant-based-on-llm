"""
模式提取器 - 從 API 程式碼中識別和提取數據模型和結構
"""
import ast
import os
import re
from typing import Dict, List, Set, Optional, Any

from code_analyzer.ast_parser import analyze_python_file
from utils.file_operations import read_file


class SchemaExtractor:
    """從 API 程式碼中提取數據模型和結構"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化模式提取器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.models = []
        self.schemas = []
        
    def extract_models(self) -> List[Dict[str, Any]]:
        """
        從專案中提取數據模型/結構
        
        Returns:
            數據模型資訊的列表
        """
        if not self.framework:
            from .endpoint_analyzer import EndpointAnalyzer
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
        
        # 根據框架選擇適當的提取方法
        if self.framework == 'django':
            self._extract_django_models()
        elif self.framework == 'fastapi':
            self._extract_fastapi_models()
        elif self.framework == 'flask':
            self._extract_flask_sqlalchemy_models()
        
        # 通用模型提取（作為後備）
        if not self.models:
            self._extract_generic_models()
            
        return self.models
    
    def _extract_django_models(self) -> None:
        """提取 Django 模型類別"""
        # 尋找 models.py 文件
        model_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'models.py':
                    model_files.append(os.path.join(root, file))
        
        for model_file in model_files:
            content = read_file(model_file)
            
            try:
                tree = ast.parse(content)
                
                # 尋找繼承自 models.Model 的類別
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # 檢查基類是否包含 models.Model
                        inherits_model = False
                        for base in node.bases:
                            if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                                if base.value.id == 'models' and base.attr == 'Model':
                                    inherits_model = True
                        
                        if inherits_model:
                            # 提取模型欄位
                            fields = []
                            for item in node.body:
                                if isinstance(item, ast.Assign):
                                    for target in item.targets:
                                        if isinstance(target, ast.Name):
                                            field_name = target.id
                                            field_type = None
                                            field_args = []
                                            
                                            # 檢查欄位類型
                                            if isinstance(item.value, ast.Call):
                                                if isinstance(item.value.func, ast.Attribute) and \
                                                   isinstance(item.value.func.value, ast.Name) and \
                                                   item.value.func.value.id == 'models':
                                                    field_type = item.value.func.attr
                                                
                                                # 提取字段參數
                                                for keyword in item.value.keywords:
                                                    if isinstance(keyword.value, ast.Constant):
                                                        field_args.append({
                                                            'name': keyword.arg,
                                                            'value': keyword.value.value
                                                        })
                                            
                                            if field_type:
                                                fields.append({
                                                    'name': field_name,
                                                    'type': field_type,
                                                    'args': field_args
                                                })
                            
                            # 提取模型元資料
                            meta_fields = {}
                            for item in node.body:
                                if isinstance(item, ast.ClassDef) and item.name == 'Meta':
                                    for meta_item in item.body:
                                        if isinstance(meta_item, ast.Assign):
                                            for target in meta_item.targets:
                                                if isinstance(target, ast.Name):
                                                    meta_name = target.id
                                                    
                                                    # 處理不同類型的元數據值
                                                    if isinstance(meta_item.value, ast.Constant):
                                                        meta_fields[meta_name] = meta_item.value.value
                                                    elif isinstance(meta_item.value, ast.List):
                                                        meta_fields[meta_name] = [
                                                            elt.value if isinstance(elt, ast.Constant) else None
                                                            for elt in meta_item.value.elts
                                                        ]
                            
                            # 添加模型到列表
                            self.models.append({
                                'name': node.name,
                                'type': 'django.model',
                                'fields': fields,
                                'meta': meta_fields,
                                'file': model_file,
                                'line': node.lineno
                            })
            except SyntaxError:
                continue
    
    def _extract_fastapi_models(self) -> None:
        """提取 FastAPI Pydantic 模型"""
        # 搜尋 schemas.py 或任何 Python 文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否導入 pydantic
                    if 'pydantic' not in content.lower():
                        continue
                    
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找繼承自 pydantic.BaseModel 的類別
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                # 檢查基類
                                is_pydantic_model = False
                                for base in node.bases:
                                    if isinstance(base, ast.Attribute):
                                        if isinstance(base.value, ast.Name) and base.value.id == 'pydantic' and base.attr == 'BaseModel':
                                            is_pydantic_model = True
                                    elif isinstance(base, ast.Name) and base.id == 'BaseModel':
                                        # 也檢查直接導入的 BaseModel
                                        is_pydantic_model = True
                                
                                if is_pydantic_model:
                                    # 提取欄位
                                    fields = []
                                    for item in node.body:
                                        if isinstance(item, ast.AnnAssign):
                                            if isinstance(item.target, ast.Name):
                                                field_name = item.target.id
                                                
                                                # 獲取類型註解
                                                field_type = None
                                                if isinstance(item.annotation, ast.Name):
                                                    field_type = item.annotation.id
                                                elif isinstance(item.annotation, ast.Subscript):
                                                    if isinstance(item.annotation.value, ast.Name):
                                                        field_type = f"{item.annotation.value.id}[...]"
                                                
                                                # 獲取默認值
                                                default_value = None
                                                if item.value:
                                                    if isinstance(item.value, ast.Constant):
                                                        default_value = item.value.value
                                                    elif isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                                                        default_value = f"{item.value.func.id}(...)"
                                                
                                                if field_name:
                                                    fields.append({
                                                        'name': field_name,
                                                        'type': field_type,
                                                        'default': default_value
                                                    })
                                    
                                    # 添加模型到列表
                                    self.models.append({
                                        'name': node.name,
                                        'type': 'pydantic.model',
                                        'fields': fields,
                                        'file': file_path,
                                        'line': node.lineno
                                    })
                    except SyntaxError:
                        continue
    
    def _extract_flask_sqlalchemy_models(self) -> None:
        """提取 Flask SQLAlchemy 模型"""
        # 搜尋潛在的模型文件
        model_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否包含 SQLAlchemy
                    if 'sqlalchemy' not in content.lower() and 'db.Model' not in content:
                        continue
                    
                    model_files.append(file_path)
        
        for model_file in model_files:
            content = read_file(model_file)
            
            try:
                tree = ast.parse(content)
                
                # 尋找定義 db 變數的地方
                db_var_name = 'db'
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                                if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'SQLAlchemy':
                                    db_var_name = target.id
                
                # 尋找繼承自 db.Model 的類別
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # 檢查基類是否包含 db.Model
                        inherits_db_model = False
                        for base in node.bases:
                            if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                                if base.value.id == db_var_name and base.attr == 'Model':
                                    inherits_db_model = True
                        
                        if inherits_db_model:
                            # 提取模型欄位
                            fields = []
                            for item in node.body:
                                if isinstance(item, ast.Assign):
                                    for target in item.targets:
                                        if isinstance(target, ast.Name):
                                            field_name = target.id
                                            field_type = None
                                            field_args = []
                                            
                                            # 檢查欄位類型
                                            if isinstance(item.value, ast.Call):
                                                if isinstance(item.value.func, ast.Attribute) and \
                                                   isinstance(item.value.func.value, ast.Name) and \
                                                   (item.value.func.value.id == 'db' or 'Column' in item.value.func.attr):
                                                    field_type = item.value.func.attr
                                                    
                                                    # 提取列參數
                                                    for arg in item.value.args:
                                                        if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):
                                                            field_args.append({
                                                                'type': arg.func.attr
                                                            })
                                                    
                                                    for keyword in item.value.keywords:
                                                        field_args.append({
                                                            'name': keyword.arg,
                                                            'value': keyword.value
                                                        })
                                            
                                            if field_type:
                                                fields.append({
                                                    'name': field_name,
                                                    'type': field_type,
                                                    'args': field_args
                                                })
                            
                            # 添加模型到列表
                            self.models.append({
                                'name': node.name,
                                'type': 'sqlalchemy.model',
                                'fields': fields,
                                'file': model_file,
                                'line': node.lineno
                            })
            except SyntaxError:
                continue
    
    def _extract_generic_models(self) -> None:
        """通用模型提取方法（作為後備）"""
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # 跳過已經處理過的文件
                    if any(model['file'] == file_path for model in self.models):
                        continue
                    
                    content = read_file(file_path)
                    
                    # 使用啟發式方法識別可能的模型
                    # 例如，檢查包含常見資料庫相關屬性的類別
                    model_indicators = ['id', 'created_at', 'updated_at', 'pk', 'primary_key']
                    
                    try:
                        tree = ast.parse(content)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                # 檢查類別是否有模型指標
                                has_indicators = False
                                fields = []
                                
                                for item in node.body:
                                    # 檢查欄位分配
                                    if isinstance(item, ast.Assign):
                                        for target in item.targets:
                                            if isinstance(target, ast.Name):
                                                field_name = target.id
                                                if field_name in model_indicators:
                                                    has_indicators = True
                                                
                                                # 添加到欄位列表
                                                fields.append({
                                                    'name': field_name,
                                                    'type': 'unknown'
                                                })
                                    
                                    # 檢查類型註解分配
                                    elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                        field_name = item.target.id
                                        if field_name in model_indicators:
                                            has_indicators = True
                                        
                                        # 獲取類型註解
                                        field_type = None
                                        if isinstance(item.annotation, ast.Name):
                                            field_type = item.annotation.id
                                        
                                        fields.append({
                                            'name': field_name,
                                            'type': field_type if field_type else 'unknown'
                                        })
                                
                                # 如果有足夠的指標，將其添加為潛在模型
                                if has_indicators and len(fields) >= 2:
                                    self.models.append({
                                        'name': node.name,
                                        'type': 'potential.model',
                                        'fields': fields,
                                        'file': file_path,
                                        'line': node.lineno,
                                        'confidence': 'low'  # 表示這是一個啟發式檢測
                                    })
                    except SyntaxError:
                        continue
    
    def extract_model_relationships(self) -> List[Dict[str, Any]]:
        """
        識別模型之間的關係
        
        Returns:
            模型關係列表
        """
        relationships = []
        
        # 確保先提取模型
        if not self.models:
            self.extract_models()
        
        # 尋找外鍵和關係
        for model in self.models:
            model_name = model['name']
            model_type = model['type']
            
            if model_type == 'django.model':
                # 檢查 Django ForeignKey, OneToOneField, ManyToManyField
                for field in model['fields']:
                    field_type = field.get('type', '')
                    if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
                        # 尋找關係的目標模型
                        target_model = None
                        for arg in field.get('args', []):
                            if arg.get('name') == 'to':
                                target_model = arg.get('value')
                        
                        if target_model:
                            relationships.append({
                                'source_model': model_name,
                                'target_model': target_model,
                                'field_name': field['name'],
                                'relationship_type': field_type,
                                'framework': 'django'
                            })
            
            elif model_type == 'sqlalchemy.model':
                # 檢查 SQLAlchemy 關係
                for field in model['fields']:
                    args = field.get('args', [])
                    is_relationship = any('ForeignKey' in str(arg) for arg in args) or \
                                     any('relationship' in str(arg) for arg in args)
                    
                    if is_relationship:
                        # 尋找關係的目標模型（這需要更深入的分析）
                        relationships.append({
                            'source_model': model_name,
                            'field_name': field['name'],
                            'relationship_type': 'SQLAlchemy Relationship',
                            'framework': 'flask'
                        })
        
        return relationships
    
    def get_schema_metrics(self) -> Dict[str, Any]:
        """
        計算模式相關指標
        
        Returns:
            含有模式指標的字典
        """
        if not self.models:
            self.extract_models()
            
        # 計算總模型數
        total_models = len(self.models)
        
        # 按類型分類模型
        model_types = {}
        for model in self.models:
            model_type = model['type']
            model_types[model_type] = model_types.get(model_type, 0) + 1
        
        # 計算平均欄位數
        total_fields = sum(len(model.get('fields', [])) for model in self.models)
        avg_fields_per_model = total_fields / total_models if total_models > 0 else 0
        
        # 識別複雜模型（有很多欄位的模型）
        complex_models = []
        for model in self.models:
            fields_count = len(model.get('fields', []))
            if fields_count > 10:  # 超過 10 個欄位的定義為複雜
                complex_models.append({
                    'name': model['name'],
                    'fields_count': fields_count,
                    'file': model.get('file', '')
                })
        
        # 提取關係
        relationships = self.extract_model_relationships()
        
        return {
            'total_models': total_models,
            'model_types': model_types,
            'avg_fields_per_model': avg_fields_per_model,
            'complex_models': complex_models,
            'relationships_count': len(relationships),
            'framework': self.framework
        }