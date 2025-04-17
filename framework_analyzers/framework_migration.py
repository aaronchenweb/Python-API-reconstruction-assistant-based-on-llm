"""
框架遷移幫助工具 - 提供跨 Web 框架的遷移工具和建議
"""
import ast
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any

from code_analyzer.ast_parser import analyze_python_file
from framework_analyzers.django_analyzer import DjangoAnalyzer
from framework_analyzers.fastapi_analyzer import FastAPIAnalyzer
from framework_analyzers.flask_analyzer import FlaskAnalyzer
from utils.file_operations import read_file
from api_analyzer.endpoint_analyzer import EndpointAnalyzer


class FrameworkMigrationHelper:
    """提供跨 Web 框架的遷移工具和建議"""
    
    def __init__(self, project_path: str, source_framework: str, target_framework: str):
        """
        初始化框架遷移幫助工具
        
        Args:
            project_path: API 專案的路徑
            source_framework: 源框架 (django, flask, fastapi)
            target_framework: 目標框架 (django, flask, fastapi)
        """
        self.project_path = project_path
        self.source_framework = source_framework.lower()
        self.target_framework = target_framework.lower()
        self.endpoints = []
        self.models = []
        
    def analyze_project(self) -> Dict[str, Any]:
        """
        分析專案以獲取遷移信息
        
        Returns:
            包含遷移信息的字典
        """
        # 使用 EndpointAnalyzer 獲取端點
        endpoint_analyzer = EndpointAnalyzer(self.project_path)
        
        # 如果未指定源框架，則檢測框架
        if not self.source_framework or self.source_framework == 'unknown':
            self.source_framework = endpoint_analyzer.detect_framework()
        
        # 獲取端點
        self.endpoints = endpoint_analyzer.analyze_endpoints()
        
        # 根據源框架採用不同的分析方法
        if self.source_framework == 'django':
            from .django_analyzer import DjangoAnalyzer
            analyzer = DjangoAnalyzer(self.project_path)
            return self._analyze_django_to_x(analyzer)
        elif self.source_framework == 'flask':
            from .flask_analyzer import FlaskAnalyzer
            analyzer = FlaskAnalyzer(self.project_path)
            return self._analyze_flask_to_x(analyzer)
        elif self.source_framework == 'fastapi':
            from .fastapi_analyzer import FastAPIAnalyzer
            analyzer = FastAPIAnalyzer(self.project_path)
            return self._analyze_fastapi_to_x(analyzer)
        else:
            return {
                'error': f"不支援的源框架: {self.source_framework}",
                'supported_frameworks': ['django', 'flask', 'fastapi']
            }
    
    def _analyze_django_to_x(self, analyzer: 'DjangoAnalyzer') -> Dict[str, Any]:
        """
        分析從 Django 遷移到其他框架的信息
        
        Args:
            analyzer: Django 分析器
            
        Returns:
            遷移信息字典
        """
        # 獲取 Django 專案結構
        project_structure = analyzer.detect_project_structure()
        
        # 分析視圖
        views = analyzer.analyze_views()
        
        # 分析 DRF ViewSets
        uses_drf = project_structure.get('rest_framework', False)
        viewsets = []
        serializers = []
        
        if uses_drf:
            viewsets = analyzer.analyze_drf_viewsets()
            serializers = analyzer.analyze_serializers()
        
        # 計算遷移複雜度和挑戰
        migration_complexity = self._calculate_django_migration_complexity(
            project_structure, views, viewsets, serializers
        )
        
        # 生成特定於目標框架的遷移建議
        migration_suggestions = self._generate_django_migration_suggestions(
            project_structure, views, viewsets, serializers
        )
        
        return {
            'source_framework': 'django',
            'target_framework': self.target_framework,
            'project_structure': project_structure,
            'views_count': len(views),
            'viewsets_count': len(viewsets),
            'serializers_count': len(serializers),
            'uses_drf': uses_drf,
            'endpoints_count': len(self.endpoints),
            'migration_complexity': migration_complexity,
            'migration_suggestions': migration_suggestions
        }
    
    def _calculate_django_migration_complexity(
        self, 
        project_structure: Dict[str, Any], 
        views: List[Dict[str, Any]], 
        viewsets: List[Dict[str, Any]], 
        serializers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        計算從 Django 遷移的複雜度
        
        Args:
            project_structure: Django 專案結構
            views: Django 視圖列表
            viewsets: Django REST Framework ViewSets 列表
            serializers: Django REST Framework Serializers 列表
            
        Returns:
            複雜度分數和挑戰
        """
        complexity = {
            'score': 0,  # 0-10，越高越複雜
            'factors': [],
            'challenges': []
        }
        
        # 基礎複雜度
        base_complexity = 5
        complexity['score'] = base_complexity
        
        # 複雜性因素
        
        # 1. 使用 Django REST Framework - 增加複雜度
        if project_structure.get('rest_framework', False):
            complexity['score'] += 1
            complexity['factors'].append('使用 Django REST Framework')
        
        # 2. 大量視圖 - 增加複雜度
        if len(views) > 20:
            complexity['score'] += 1
            complexity['factors'].append(f'大量視圖 ({len(views)})')
        
        # 3. 使用了類視圖 - 減少複雜度（對 FastAPI 遷移更容易）
        class_based_views = [view for view in views if view.get('type') == 'class_view']
        if len(class_based_views) > len(views) / 2:
            if self.target_framework == 'fastapi':
                complexity['score'] -= 1
                complexity['factors'].append('主要使用類視圖，更易於遷移到 FastAPI')
        
        # 4. 大量 ViewSets - 增加複雜度
        if len(viewsets) > 10:
            complexity['score'] += 1
            complexity['factors'].append(f'大量 ViewSets ({len(viewsets)})')
        
        # 5. 自定義中間件 - 增加複雜度
        if len(project_structure.get('middlewares', [])) > 5:
            complexity['score'] += 1
            complexity['factors'].append('大量自定義中間件')
        
        # 遷移挑戰
        
        # 1. ORM 遷移
        complexity['challenges'].append({
            'type': 'orm_migration',
            'description': '需要從 Django ORM 遷移到目標框架的 ORM',
            'difficulty': 'high'
        })
        
        # 2. 身份驗證系統遷移
        complexity['challenges'].append({
            'type': 'auth_migration',
            'description': '需要重新實現 Django 身份驗證和權限系統',
            'difficulty': 'high'
        })
        
        # 3. 模板系統遷移（如果使用）
        if project_structure.get('templates_dir'):
            complexity['challenges'].append({
                'type': 'template_migration',
                'description': '需要從 Django 模板系統遷移到目標框架的模板系統',
                'difficulty': 'medium'
            })
        
        # 4. Admin 界面遷移（如果使用）
        if project_structure.get('admin_apps'):
            complexity['challenges'].append({
                'type': 'admin_migration',
                'description': '需要為 Django Admin 功能找到替代方案',
                'difficulty': 'high'
            })
        
        # 5. DRF 序列化器遷移（如果使用）
        if serializers:
            complexity['challenges'].append({
                'type': 'serializer_migration',
                'description': '需要從 DRF 序列化器遷移到目標框架的數據驗證系統',
                'difficulty': 'medium'
            })
        
        # 確保分數在 0-10 範圍內
        complexity['score'] = max(0, min(10, complexity['score']))
        
        return complexity
    
    def _generate_django_migration_suggestions(
        self, 
        project_structure: Dict[str, Any], 
        views: List[Dict[str, Any]], 
        viewsets: List[Dict[str, Any]], 
        serializers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成從 Django 遷移的建議
        
        Args:
            project_structure: Django 專案結構
            views: Django 視圖列表
            viewsets: Django REST Framework ViewSets 列表
            serializers: Django REST Framework Serializers 列表
            
        Returns:
            遷移建議列表
        """
        suggestions = []
        
        # 根據目標框架生成建議
        if self.target_framework == 'flask':
            # Django 到 Flask 的建議
            suggestions.append({
                'title': 'URL 模式遷移',
                'description': '將 Django URL 配置轉換為 Flask 路由裝飾器',
                'guidance': [
                    'Django URL 模式使用正則表達式可以轉換為 Flask 的路由格式',
                    '例如: `/users/<int:user_id>/` 變為 `/users/<int:user_id>`',
                    '在 Flask 中，路由直接裝飾視圖函數'
                ]
            })
            
            suggestions.append({
                'title': 'ORM 遷移',
                'description': '從 Django ORM 遷移到 SQLAlchemy',
                'guidance': [
                    'Django 模型可以轉換為 SQLAlchemy 模型',
                    'Django 的 ForeignKey 對應 SQLAlchemy 的 relationship',
                    '需要使用 SQLAlchemy 會話而非 Django 查詢管理器',
                    '考慮使用 Flask-SQLAlchemy 擴展簡化整合'
                ]
            })
            
            suggestions.append({
                'title': '身份驗證系統遷移',
                'description': '從 Django 身份驗證遷移到 Flask-Login',
                'guidance': [
                    'Flask-Login 提供用戶會話管理',
                    'Django 的 @login_required 裝飾器對應 Flask-Login 的同名裝飾器',
                    '需要實現自己的 UserMixin 類',
                    '對於更複雜的權限控制，考慮 Flask-Principal'
                ]
            })
            
            if project_structure.get('templates_dir'):
                suggestions.append({
                    'title': '模板系統遷移',
                    'description': '從 Django 模板遷移到 Jinja2',
                    'guidance': [
                        'Flask 默認使用 Jinja2，與 Django 模板語法類似',
                        '需要調整 Django 特定的模板標籤和過濾器',
                        'Django 的 {% csrf_token %} 在 Flask 中需要使用 WTForms 實現'
                    ]
                })
            
            if project_structure.get('rest_framework', False):
                suggestions.append({
                    'title': 'API 開發遷移',
                    'description': '從 Django REST Framework 遷移到 Flask RESTful',
                    'guidance': [
                        'Flask-RESTful 提供類似 DRF 的資源類',
                        'DRF 的序列化器可以轉換為 Flask-Marshmallow 結構',
                        'ViewSets 可以轉換為 Flask-RESTful 的 Resource 類'
                    ]
                })
        
        elif self.target_framework == 'fastapi':
            # Django 到 FastAPI 的建議
            suggestions.append({
                'title': '路由系統遷移',
                'description': '將 Django URL 配置轉換為 FastAPI 路由裝飾器',
                'guidance': [
                    '使用 FastAPI 的路徑參數取代 Django URL 模式',
                    '例如: `/users/<int:user_id>/` 變為 `/users/{user_id}`',
                    'FastAPI 路由裝飾器直接指定 HTTP 方法和路徑'
                ]
            })
            
            suggestions.append({
                'title': 'ORM 遷移',
                'description': '從 Django ORM 遷移到 SQLAlchemy',
                'guidance': [
                    'Django 模型可以轉換為 SQLAlchemy 模型',
                    '使用 SQLAlchemy 的異步功能與 FastAPI 配合',
                    '考慮使用 FastAPI 的依賴注入系統管理數據庫會話'
                ]
            })
            
            suggestions.append({
                'title': '參數驗證遷移',
                'description': '從 Django 表單/DRF 遷移到 Pydantic 模型',
                'guidance': [
                    'Pydantic 模型可以替代 Django 表單和 DRF 序列化器',
                    'FastAPI 自動解析並驗證輸入數據',
                    'Pydantic 支援比 Django 表單更豐富的類型註解'
                ]
            })
            
            suggestions.append({
                'title': '身份驗證系統遷移',
                'description': '從 Django 身份驗證遷移到 FastAPI 安全依賴',
                'guidance': [
                    'FastAPI 提供多種安全依賴選項（OAuth2、JWT、API 密鑰等）',
                    '使用 FastAPI 的依賴注入系統實現身份驗證',
                    '身份驗證可以使用 Depends 函數實現'
                ]
            })
            
            if project_structure.get('rest_framework', False):
                suggestions.append({
                    'title': 'API 開發遷移',
                    'description': '從 Django REST Framework 遷移到 FastAPI',
                    'guidance': [
                        'FastAPI 本身就是為 API 開發設計的，不需要額外的框架',
                        'DRF 的序列化器可以轉換為 Pydantic 模型',
                        'DRF 的 ViewSets 可以轉換為 FastAPI 的依賴注入和路由'
                    ]
                })
        
        return suggestions
    
    def _analyze_flask_to_x(self, analyzer: 'FlaskAnalyzer') -> Dict[str, Any]:
        """
        分析從 Flask 遷移到其他框架的信息
        
        Args:
            analyzer: Flask 分析器
            
        Returns:
            遷移信息字典
        """
        # 獲取 Flask 專案結構
        project_structure = analyzer.detect_project_structure()
        
        # 分析路由
        routes = analyzer.analyze_routes()
        
        # 分析視圖函數
        view_functions = analyzer.analyze_view_functions()
        
        # 分析藍圖
        blueprints = analyzer.analyze_blueprints()
        
        # 分析擴展
        extensions = analyzer.analyze_extensions()
        
        # 計算遷移複雜度和挑戰
        migration_complexity = self._calculate_flask_migration_complexity(
            project_structure, routes, view_functions, blueprints, extensions
        )
        
        # 生成特定於目標框架的遷移建議
        migration_suggestions = self._generate_flask_migration_suggestions(
            project_structure, routes, view_functions, blueprints, extensions
        )
        
        return {
            'source_framework': 'flask',
            'target_framework': self.target_framework,
            'project_structure': project_structure,
            'routes_count': len(routes),
            'view_functions_count': len(view_functions),
            'blueprints_count': len(blueprints),
            'extensions_count': len(extensions),
            'endpoints_count': len(self.endpoints),
            'migration_complexity': migration_complexity,
            'migration_suggestions': migration_suggestions
        }
    
    def _calculate_flask_migration_complexity(
        self, 
        project_structure: Dict[str, Any], 
        routes: List[Dict[str, Any]], 
        view_functions: List[Dict[str, Any]], 
        blueprints: List[Dict[str, Any]], 
        extensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        計算從 Flask 遷移的複雜度
        
        Args:
            project_structure: Flask 專案結構
            routes: Flask 路由列表
            view_functions: Flask 視圖函數列表
            blueprints: Flask 藍圖列表
            extensions: Flask 擴展列表
            
        Returns:
            複雜度分數和挑戰
        """
        complexity = {
            'score': 0,  # 0-10，越高越複雜
            'factors': [],
            'challenges': []
        }
        
        # 基礎複雜度
        base_complexity = 4  # Flask 作為一個微框架，通常比 Django 更容易遷移
        complexity['score'] = base_complexity
        
        # 複雜性因素
        
        # 1. 大量路由 - 增加複雜度
        if len(routes) > 20:
            complexity['score'] += 1
            complexity['factors'].append(f'大量路由 ({len(routes)})')
        
        # 2. 使用藍圖 - 視目標框架可能增加或減少複雜度
        if blueprints:
            if self.target_framework == 'fastapi':
                complexity['score'] += 0.5
                complexity['factors'].append('使用藍圖，需要轉換為 FastAPI 的 APIRouter')
            elif self.target_framework == 'django':
                complexity['score'] += 1
                complexity['factors'].append('使用藍圖，需要重組為 Django 的應用結構')
        
        # 3. 使用工廠模式 - 減少複雜度（更加模塊化）
        if project_structure.get('is_factory_pattern', False):
            complexity['score'] -= 0.5
            complexity['factors'].append('使用應用工廠模式，更易於模塊化遷移')
        
        # 4. 大量擴展 - 增加複雜度
        if len(extensions) > 5:
            complexity['score'] += 1
            complexity['factors'].append(f'使用多個 Flask 擴展 ({len(extensions)})')
        
        # 5. 依賴於特定 Flask 擴展 - 增加複雜度
        extension_types = [ext.get('type', '') for ext in extensions]
        complex_extensions = ['Login', 'Admin', 'RestPlus', 'Security']
        
        for ext_type in complex_extensions:
            if any(ext_type in ext for ext in extension_types):
                complexity['score'] += 0.5
                complexity['factors'].append(f'使用複雜的 Flask 擴展: {ext_type}')
        
        # 遷移挑戰
        
        # 1. 模板系統遷移（如果使用）
        if project_structure.get('templates_dir'):
            challenge_level = 'low' if self.target_framework == 'django' else 'medium'
            complexity['challenges'].append({
                'type': 'template_migration',
                'description': '從 Jinja2 模板遷移到目標框架的模板系統',
                'difficulty': challenge_level
            })
        
        # 2. ORM 遷移（如果使用 SQLAlchemy）
        if any('SQLAlchemy' in ext.get('type', '') for ext in extensions):
            if self.target_framework == 'django':
                complexity['challenges'].append({
                    'type': 'orm_migration',
                    'description': '從 SQLAlchemy 遷移到 Django ORM',
                    'difficulty': 'high'
                })
            elif self.target_framework == 'fastapi':
                complexity['challenges'].append({
                    'type': 'orm_migration',
                    'description': '從 SQLAlchemy 遷移到 SQLAlchemy (異步版本)',
                    'difficulty': 'low'
                })
        
        # 3. 身份驗證系統遷移
        if any(auth in ext.get('type', '') for ext in extensions for auth in ['Login', 'Security', 'JWT']):
            complexity['challenges'].append({
                'type': 'auth_migration',
                'description': '從 Flask 身份驗證擴展遷移到目標框架的身份驗證系統',
                'difficulty': 'medium'
            })
        
        # 4. 路由系統遷移
        complexity['challenges'].append({
            'type': 'routing_migration',
            'description': '從 Flask 路由裝飾器遷移到目標框架的路由系統',
            'difficulty': 'low'
        })
        
        # 5. 藍圖/模塊化結構遷移
        if blueprints:
            complexity['challenges'].append({
                'type': 'blueprint_migration',
                'description': '從 Flask 藍圖遷移到目標框架的模塊化系統',
                'difficulty': 'medium'
            })
        
        # 確保分數在 0-10 範圍內
        complexity['score'] = max(0, min(10, complexity['score']))
        
        return complexity
    
    def _generate_flask_migration_suggestions(
        self, 
        project_structure: Dict[str, Any], 
        routes: List[Dict[str, Any]], 
        view_functions: List[Dict[str, Any]], 
        blueprints: List[Dict[str, Any]], 
        extensions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成從 Flask 遷移的建議
        
        Args:
            project_structure: Flask 專案結構
            routes: Flask 路由列表
            view_functions: Flask 視圖函數列表
            blueprints: Flask 藍圖列表
            extensions: Flask 擴展列表
            
        Returns:
            遷移建議列表
        """
        suggestions = []
        
        # 根據目標框架生成建議
        if self.target_framework == 'django':
            # Flask 到 Django 的建議
            suggestions.append({
                'title': '路由系統遷移',
                'description': '將 Flask 路由裝飾器轉換為 Django URL 配置',
                'guidance': [
                    'Flask 路由需要移至 Django 的 urls.py 檔案',
                    '路由參數格式需要調整（例如 `/users/<int:user_id>` 變為 `/users/<int:user_id>/`）',
                    '創建適當的 Django 視圖函數或類'
                ]
            })
            
            suggestions.append({
                'title': '專案結構重組',
                'description': '將 Flask 應用重組為 Django 專案結構',
                'guidance': [
                    '創建 Django 專案和應用',
                    '將 Flask 藍圖轉換為 Django 應用',
                    '設置 Django 的 settings.py',
                    '遵循 Django 的 MTV (Model-Template-View) 模式'
                ]
            })
            
            # 檢查是否使用 SQLAlchemy
            if any('SQLAlchemy' in ext.get('type', '') for ext in extensions):
                suggestions.append({
                    'title': 'ORM 遷移',
                    'description': '從 SQLAlchemy 遷移到 Django ORM',
                    'guidance': [
                        '將 SQLAlchemy 模型轉換為 Django 模型',
                        '使用 Django 的遷移系統管理數據庫結構',
                        '調整查詢語法從 SQLAlchemy 到 Django ORM'
                    ]
                })
            
            # 檢查是否使用 Jinja2 模板
            if project_structure.get('templates_dir'):
                suggestions.append({
                    'title': '模板系統遷移',
                    'description': '從 Jinja2 遷移到 Django 模板',
                    'guidance': [
                        'Django 模板語法與 Jinja2 類似但有差異',
                        '調整變量訪問和過濾器語法',
                        '使用 Django 的模板標籤和過濾器'
                    ]
                })
            
            # 檢查是否使用身份驗證
            if any(auth in ext.get('type', '') for ext in extensions for auth in ['Login', 'Security', 'JWT']):
                suggestions.append({
                    'title': '身份驗證系統遷移',
                    'description': '從 Flask 身份驗證擴展遷移到 Django 身份驗證',
                    'guidance': [
                        '使用 Django 的內置用戶模型和身份驗證系統',
                        '轉換 Flask-Login 裝飾器為 Django 的 @login_required',
                        '使用 Django 的會話和中間件'
                    ]
                })
        
        elif self.target_framework == 'fastapi':
            # Flask 到 FastAPI 的建議
            suggestions.append({
                'title': '路由系統遷移',
                'description': '將 Flask 路由裝飾器轉換為 FastAPI 路由裝飾器',
                'guidance': [
                    'Flask 路由語法與 FastAPI 類似，但路徑參數格式不同',
                    '調整路徑參數格式（例如 `/users/<int:user_id>` 變為 `/users/{user_id}`）',
                    'FastAPI 路由裝飾器同時指定 HTTP 方法'
                ]
            })
            
            suggestions.append({
                'title': '參數驗證遷移',
                'description': '使用 Pydantic 模型進行參數驗證',
                'guidance': [
                    'Flask 的請求解析轉換為 FastAPI 的 Pydantic 模型',
                    'request.form 和 request.args 轉換為函數參數',
                    '利用 FastAPI 的自動數據驗證'
                ]
            })
            
            # 檢查是否使用 SQLAlchemy
            if any('SQLAlchemy' in ext.get('type', '') for ext in extensions):
                suggestions.append({
                    'title': 'ORM 遷移',
                    'description': '從 Flask-SQLAlchemy 遷移到 FastAPI 中的 SQLAlchemy',
                    'guidance': [
                        '使用 SQLAlchemy 的異步功能',
                        '使用 FastAPI 的依賴注入管理數據庫會話',
                        '調整查詢語法以支援非同步操作'
                    ]
                })
            
            suggestions.append({
                'title': '異步轉換',
                'description': '將 Flask 同步視圖轉換為 FastAPI 異步函數',
                'guidance': [
                    '使用 async/await 語法改寫視圖函數',
                    '確保所有 I/O 操作（如數據庫查詢）都是非同步的',
                    '使用適當的異步庫替代同步庫'
                ]
            })
            
            # 檢查是否使用藍圖
            if blueprints:
                suggestions.append({
                    'title': '藍圖遷移',
                    'description': '將 Flask 藍圖轉換為 FastAPI 路由器',
                    'guidance': [
                        'Flask 藍圖可以轉換為 FastAPI 的 APIRouter',
                        '將藍圖的路由轉換為 APIRouter 的路由',
                        '使用 include_router 註冊路由器'
                    ]
                })
        
        return suggestions
    
    def _analyze_fastapi_to_x(self, analyzer: 'FastAPIAnalyzer') -> Dict[str, Any]:
        """
        分析從 FastAPI 遷移到其他框架的信息
        
        Args:
            analyzer: FastAPI 分析器
            
        Returns:
            遷移信息字典
        """
        # 獲取 FastAPI 專案結構
        project_structure = analyzer.detect_project_structure()
        
        # 分析端點
        endpoints = analyzer.analyze_endpoints()
        
        # 分析 Pydantic 模型
        models = analyzer.analyze_pydantic_models()
        
        # 分析依賴項
        dependencies = analyzer.analyze_dependencies()
        
        # 分析路由器
        routers = analyzer.analyze_routers()
        
        # 計算遷移複雜度和挑戰
        migration_complexity = self._calculate_fastapi_migration_complexity(
            project_structure, endpoints, models, dependencies, routers
        )
        
        # 生成特定於目標框架的遷移建議
        migration_suggestions = self._generate_fastapi_migration_suggestions(
            project_structure, endpoints, models, dependencies, routers
        )
        
        return {
            'source_framework': 'fastapi',
            'target_framework': self.target_framework,
            'project_structure': project_structure,
            'endpoints_count': len(endpoints),
            'pydantic_models_count': len(models),
            'dependencies_count': len(dependencies),
            'routers_count': len(routers),
            'migration_complexity': migration_complexity,
            'migration_suggestions': migration_suggestions
        }
    
    def _calculate_fastapi_migration_complexity(
        self, 
        project_structure: Dict[str, Any], 
        endpoints: List[Dict[str, Any]], 
        models: List[Dict[str, Any]], 
        dependencies: List[Dict[str, Any]], 
        routers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        計算從 FastAPI 遷移的複雜度
        
        Args:
            project_structure: FastAPI 專案結構
            endpoints: FastAPI 端點列表
            models: Pydantic 模型列表
            dependencies: 依賴項列表
            routers: 路由器列表
            
        Returns:
            複雜度分數和挑戰
        """
        complexity = {
            'score': 0,  # 0-10，越高越複雜
            'factors': [],
            'challenges': []
        }
        
        # 基礎複雜度
        base_complexity = 5
        complexity['score'] = base_complexity
        
        # 複雜性因素
        
        # 1. 大量端點 - 增加複雜度
        if len(endpoints) > 20:
            complexity['score'] += 1
            complexity['factors'].append(f'大量端點 ({len(endpoints)})')
        
        # 2. 使用依賴注入 - 增加複雜度
        if dependencies:
            complexity['score'] += 1
            complexity['factors'].append('大量使用依賴注入')
        
        # 3. 異步端點 - 增加複雜度
        async_endpoints = sum(1 for endpoint in endpoints if 'async' in str(endpoint.get('view', '')))
        if async_endpoints > len(endpoints) / 2:
            complexity['score'] += 1
            complexity['factors'].append('主要使用異步端點')
        
        # 4. 複雜的 Pydantic 模型 - 增加複雜度
        complex_models = [model for model in models if len(model.get('fields', [])) > 10]
        if complex_models:
            complexity['score'] += 0.5
            complexity['factors'].append('複雜的 Pydantic 模型結構')
        
        # 5. 使用路由器 - 視目標框架可能增加或減少複雜度
        if routers:
            if self.target_framework == 'django':
                complexity['score'] += 0.5
                complexity['factors'].append('使用路由器，需要轉換為 Django 應用')
            elif self.target_framework == 'flask':
                complexity['score'] += 0.5
                complexity['factors'].append('使用路由器，需要轉換為 Flask 藍圖')
        
        # 遷移挑戰
        
        # 1. 同步/異步轉換
        complexity['challenges'].append({
            'type': 'async_conversion',
            'description': '從 FastAPI 的異步模型轉換為目標框架的同步或異步模型',
            'difficulty': 'high'
        })
        
        # 2. 參數驗證系統
        complexity['challenges'].append({
            'type': 'validation_migration',
            'description': '從 Pydantic 模型遷移到目標框架的驗證系統',
            'difficulty': 'medium'
        })
        
        # 3. 依賴注入系統
        if dependencies:
            complexity['challenges'].append({
                'type': 'dependency_injection_migration',
                'description': '從 FastAPI 的依賴注入系統遷移到目標框架的替代方案',
                'difficulty': 'high'
            })
        
        # 4. ORM 遷移（如果使用 SQLAlchemy）
        if project_structure.get('uses_sqlalchemy', False):
            if self.target_framework == 'django':
                complexity['challenges'].append({
                    'type': 'orm_migration',
                    'description': '從 SQLAlchemy 遷移到 Django ORM',
                    'difficulty': 'high'
                })
            elif self.target_framework == 'flask':
                complexity['challenges'].append({
                    'type': 'orm_migration',
                    'description': '從 SQLAlchemy (異步) 遷移到 SQLAlchemy (同步)',
                    'difficulty': 'low'
                })
        
        # 5. 路由系統遷移
        complexity['challenges'].append({
            'type': 'routing_migration',
            'description': '從 FastAPI 路由系統遷移到目標框架的路由系統',
            'difficulty': 'medium'
        })
        
        # 確保分數在 0-10 範圍內
        complexity['score'] = max(0, min(10, complexity['score']))
        
        return complexity
    
    def _generate_fastapi_migration_suggestions(
        self, 
        project_structure: Dict[str, Any], 
        endpoints: List[Dict[str, Any]], 
        models: List[Dict[str, Any]], 
        dependencies: List[Dict[str, Any]], 
        routers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成從 FastAPI 遷移的建議
        
        Args:
            project_structure: FastAPI 專案結構
            endpoints: FastAPI 端點列表
            models: Pydantic 模型列表
            dependencies: 依賴項列表
            routers: 路由器列表
            
        Returns:
            遷移建議列表
        """
        suggestions = []
        
        # 根據目標框架生成建議
        if self.target_framework == 'django':
            # FastAPI 到 Django 的建議
            suggestions.append({
                'title': '路由系統遷移',
                'description': '將 FastAPI 路由裝飾器轉換為 Django URL 配置',
                'guidance': [
                    'FastAPI 路由需要移至 Django 的 urls.py 檔案',
                    '路徑參數格式需要調整（例如 `/users/{user_id}` 變為 `/users/<int:user_id>/`）',
                    '創建適當的 Django 視圖函數或類'
                ]
            })
            
            suggestions.append({
                'title': '專案結構重組',
                'description': '將 FastAPI 應用重組為 Django 專案結構',
                'guidance': [
                    '創建 Django 專案和應用',
                    '將 FastAPI 路由器轉換為 Django 應用',
                    '設置 Django 的 settings.py',
                    '遵循 Django 的 MTV (Model-Template-View) 模式'
                ]
            })
            
            suggestions.append({
                'title': '模型系統遷移',
                'description': '從 Pydantic 模型遷移到 Django 模型和表單',
                'guidance': [
                    '將 Pydantic 模型轉換為 Django 模型（用於持久化）',
                    '將 Pydantic 模型轉換為 Django 表單（用於驗證）',
                    '使用 Django REST Framework 序列化器替代 Pydantic 模型（用於 API）'
                ]
            })
            
            suggestions.append({
                'title': '同步轉換',
                'description': '將 FastAPI 異步函數轉換為 Django 同步視圖',
                'guidance': [
                    '移除 async/await 語法',
                    '使用同步替代方案替代異步庫',
                    '在必要時使用 Django 的 asgiref 庫進行異步/同步轉換'
                ]
            })
            
            suggestions.append({
                'title': '依賴注入轉換',
                'description': '從 FastAPI 依賴注入系統轉換為 Django 替代方案',
                'guidance': [
                    '使用 Django 中間件替代某些依賴項',
                    '使用 Django 裝飾器替代其他依賴項',
                    '為複雜的依賴邏輯創建輔助函數'
                ]
            })
            
            if project_structure.get('uses_sqlalchemy', False):
                suggestions.append({
                    'title': 'ORM 遷移',
                    'description': '從 SQLAlchemy 遷移到 Django ORM',
                    'guidance': [
                        '重新定義數據模型為 Django 模型',
                        '使用 Django 的遷移系統',
                        '將 SQLAlchemy 查詢轉換為 Django ORM 查詢'
                    ]
                })
            
        elif self.target_framework == 'flask':
            # FastAPI 到 Flask 的建議
            suggestions.append({
                'title': '路由系統遷移',
                'description': '將 FastAPI 路由裝飾器轉換為 Flask 路由裝飾器',
                'guidance': [
                    'FastAPI 路由語法與 Flask 類似，但路徑參數格式不同',
                    '調整路徑參數格式（例如 `/users/{user_id}` 變為 `/users/<int:user_id>`）',
                    'Flask 需要單獨指定 HTTP 方法'
                ]
            })
            
            suggestions.append({
                'title': '參數驗證遷移',
                'description': '從 Pydantic 模型遷移到 Flask 表單驗證',
                'guidance': [
                    '使用 Flask-WTF 或 Marshmallow 替代 Pydantic',
                    '手動處理請求解析和驗證',
                    '使用 Flask 的 request 對象獲取數據'
                ]
            })
            
            suggestions.append({
                'title': '同步轉換',
                'description': '將 FastAPI 異步函數轉換為 Flask 同步視圖',
                'guidance': [
                    '移除 async/await 語法',
                    '使用同步替代方案替代異步庫',
                    '對於需要保持異步的部分，考慮使用 Flask 2.0 的異步支援'
                ]
            })
            
            suggestions.append({
                'title': '路由器遷移',
                'description': '將 FastAPI 路由器轉換為 Flask 藍圖',
                'guidance': [
                    'FastAPI 的 APIRouter 對應 Flask 的 Blueprint',
                    '調整路由註冊語法',
                    '保持相同的路由前綴和參數'
                ]
            })
            
            suggestions.append({
                'title': '依賴注入轉換',
                'description': '從 FastAPI 依賴注入系統轉換為 Flask 替代方案',
                'guidance': [
                    '使用 Flask 裝飾器實現部分依賴項',
                    '使用 Flask 的 g 對象和請求鉤子',
                    '為複雜的依賴邏輯創建輔助函數'
                ]
            })
            
            if project_structure.get('uses_sqlalchemy', False):
                suggestions.append({
                    'title': 'ORM 遷移',
                    'description': '從 SQLAlchemy (異步) 遷移到 Flask-SQLAlchemy',
                    'guidance': [
                        '使用 Flask-SQLAlchemy 擴展',
                        '將異步查詢轉換為同步查詢',
                        '調整數據庫會話管理模式'
                    ]
                })
        
        return suggestions
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """
        生成完整的遷移報告
        
        Returns:
            遷移報告字典
        """
        # 分析專案
        analysis_result = self.analyze_project()
        
        # 生成遷移總結
        migration_summary = {
            'source_framework': self.source_framework,
            'target_framework': self.target_framework,
            'complexity_score': analysis_result.get('migration_complexity', {}).get('score', 0),
            'key_challenges': [challenge['description'] for challenge in analysis_result.get('migration_complexity', {}).get('challenges', [])[:3]],
            'endpoints_count': analysis_result.get('endpoints_count', 0),
            'estimated_effort': self._estimate_migration_effort(analysis_result)
        }
        
        # 合併結果
        return {
            'summary': migration_summary,
            'analysis': analysis_result,
            'migration_plan': self._generate_migration_plan(analysis_result)
        }
    
    def _estimate_migration_effort(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        估算遷移工作量
        
        Args:
            analysis_result: 分析結果
            
        Returns:
            工作量估算
        """
        # 取得複雜度分數
        complexity_score = analysis_result.get('migration_complexity', {}).get('score', 0)
        endpoints_count = analysis_result.get('endpoints_count', 0)
        
        # 基於端點數量和複雜度分數估算工作天數
        # 這是一個簡化的估算，實際情況可能因專案而異
        base_days = endpoints_count * 0.5  # 每個端點平均 0.5 天
        complexity_factor = complexity_score / 5  # 複雜度因子 (0-2)
        
        estimated_days = base_days * (1 + complexity_factor)
        
        # 估算人員需求
        if estimated_days < 10:
            team_size = 1
        elif estimated_days < 30:
            team_size = 2
        else:
            team_size = 3
        
        return {
            'estimated_days': round(estimated_days),
            'suggested_team_size': team_size,
            'complexity_level': 'Low' if complexity_score < 4 else 'Medium' if complexity_score < 7 else 'High'
        }
    
    def _generate_migration_plan(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成遷移計劃
        
        Args:
            analysis_result: 分析結果
            
        Returns:
            遷移計劃
        """
        # 獲取建議
        suggestions = analysis_result.get('migration_suggestions', [])
        
        # 組織為分階段計劃
        phases = [
            {
                'name': '分析和準備',
                'description': '細化需求、設置目標框架環境、建立測試策略',
                'tasks': [
                    '安裝並配置目標框架',
                    '建立新專案結構',
                    '確定端點、模型和測試需求',
                    '準備測試環境和測試數據'
                ],
                'estimated_completion': '10%'
            },
            {
                'name': '核心結構遷移',
                'description': '遷移專案結構、路由系統和基礎模型',
                'tasks': [
                    '設置基本專案結構',
                    f'將 {self.source_framework} 的路由系統遷移到 {self.target_framework}',
                    '遷移數據模型定義',
                    '實現最基本的端點功能'
                ],
                'estimated_completion': '30%'
            },
            {
                'name': '功能實現',
                'description': '遷移業務邏輯、驗證和依賴項',
                'tasks': []
            },
            {
                'name': '測試和修復',
                'description': '執行端到端測試，解決問題',
                'tasks': [
                    '執行單元測試',
                    '執行整合測試',
                    '檢查性能和安全性',
                    '修復發現的問題'
                ],
                'estimated_completion': '90%'
            },
            {
                'name': '部署和文檔',
                'description': '完成部署配置和文檔',
                'tasks': [
                    '更新部署腳本和配置',
                    '撰寫文檔',
                    '建立監控和日誌系統',
                    '完成最終部署'
                ],
                'estimated_completion': '100%'
            }
        ]
        
        # 根據建議添加功能實現任務
        implementation_tasks = []
        
        for suggestion in suggestions:
            task = f"{suggestion.get('title', '')}: {suggestion.get('description', '')}"
            implementation_tasks.append(task)
        
        if not implementation_tasks:
            # 添加一些一般任務
            implementation_tasks = [
                f'從 {self.source_framework} 遷移業務邏輯到 {self.target_framework}',
                '遷移資料驗證系統',
                '遷移身份驗證和授權系統',
                '遷移錯誤處理機制',
                '遷移中間件/攔截器功能'
            ]
        
        # 添加到第三階段
        phases[2]['tasks'] = implementation_tasks
        phases[2]['estimated_completion'] = '70%'
        
        return {
            'phases': phases,
            'suggested_approach': 'incremental' if analysis_result.get('endpoints_count', 0) > 10 else 'complete',
            'key_risks': self._identify_migration_risks(analysis_result),
            'testing_strategy': self._suggest_testing_strategy(analysis_result)
        }
    
    def _identify_migration_risks(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        識別遷移風險
        
        Args:
            analysis_result: 分析結果
            
        Returns:
            風險列表
        """
        risks = []
        
        # 基於遷移挑戰識別風險
        challenges = analysis_result.get('migration_complexity', {}).get('challenges', [])
        
        for challenge in challenges:
            if challenge.get('difficulty') == 'high':
                risks.append({
                    'risk': challenge.get('description', ''),
                    'impact': 'High',
                    'mitigation': f"分配更多資源到 {challenge.get('type', '')} 的遷移，並提前進行概念驗證測試。"
                })
        
        # 添加一些通用風險
        generic_risks = [
            {
                'risk': '未覆蓋的邊緣案例可能導致生產環境問題',
                'impact': 'Medium',
                'mitigation': '確保全面的測試覆蓋率，包括正常和錯誤情況的測試。'
            },
            {
                'risk': '遷移期間系統不可用',
                'impact': 'High',
                'mitigation': '計劃分階段遷移，確保舊系統可以繼續運行直到新系統完全測試通過。'
            },
            {
                'risk': '性能下降',
                'impact': 'Medium',
                'mitigation': '在遷移過程中進行性能測試，確保新系統至少與舊系統相當。'
            }
        ]
        
        # 合併風險
        risks.extend(generic_risks)
        
        return risks
    
    def _suggest_testing_strategy(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        建議測試策略
        
        Args:
            analysis_result: 分析結果
            
        Returns:
            測試策略
        """
        # 基於專案規模和複雜度建議測試策略
        endpoints_count = analysis_result.get('endpoints_count', 0)
        complexity_score = analysis_result.get('migration_complexity', {}).get('score', 0)
        
        # 端點測試優先級
        high_priority_percentage = 30
        medium_priority_percentage = 40
        low_priority_percentage = 30
        
        # 根據複雜度調整
        if complexity_score > 7:
            high_priority_percentage = 50
            medium_priority_percentage = 30
            low_priority_percentage = 20
        
        # 計算各優先級的端點數量
        high_priority_count = int(endpoints_count * high_priority_percentage / 100)
        medium_priority_count = int(endpoints_count * medium_priority_percentage / 100)
        low_priority_count = endpoints_count - high_priority_count - medium_priority_count
        
        return {
            'unit_testing': {
                'coverage_target': '80%',
                'focus_areas': [
                    '業務邏輯函數',
                    '數據驗證',
                    '複雜的計算和轉換'
                ]
            },
            'integration_testing': {
                'coverage_target': '90%',
                'focus_areas': [
                    'API 端點',
                    '數據庫交互',
                    '身份驗證和授權流程'
                ]
            },
            'endpoint_testing': {
                'high_priority': high_priority_count,
                'medium_priority': medium_priority_count,
                'low_priority': low_priority_count,
                'strategy': 'Prioritize testing critical endpoints first (e.g. authentication, core business logic), then medium and low priority endpoints.'
            },
            'performance_testing': {
                'needed': complexity_score > 5,
                'target_metrics': [
                    '響應時間不超過原系統的 1.2 倍',
                    '在峰值負載下系統穩定',
                    '資源使用率在可接受範圍內'
                ]
            }
        }