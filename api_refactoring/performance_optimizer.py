"""
API 性能優化器 - 識別和解決 API 性能問題
"""
import ast
import os
import re
from typing import Dict, List, Tuple, Optional, Any

from utils.file_operations import read_file, write_file
from code_analyzer.ast_parser import analyze_python_file


class APIPerformanceOptimizer:
    """識別和解決 API 性能問題"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化 API 性能優化器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        
        # 如果未指定框架，則檢測框架
        if not self.framework:
            from api_analyzer.endpoint_analyzer import EndpointAnalyzer
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
    
    def analyze_api_performance(self) -> Dict[str, Any]:
        """
        分析 API 性能
        
        Returns:
            性能分析結果
        """
        # 初始化分析結果
        analysis_result = {
            'issues': [],
            'hotspots': [],
            'database_issues': [],
            'caching_opportunities': [],
            'overall_score': 0
        }
        
        # 分析常見的性能問題
        self._analyze_n_plus_one_queries(analysis_result)
        self._analyze_bulk_operations(analysis_result)
        self._analyze_serialization(analysis_result)
        self._analyze_pagination(analysis_result)
        self._analyze_response_size(analysis_result)
        
        # 計算總體性能分數
        analysis_result['overall_score'] = self._calculate_performance_score(analysis_result)
        
        return analysis_result
    
    def _analyze_n_plus_one_queries(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析 N+1 查詢問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 根據框架使用不同的檢測方法
        if self.framework == 'django':
            self._detect_django_n_plus_one(analysis_result)
        elif self.framework == 'flask':
            self._detect_flask_n_plus_one(analysis_result)
        elif self.framework == 'fastapi':
            self._detect_fastapi_n_plus_one(analysis_result)
    
    def _detect_django_n_plus_one(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 Django 中的 N+1 查詢問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 搜索視圖文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py') and ('view' in file.lower() or 'viewset' in file.lower()):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否有循環中進行查詢的模式
                    loop_query_patterns = [
                        (r'for\s+\w+\s+in\s+.*?:\s*.*?\.objects', 'for 循環中使用 .objects 查詢'),
                        (r'for\s+\w+\s+in\s+.*?:\s*.*?\.filter', 'for 循環中使用 .filter 查詢'),
                        (r'for\s+\w+\s+in\s+.*?:\s*.*?\.get\(', 'for 循環中使用 .get() 查詢')
                    ]
                    
                    for pattern, description in loop_query_patterns:
                        matches = re.findall(pattern, content, re.DOTALL)
                        if matches:
                            analysis_result['database_issues'].append({
                                'type': 'n_plus_one',
                                'file': file_path,
                                'description': description,
                                'solution': '使用 select_related 或 prefetch_related 提前獲取關聯數據',
                                'severity': 'high'
                            })
                    
                    # 檢查是否缺少 select_related 或 prefetch_related
                    if 'ForeignKey' in content or 'ManyToManyField' in content:
                        if 'objects.all()' in content and not ('select_related' in content or 'prefetch_related' in content):
                            analysis_result['database_issues'].append({
                                'type': 'missing_related_prefetch',
                                'file': file_path,
                                'description': '使用 ForeignKey 或 ManyToManyField 但未使用 select_related/prefetch_related',
                                'solution': '使用 select_related 或 prefetch_related 優化關聯查詢',
                                'severity': 'medium'
                            })
    
    def _detect_flask_n_plus_one(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 Flask 中的 N+1 查詢問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 搜索視圖文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 如果不使用 SQLAlchemy，則跳過
                    if 'sqlalchemy' not in content.lower():
                        continue
                    
                    # 檢查是否有循環中進行查詢的模式
                    loop_query_patterns = [
                        (r'for\s+\w+\s+in\s+.*?:\s*.*?\.query', 'for 循環中使用 SQLAlchemy 查詢'),
                        (r'for\s+\w+\s+in\s+.*?:\s*.*?session\.query', 'for 循環中使用 session.query'),
                        (r'for\s+\w+\s+in\s+.*?:\s*.*?\.get\(', 'for 循環中使用 .get() 查詢')
                    ]
                    
                    for pattern, description in loop_query_patterns:
                        matches = re.findall(pattern, content, re.DOTALL)
                        if matches:
                            analysis_result['database_issues'].append({
                                'type': 'n_plus_one',
                                'file': file_path,
                                'description': description,
                                'solution': '使用 joinedload 或 subqueryload 提前獲取關聯數據',
                                'severity': 'high'
                            })
                    
                    # 檢查是否缺少 joinedload
                    if 'relationship' in content:
                        if ('query(' in content or 'query.' in content) and 'joinedload' not in content and 'subqueryload' not in content:
                            analysis_result['database_issues'].append({
                                'type': 'missing_joined_load',
                                'file': file_path,
                                'description': '使用關聯關係但未使用 joinedload 或 subqueryload',
                                'solution': '使用 joinedload 或 subqueryload 優化關聯查詢',
                                'severity': 'medium'
                            })
    
    def _detect_fastapi_n_plus_one(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 FastAPI 中的 N+1 查詢問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # FastAPI 通常使用 SQLAlchemy，所以檢測方法類似 Flask
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 如果不使用 SQLAlchemy，則跳過
                    if 'sqlalchemy' not in content.lower():
                        continue
                    
                    # 檢查 async 函數中的循環查詢
                    loop_query_patterns = [
                        (r'async\s+def.*?for\s+\w+\s+in\s+.*?:\s*.*?await\s+.*?\.get\(', 'async 函數的 for 循環中使用 await .get()'),
                        (r'async\s+def.*?for\s+\w+\s+in\s+.*?:\s*.*?await\s+db\.', 'async 函數的 for 循環中使用數據庫查詢')
                    ]
                    
                    for pattern, description in loop_query_patterns:
                        matches = re.findall(pattern, content, re.DOTALL)
                        if matches:
                            analysis_result['database_issues'].append({
                                'type': 'async_n_plus_one',
                                'file': file_path,
                                'description': description,
                                'solution': '使用 selectinload 或批次查詢優化異步查詢',
                                'severity': 'high'
                            })
    
    def _analyze_bulk_operations(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析批量操作機會
        
        Args:
            analysis_result: 分析結果字典
        """
        # 根據框架分析批量操作
        if self.framework == 'django':
            self._detect_django_bulk_opportunities(analysis_result)
        elif self.framework == 'flask' or self.framework == 'fastapi':
            self._detect_sqlalchemy_bulk_opportunities(analysis_result)
    
    def _detect_django_bulk_opportunities(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 Django 中的批量操作機會
        
        Args:
            analysis_result: 分析結果字典
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查循環中的個別創建或更新
                    multiple_create_pattern = r'for\s+\w+\s+in\s+.*?:\s*.*?\.objects\.create\('
                    individual_save_pattern = r'for\s+\w+\s+in\s+.*?:\s*.*?\.save\('
                    
                    if re.search(multiple_create_pattern, content, re.DOTALL):
                        analysis_result['database_issues'].append({
                            'type': 'individual_creates',
                            'file': file_path,
                            'description': '循環中使用個別的 .objects.create() 而非批量操作',
                            'solution': '使用 bulk_create() 代替循環中的單獨創建',
                            'severity': 'medium',
                            'code_example': '''
# 優化前:
for item in items:
    Model.objects.create(field1=item.value1, field2=item.value2)

# 優化後:
objects_to_create = [Model(field1=item.value1, field2=item.value2) for item in items]
Model.objects.bulk_create(objects_to_create)
'''
                        })
                    
                    if re.search(individual_save_pattern, content, re.DOTALL):
                        analysis_result['database_issues'].append({
                            'type': 'individual_saves',
                            'file': file_path,
                            'description': '循環中使用個別的 .save() 而非批量操作',
                            'solution': '使用 bulk_update() 代替循環中的單獨更新',
                            'severity': 'medium',
                            'code_example': '''
# 優化前:
for obj in objects:
    obj.field = new_value
    obj.save()

# 優化後:
for obj in objects:
    obj.field = new_value
Model.objects.bulk_update(objects, ['field'])
'''
                        })
    
    def _detect_sqlalchemy_bulk_opportunities(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 SQLAlchemy 中的批量操作機會
        
        Args:
            analysis_result: 分析結果字典
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 如果不使用 SQLAlchemy，則跳過
                    if 'sqlalchemy' not in content.lower():
                        continue
                    
                    # 檢查循環中的個別添加或提交
                    individual_add_pattern = r'for\s+\w+\s+in\s+.*?:\s*.*?session\.add\('
                    multiple_flush_pattern = r'for\s+\w+\s+in\s+.*?:\s*.*?session\.flush\('
                    multiple_commit_pattern = r'for\s+\w+\s+in\s+.*?:\s*.*?session\.commit\('
                    
                    if re.search(individual_add_pattern, content, re.DOTALL):
                        analysis_result['database_issues'].append({
                            'type': 'individual_adds',
                            'file': file_path,
                            'description': '循環中使用個別的 session.add() 操作',
                            'solution': '在循環外執行一次 session.add_all() 和 session.commit()',
                            'severity': 'medium',
                            'code_example': '''
# 優化前:
for item in items:
    new_obj = Model(field1=item.value1, field2=item.value2)
    session.add(new_obj)
    session.commit()

# 優化後:
objects_to_add = [Model(field1=item.value1, field2=item.value2) for item in items]
session.add_all(objects_to_add)
session.commit()
'''
                        })
                    
                    if re.search(multiple_flush_pattern, content, re.DOTALL) or re.search(multiple_commit_pattern, content, re.DOTALL):
                        analysis_result['database_issues'].append({
                            'type': 'multiple_commits',
                            'file': file_path,
                            'description': '循環中執行多次 flush/commit 操作',
                            'solution': '在循環外批量執行一次 commit',
                            'severity': 'high',
                            'code_example': '''
# 優化前:
for item in items:
    new_obj = Model(field1=item.value1, field2=item.value2)
    session.add(new_obj)
    session.commit()  # 每次迭代都提交事務

# 優化後:
for item in items:
    new_obj = Model(field1=item.value1, field2=item.value2)
    session.add(new_obj)
session.commit()  # 循環結束後執行一次提交
'''
                        })
    
    def _analyze_serialization(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析序列化性能問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 根據框架分析序列化問題
        if self.framework == 'django':
            self._detect_django_serialization_issues(analysis_result)
        elif self.framework == 'fastapi':
            self._detect_fastapi_serialization_issues(analysis_result)
        # Flask 沒有標準的序列化方法，所以不做特定檢查
    
    def _detect_django_serialization_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 Django 中的序列化問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 尋找序列化器文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py') and ('serializer' in file.lower() or 'viewset' in file.lower()):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否使用 DRF 序列化器
                    if 'rest_framework' in content and 'Serializer' in content:
                        # 檢查 depth 參數使用
                        if 'depth = ' in content:
                            analysis_result['issues'].append({
                                'type': 'serializer_depth',
                                'file': file_path,
                                'description': '使用序列化器的 depth 參數可能導致過度序列化',
                                'solution': '考慮使用嵌套序列化器並明確指定要包含的欄位，而非使用通用 depth',
                                'severity': 'medium'
                            })
                        
                        # 檢查是否使用了 SerializerMethodField 但沒有緩存結果
                        if 'SerializerMethodField' in content and '@cached_property' not in content:
                            analysis_result['issues'].append({
                                'type': 'uncached_method_field',
                                'file': file_path,
                                'description': '使用 SerializerMethodField 但沒有緩存計算結果',
                                'solution': '考慮使用 @cached_property 裝飾器緩存 get_* 方法的結果',
                                'severity': 'low',
                                'code_example': '''
# 優化前:
def get_calculated_field(self, obj):
    # 執行複雜計算
    return complex_calculation(obj)

# 優化後:
@cached_property
def get_calculated_field(self, obj):
    # 執行複雜計算
    return complex_calculation(obj)
'''
                            })
                        
                        # 檢查是否有不必要的序列化欄位
                        if 'fields = ' in content and "'__all__'" in content:
                            analysis_result['issues'].append({
                                'type': 'excessive_serialization',
                                'file': file_path,
                                'description': '使用 fields = "__all__" 可能導致過度序列化，包含不必要的欄位',
                                'solution': '明確指定僅需要的欄位列表，而非使用 "__all__"',
                                'severity': 'medium',
                                'code_example': '''
# 優化前:
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

# 優化後:
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']  # 只包含必要欄位
'''
                            })
    
    def _detect_fastapi_serialization_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 FastAPI 中的序列化問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 尋找 Pydantic 模型文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否使用 Pydantic
                    if 'pydantic' in content and 'BaseModel' in content:
                        # 檢查是否有複雜的計算屬性但沒有緩存
                        property_pattern = r'@property\s+def\s+\w+\s*\([^)]*\):\s*(?!.*?\bcached\b)'
                        if re.search(property_pattern, content, re.DOTALL):
                            analysis_result['issues'].append({
                                'type': 'uncached_property',
                                'file': file_path,
                                'description': '使用未緩存的計算屬性可能導致序列化期間重複計算',
                                'solution': '考慮使用 functools.cached_property 緩存計算結果',
                                'severity': 'low',
                                'code_example': '''
# 優化前:
@property
def full_name(self) -> str:
    return f"{self.first_name} {self.last_name}"

# 優化後:
from functools import cached_property

@cached_property
def full_name(self) -> str:
    return f"{self.first_name} {self.last_name}"
'''
                            })
                        
                        # 檢查是否使用了過多的嵌套模型
                        nested_models_count = content.count('BaseModel')
                        if nested_models_count > 5:
                            analysis_result['issues'].append({
                                'type': 'excessive_nested_models',
                                'file': file_path,
                                'description': f'檢測到大量嵌套的 Pydantic 模型 ({nested_models_count})，可能導致過度序列化',
                                'solution': '考慮拆分模型或使用回應模型減少不必要的欄位',
                                'severity': 'medium'
                            })
    
    def _analyze_pagination(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析分頁問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 根據框架分析分頁問題
        if self.framework == 'django':
            self._detect_django_pagination_issues(analysis_result)
        elif self.framework == 'flask':
            self._detect_flask_pagination_issues(analysis_result)
        elif self.framework == 'fastapi':
            self._detect_fastapi_pagination_issues(analysis_result)
    
    def _detect_django_pagination_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 Django 中的分頁問題
        
        Args:
            analysis_result: 分析結果字典
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py') and ('view' in file.lower() or 'viewset' in file.lower()):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否有缺少分頁的 API 視圖
                    view_pattern = r'class\s+\w+(?:View|ViewSet)\s*\([^)]*\):'
                    view_matches = re.findall(view_pattern, content)
                    
                    # 檢查這些視圖是否缺少分頁
                    if view_matches and 'ListAPIView' in content and 'pagination_class' not in content and 'paginate_queryset' not in content:
                        analysis_result['issues'].append({
                            'type': 'missing_pagination',
                            'file': file_path,
                            'description': '列表視圖缺少分頁，可能導致大型資料集的性能問題',
                            'solution': '添加分頁類以限制回應大小',
                            'severity': 'high',
                            'code_example': '''
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100
}

# 或在視圖中指定
class MyListView(ListAPIView):
    pagination_class = PageNumberPagination
    page_size = 100
'''
                        })
                    
                    # 檢查是否有過大的分頁大小
                    large_page_pattern = r'page_size\s*=\s*(\d+)'
                    page_size_matches = re.findall(large_page_pattern, content)
                    
                    for size_match in page_size_matches:
                        size = int(size_match)
                        if size > 1000:
                            analysis_result['issues'].append({
                                'type': 'large_page_size',
                                'file': file_path,
                                'description': f'過大的分頁大小 ({size})，可能導致資料傳輸和處理延遲',
                                'solution': '將分頁大小減少到合理範圍（通常為 20-100）',
                                'severity': 'medium'
                            })
    
    def _detect_flask_pagination_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 Flask 中的分頁問題
        
        Args:
            analysis_result: 分析結果字典
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 跳過不處理 SQLAlchemy 的文件
                    if 'sqlalchemy' not in content.lower():
                        continue
                    
                    # 檢查是否有返回所有結果而不分頁的端點
                    query_all_pattern = r'\.query\.all\(\)'
                    route_pattern = r'@(?:app|blueprint)\.route\([\'"][^\'"]*[\'"]\)'
                    
                    if re.search(query_all_pattern, content) and re.search(route_pattern, content) and 'limit' not in content:
                        analysis_result['issues'].append({
                            'type': 'missing_pagination',
                            'file': file_path,
                            'description': '直接返回 .query.all() 結果而沒有分頁',
                            'solution': '實施分頁以限制回應大小',
                            'severity': 'high',
                            'code_example': '''
# 優化前:
@app.route('/api/items')
def get_items():
    items = Item.query.all()
    return jsonify([item.to_dict() for item in items])

# 優化後:
@app.route('/api/items')
def get_items():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)  # 限制最大頁面大小
    pagination = Item.query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [item.to_dict() for item in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })
'''
                        })
    
    def _detect_fastapi_pagination_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        檢測 FastAPI 中的分頁問題
        
        Args:
            analysis_result: 分析結果字典
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否有 FastAPI 端點定義
                    if '@app.get' not in content and '@router.get' not in content:
                        continue
                    
                    # 檢查是否有返回所有結果而不分頁的端點
                    # 檢查有請求參數但沒有分頁參數的端點
                    endpoint_pattern = r'@(?:app|router)\.get\([\'"][^\'"]*[\'"]\)\s*async\s+def\s+([^\(]+)\('
                    endpoint_matches = re.findall(endpoint_pattern, content)
                    
                    for endpoint in endpoint_matches:
                        # 檢查這個端點的函數定義中是否提到 limit 或 skip 參數
                        func_pattern = rf'async\s+def\s+{re.escape(endpoint)}\s*\([^)]*\)'
                        func_match = re.search(func_pattern, content)
                        
                        if func_match and 'limit' not in func_match.group(0) and 'skip' not in func_match.group(0) and 'page' not in func_match.group(0):
                            # 檢查函數體是否有 .all() 調用
                            func_index = content.find(func_match.group(0))
                            if func_index >= 0:
                                # 簡單檢查：查找下一個函數定義或文件結尾前的內容
                                next_func = content.find('async def', func_index + len(func_match.group(0)))
                                func_content = content[func_index : next_func if next_func > 0 else len(content)]
                                
                                # 如果使用資料庫操作但沒有分頁
                                if ('.all()' in func_content or '.filter(' in func_content) and 'limit' not in func_content and 'offset' not in func_content:
                                    analysis_result['issues'].append({
                                        'type': 'missing_pagination',
                                        'file': file_path,
                                        'description': f'端點 {endpoint} 返回所有結果而沒有分頁',
                                        'solution': '使用查詢參數實施分頁',
                                        'severity': 'high',
                                        'code_example': '''
# 優化前:
@app.get("/items/")
async def read_items():
    items = db.query(Item).all()
    return items

# 優化後:
@app.get("/items/")
async def read_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    items = db.query(Item).offset(skip).limit(limit).all()
    return items
'''
                                    })
    
    def _analyze_response_size(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析回應大小問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 查找可能返回大量數據的端點
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否有端點定義
                    if '@app' not in content and '@route' not in content and 'def get' not in content:
                        continue
                    
                    # 檢查是否有不加篩選的查詢
                    unfiltered_queries = [
                        ('.all()', '使用 .all() 檢索所有記錄'),
                        ('find({})', '使用空篩選查詢所有文檔'),
                        ('select()', '使用沒有篩選的 select()')
                    ]
                    
                    for query, description in unfiltered_queries:
                        if query in content:
                            # 檢查是否在回應中直接返回
                            analysis_result['issues'].append({
                                'type': 'large_response',
                                'file': file_path,
                                'description': description + '，可能導致大量數據傳輸',
                                'solution': '使用分頁、適當的篩選或欄位選擇限制回應大小',
                                'severity': 'medium'
                            })
                    
                    # 檢查是否有嵌套循環生成回應
                    nested_list_comp_pattern = r'\[\s*\[\s*.*?\s*for\s+.*?\s+in\s+.*?\s*\]\s*for\s+'
                    if re.search(nested_list_comp_pattern, content):
                        analysis_result['issues'].append({
                            'type': 'nested_response_generation',
                            'file': file_path,
                            'description': '使用嵌套列表推導式生成回應，可能導致性能問題',
                            'solution': '考慮優化資料結構或使用資料庫層面的連接',
                            'severity': 'medium'
                        })
                    
                    # 檢查是否有大量連接的查詢
                    if self.framework == 'django':
                        if 'select_related' in content and content.count('__') > 5:
                            analysis_result['issues'].append({
                                'type': 'excessive_joins',
                                'file': file_path,
                                'description': '使用過多的級聯關係（__）可能導致複雜的 SQL 連接',
                                'solution': '減少查詢中的關聯層次或分解為多個查詢',
                                'severity': 'medium'
                            })
    
    def _calculate_performance_score(self, analysis_result: Dict[str, Any]) -> int:
        """
        計算性能分數
        
        Args:
            analysis_result: 分析結果字典
            
        Returns:
            性能分數 (0-100)
        """
        # 基礎分數
        base_score = 100
        
        # 根據問題數量和嚴重性減少分數
        severity_penalties = {
            'high': 10,
            'medium': 5,
            'low': 2
        }
        
        # 數據庫問題扣分
        for issue in analysis_result['database_issues']:
            severity = issue.get('severity', 'medium')
            base_score -= severity_penalties.get(severity, 5)
        
        # 一般性能問題扣分
        for issue in analysis_result['issues']:
            severity = issue.get('severity', 'medium')
            base_score -= severity_penalties.get(severity, 5)
        
        # 確保分數在 0-100 範圍內
        return max(0, min(100, base_score))
    
    def generate_optimization_recommendations(self) -> Dict[str, Any]:
        """
        生成性能優化建議
        
        Returns:
            含詳細建議的字典
        """
        # 首先分析性能問題
        analysis = self.analyze_api_performance()
        
        # 根據分析結果生成建議
        recommendations = {
            'summary': {
                'score': analysis['overall_score'],
                'rating': self._get_score_rating(analysis['overall_score']),
                'total_issues': len(analysis['issues']) + len(analysis['database_issues']),
                'high_priority_issues': sum(1 for issue in analysis['issues'] + analysis['database_issues'] if issue.get('severity') == 'high')
            },
            'database_recommendations': self._generate_database_recommendations(analysis),
            'caching_recommendations': self._generate_caching_recommendations(analysis),
            'code_recommendations': self._generate_code_recommendations(analysis),
            'framework_specific': self._generate_framework_recommendations(analysis)
        }
        
        return recommendations
    
    def _get_score_rating(self, score: int) -> str:
        """
        將分數轉換為等級
        
        Args:
            score: 性能分數
            
        Returns:
            等級字符串
        """
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _generate_database_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成數據庫優化建議
        
        Args:
            analysis: 性能分析結果
            
        Returns:
            數據庫優化建議列表
        """
        recommendations = []
        
        # 從資料庫問題生成建議
        for issue in analysis['database_issues']:
            recommendations.append({
                'title': self._get_issue_title(issue),
                'description': issue.get('description', ''),
                'solution': issue.get('solution', ''),
                'priority': issue.get('severity', 'medium'),
                'code_example': issue.get('code_example', None)
            })
        
        # 添加通用資料庫建議
        if not any(issue['type'] == 'n_plus_one' for issue in analysis['database_issues']):
            if self.framework == 'django':
                recommendations.append({
                    'title': '使用 select_related 和 prefetch_related',
                    'description': '對於有外鍵關係的模型，使用 select_related 和 prefetch_related 可以減少資料庫查詢',
                    'solution': '識別有關聯的查詢，並使用適當的方法預取資料',
                    'priority': 'medium',
                    'code_example': '''
# 優化前
user = User.objects.get(id=user_id)
company = user.company  # 導致額外的資料庫查詢

# 優化後
user = User.objects.select_related('company').get(id=user_id)
company = user.company  # 不需要額外的查詢
'''
                })
            elif self.framework == 'flask' or self.framework == 'fastapi':
                recommendations.append({
                    'title': '使用 joinedload 和 subqueryload',
                    'description': '對於有關聯關係的模型，使用 joinedload 和 subqueryload 可以減少資料庫查詢',
                    'solution': '識別有關聯的查詢，並使用適當的方法預取資料',
                    'priority': 'medium',
                    'code_example': '''
# 優化前
user = session.query(User).filter(User.id == user_id).first()
company = user.company  # 導致額外的資料庫查詢

# 優化後
from sqlalchemy.orm import joinedload
user = session.query(User).options(joinedload(User.company)).filter(User.id == user_id).first()
company = user.company  # 不需要額外的查詢
'''
                })
        
        # 添加索引建議
        recommendations.append({
            'title': '確保常用查詢欄位有索引',
            'description': '缺少關鍵欄位的索引可能導致慢查詢',
            'solution': '識別常用於篩選、排序和連接的欄位，並為它們創建索引',
            'priority': 'high'
        })
        
        return recommendations
    
    def _generate_caching_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成緩存優化建議
        
        Args:
            analysis: 性能分析結果
            
        Returns:
            緩存優化建議列表
        """
        recommendations = []
        
        # 添加一般緩存建議
        if self.framework == 'django':
            recommendations.append({
                'title': '使用 Django 緩存框架',
                'description': '對於經常訪問且很少變化的資料，使用緩存可以顯著提高性能',
                'solution': '設置 Django 緩存並使用裝飾器或手動緩存常用視圖或計算',
                'priority': 'medium',
                'code_example': '''
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# views.py
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 緩存 15 分鐘
def my_view(request):
    # 視圖邏輯
    return response
'''
            })
        elif self.framework == 'flask':
            recommendations.append({
                'title': '使用 Flask-Caching',
                'description': '對於經常訪問且很少變化的資料，使用緩存可以顯著提高性能',
                'solution': '設置 Flask-Caching 並使用裝飾器緩存常用路由或函數結果',
                'priority': 'medium',
                'code_example': '''
from flask import Flask
from flask_caching import Cache

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

@app.route('/api/expensive-operation')
@cache.cached(timeout=300)  # 緩存 5 分鐘
def expensive_operation():
    # 複雜計算或查詢
    return result
'''
            })
        elif self.framework == 'fastapi':
            recommendations.append({
                'title': '實施 FastAPI 緩存',
                'description': '對於經常訪問且很少變化的資料，使用緩存可以顯著提高性能',
                'solution': '使用 fastapi-cache 或實施自定義緩存依賴',
                'priority': 'medium',
                'code_example': '''
from fastapi import FastAPI, Depends
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

app = FastAPI()

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost", encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

@app.get("/api/expensive-operation")
@cache(expire=300)  # 緩存 5 分鐘
async def expensive_operation():
    # 複雜計算或查詢
    return result
'''
            })
        
        # ETags 建議
        recommendations.append({
            'title': '實施 ETags 支援',
            'description': 'ETags 允許客戶端快取回應，並只在資料變化時獲取新資料',
            'solution': '設置 ETag 標頭並處理條件請求，減少不必要的資料傳輸',
            'priority': 'medium'
        })
        
        # 回應壓縮建議
        recommendations.append({
            'title': '啟用 Gzip/Brotli 壓縮',
            'description': '壓縮回應可以顯著減少網絡傳輸大小和時間',
            'solution': '在 Web 服務器或應用程式層級啟用回應壓縮',
            'priority': 'high'
        })
        
        return recommendations
    
    def _generate_code_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成程式碼優化建議
        
        Args:
            analysis: 性能分析結果
            
        Returns:
            程式碼優化建議列表
        """
        recommendations = []
        
        # 從一般問題生成建議
        for issue in analysis['issues']:
            recommendations.append({
                'title': self._get_issue_title(issue),
                'description': issue.get('description', ''),
                'solution': issue.get('solution', ''),
                'priority': issue.get('severity', 'medium'),
                'code_example': issue.get('code_example', None)
            })
        
        # 添加異步建議（如果適用）
        if self.framework == 'fastapi':
            recommendations.append({
                'title': '優化異步操作',
                'description': '未正確使用異步功能可能導致性能瓶頸',
                'solution': '確保 I/O 密集型操作（如資料庫查詢、HTTP 請求）使用 async/await 模式',
                'priority': 'high',
                'code_example': '''
# 優化前 - 阻塞操作
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    # 注意：在異步函數中使用同步 API 會阻塞事件循環
    item = sync_db_client.get_item(item_id)  
    return item

# 優化後 - 正確的異步操作
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    item = await async_db_client.get_item(item_id)
    return item
'''
            })
        
        # 添加序列化建議
        recommendations.append({
            'title': '最小化序列化負載',
            'description': '只返回客戶端需要的欄位可以減少序列化時間和傳輸大小',
            'solution': '明確指定需要序列化的欄位，避免使用 "__all__" 或自動序列化所有欄位',
            'priority': 'medium'
        })
        
        # 添加日誌優化建議
        recommendations.append({
            'title': '優化日誌操作',
            'description': '過度或低效的日誌記錄可能影響 API 性能',
            'solution': '在生產環境中使用適當的日誌級別，考慮異步日誌處理',
            'priority': 'low'
        })
        
        return recommendations
    
    def _generate_framework_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成框架特定的優化建議
        
        Args:
            analysis: 性能分析結果
            
        Returns:
            框架特定的優化建議列表
        """
        recommendations = []
        
        if self.framework == 'django':
            recommendations.extend([
                {
                    'title': '使用 Django 調試工具欄分析性能',
                    'description': 'Django 調試工具欄可以幫助識別慢查詢和性能瓶頸',
                    'solution': '在開發環境中安裝 django-debug-toolbar 並分析查詢性能',
                    'priority': 'medium'
                },
                {
                    'title': '設置適當的數據庫連接池',
                    'description': '默認的 Django 數據庫設置可能不適合高流量 API',
                    'solution': '配置資料庫連接池大小和超時設置以適應負載',
                    'priority': 'medium'
                }
            ])
        elif self.framework == 'flask':
            recommendations.extend([
                {
                    'title': '使用適當的 WSGI/ASGI 服務器',
                    'description': 'Flask 開發服務器不適合生產環境',
                    'solution': '為生產環境使用 Gunicorn 或 uWSGI，並適當設置工作進程數量',
                    'priority': 'high'
                },
                {
                    'title': '實施請求生命週期優化',
                    'description': 'Flask 的請求處理可以通過中間件優化',
                    'solution': '使用 before_request 和 after_request 鉤子優化公共操作',
                    'priority': 'medium'
                }
            ])
        elif self.framework == 'fastapi':
            recommendations.extend([
                {
                    'title': '使用 Starlette 內置優化功能',
                    'description': 'FastAPI 建立在 Starlette 之上，提供了許多性能優化選項',
                    'solution': '使用中間件緩存、壓縮和靜態文件處理',
                    'priority': 'medium'
                },
                {
                    'title': '優化 Pydantic 模型',
                    'description': 'Pydantic 驗證可能在大型模型或大量請求時成為瓶頸',
                    'solution': '使用 Pydantic 的 Config 類設置更高效的驗證選項',
                    'priority': 'medium',
                    'code_example': '''
from pydantic import BaseModel

class Config:
    # 允許從 ORM 模型自動填充
    orm_mode = True
    # 驗證分配而不是構造函數（更快）
    validate_assignment = False
    # 禁用額外屬性驗證
    extra = 'ignore'
'''
                }
            ])
        
        # 通用 API 框架建議
        recommendations.append({
            'title': '實施 API 速率限制',
            'description': '速率限制可以防止 API 過載並提高整體可用性',
            'solution': '根據客戶端 IP、API 密鑰或用戶 ID 實施速率限制',
            'priority': 'high'
        })
        
        return recommendations
    
    def _get_issue_title(self, issue: Dict[str, Any]) -> str:
        """
        從問題類型生成標題
        
        Args:
            issue: 問題字典
            
        Returns:
            問題標題
        """
        issue_type = issue.get('type', '')
        
        titles = {
            'n_plus_one': 'N+1 查詢問題',
            'async_n_plus_one': '異步 N+1 查詢問題',
            'individual_creates': '循環中的個別創建操作',
            'individual_saves': '循環中的個別保存操作',
            'individual_adds': '循環中的個別添加操作',
            'multiple_commits': '循環中的多次提交',
            'serializer_depth': '過度序列化問題',
            'uncached_method_field': '未緩存的方法欄位',
            'excessive_serialization': '過度序列化所有欄位',
            'uncached_property': '未緩存的計算屬性',
            'excessive_nested_models': '過多嵌套模型',
            'missing_pagination': '缺少分頁',
            'large_page_size': '過大的分頁大小',
            'large_response': '大型回應',
            'nested_response_generation': '嵌套回應生成',
            'excessive_joins': '過多的表連接'
        }
        
        return titles.get(issue_type, issue_type.replace('_', ' ').title())
    
    def optimize_endpoint(self, file_path: str, function_name: str) -> Dict[str, Any]:
        """
        優化特定 API 端點
        
        Args:
            file_path: 文件路徑
            function_name: 端點函數名稱
            
        Returns:
            優化結果
        """
        # 讀取文件
        content = read_file(file_path)
        
        # 尋找函數定義
        function_pattern = rf'(?:async\s+)?def\s+{re.escape(function_name)}\s*\([^)]*\):'
        function_match = re.search(function_pattern, content)
        
        if not function_match:
            return {
                'success': False,
                'message': f'未找到函數 {function_name}'
            }
        
        # 獲取函數內容
        function_start = function_match.start()
        
        # 尋找函數結束
        function_end = len(content)
        indentation = 0
        lines = content[function_start:].split('\n')
        
        # 計算函數的縮排
        first_line = lines[0]
        for i, char in enumerate(first_line):
            if char != ' ' and char != '\t':
                break
            indentation += 1
        
        # 尋找函數結束位置
        current_pos = function_start
        for i, line in enumerate(lines[1:], 1):
            # 跳過空行
            if not line.strip():
                current_pos += len(line) + 1  # +1 for newline
                continue
            
            # 檢查縮排
            line_indent = 0
            for char in line:
                if char != ' ' and char != '\t':
                    break
                line_indent += 1
            
            # 如果縮排小於或等於函數縮排，函數已結束
            if line_indent <= indentation and line.strip():
                function_end = current_pos
                break
            
            current_pos += len(line) + 1  # +1 for newline
        
        # 提取函數代碼
        function_code = content[function_start:function_end]
        
        # 分析函數代碼的性能問題
        optimization_result = self._optimize_function_code(function_code, self.framework)
        
        if not optimization_result['optimized_code']:
            return {
                'success': False,
                'message': '無法優化函數代碼',
                'original_code': function_code
            }
        
        # 更新文件
        new_content = content[:function_start] + optimization_result['optimized_code'] + content[function_end:]
        write_success = write_file(file_path, new_content)
        
        if not write_success:
            return {
                'success': False,
                'message': '無法寫入優化後的代碼到文件',
                'original_code': function_code,
                'optimized_code': optimization_result['optimized_code']
            }
        
        return {
            'success': True,
            'message': '成功優化端點',
            'optimizations': optimization_result['optimizations'],
            'original_code': function_code,
            'optimized_code': optimization_result['optimized_code']
        }
    
    def _optimize_function_code(self, function_code: str, framework: str) -> Dict[str, Any]:
        """
        優化函數代碼
        
        Args:
            function_code: 函數代碼
            framework: 框架名稱
            
        Returns:
            優化結果
        """
        optimizations = []
        optimized_code = function_code
        
        # 根據框架應用特定優化
        if framework == 'django':
            # 檢查並修復 N+1 查詢
            if '.objects.get(' in function_code and 'for ' in function_code and 'select_related' not in function_code:
                # 簡單的啟發式方法：添加 select_related
                relation_pattern = r'(\w+)\.objects\.filter\(.*?\)(?:\.\w+\(\))?'
                relation_match = re.search(relation_pattern, function_code)
                
                if relation_match:
                    model_name = relation_match.group(1)
                    
                    # 查找可能的關係字段
                    field_pattern = rf'for\s+\w+\s+in\s+.*?:\s*.*?\.(\w+)'
                    field_match = re.search(field_pattern, function_code, re.DOTALL)
                    
                    if field_match:
                        relation_field = field_match.group(1)
                        # 添加 select_related
                        original_query = f"{model_name}.objects.filter"
                        optimized_query = f"{model_name}.objects.select_related('{relation_field}').filter"
                        optimized_code = optimized_code.replace(original_query, optimized_query)
                        
                        optimizations.append({
                            'type': 'n_plus_one_fix',
                            'description': f'添加 select_related(\'{relation_field}\') 以解決 N+1 查詢問題'
                        })
            
            # 檢查並修復分頁問題
            if '.all()' in function_code and ('page' not in function_code.lower() and 'paginate' not in function_code.lower()):
                # 添加分頁
                pagination_code = '''
    # 從查詢參數獲取分頁信息
    page = request.GET.get('page', 1)
    page_size = min(int(request.GET.get('page_size', 100)), 1000)  # 限制最大頁面大小
    
    # 應用分頁
    paginator = Paginator(queryset, page_size)
    queryset = paginator.get_page(page)
'''
                # 查找並替換 .all() 調用
                all_pattern = r'(\w+)\s*=\s*.*?\.all\(\)'
                all_match = re.search(all_pattern, function_code)
                
                if all_match:
                    queryset_var = all_match.group(1)
                    insertion_point = all_match.end()
                    
                    # 插入分頁代碼
                    before_insertion = optimized_code[:insertion_point]
                    after_insertion = optimized_code[insertion_point:]
                    optimized_code = before_insertion + pagination_code + after_insertion
                    
                    # 確保導入 Paginator
                    if 'from django.core.paginator import Paginator' not in optimized_code:
                        paginator_import = 'from django.core.paginator import Paginator\n'
                        first_line_end = optimized_code.find('\n')
                        if first_line_end != -1:
                            optimized_code = optimized_code[:first_line_end + 1] + paginator_import + optimized_code[first_line_end + 1:]
                    
                    optimizations.append({
                        'type': 'pagination_added',
                        'description': '添加分頁以限制回應大小'
                    })
        
        elif framework == 'flask':
            # 檢查並修復 SQLAlchemy N+1 查詢
            if '.query.' in function_code and 'for ' in function_code and 'joinedload' not in function_code:
                # 簡單的啟發式方法：添加 joinedload
                query_pattern = r'(\w+)\.query\.(\w+)\(.*?\)'
                query_match = re.search(query_pattern, function_code)
                
                if query_match:
                    model_name = query_match.group(1)
                    
                    # 查找可能的關係字段
                    field_pattern = rf'for\s+\w+\s+in\s+.*?:\s*.*?\.(\w+)'
                    field_match = re.search(field_pattern, function_code, re.DOTALL)
                    
                    if field_match:
                        relation_field = field_match.group(1)
                        # 添加 joinedload
                        joinedload_import = 'from sqlalchemy.orm import joinedload\n'
                        
                        # 插入導入語句
                        first_line_end = optimized_code.find('\n')
                        if first_line_end != -1:
                            optimized_code = optimized_code[:first_line_end + 1] + joinedload_import + optimized_code[first_line_end + 1:]
                        
                        # 添加 joinedload 選項
                        original_query = f"{model_name}.query"
                        optimized_query = f"{model_name}.query.options(joinedload({model_name}.{relation_field}))"
                        optimized_code = optimized_code.replace(original_query, optimized_query)
                        
                        optimizations.append({
                            'type': 'n_plus_one_fix',
                            'description': f'添加 joinedload({model_name}.{relation_field}) 以解決 N+1 查詢問題'
                        })
            
            # 檢查並修復分頁問題
            if '.all()' in function_code and ('page' not in function_code.lower() and 'limit' not in function_code.lower()):
                # 添加分頁
                pagination_code = '''
    # 從查詢參數獲取分頁信息
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 100, type=int), 1000)  # 限制最大頁面大小
    
    # 應用分頁
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items
    
    # 構建分頁回應
    response = {
        'items': items,
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    }
'''
                # 查找並替換 .all() 調用
                all_pattern = r'(\w+)\s*=\s*(.*?)\.all\(\)'
                all_match = re.search(all_pattern, function_code)
                
                if all_match:
                    items_var = all_match.group(1)
                    query_var = all_match.group(2)
                    
                    # 替換全部調用為分頁查詢
                    optimized_code = optimized_code.replace(f"{items_var} = {query_var}.all()", f"query = {query_var}{pagination_code}")
                    
                    # 調整返回值
                    return_pattern = rf'return .*?{items_var}.*?'
                    return_match = re.search(return_pattern, optimized_code)
                    
                    if return_match:
                        original_return = return_match.group(0)
                        optimized_code = optimized_code.replace(original_return, "return response")
                    
                    optimizations.append({
                        'type': 'pagination_added',
                        'description': '添加分頁以限制回應大小'
                    })
        
        elif framework == 'fastapi':
            # 檢查並修復異步 N+1 查詢
            if 'async def' in function_code and 'await' in function_code and 'for ' in function_code:
                # 檢查循環中的 await 調用
                pattern = r'for\s+\w+\s+in\s+(.*?):\s*.*?await'
                match = re.search(pattern, function_code, re.DOTALL)
                
                if match:
                    # 添加批次查詢建議
                    optimizations.append({
                        'type': 'async_query_optimization',
                        'description': '檢測到循環中的異步查詢。考慮使用批次查詢或 selectinload 減少資料庫往返'
                    })
                    
                    # 由於這需要較大的結構更改，只添加注釋建議而非自動修改代碼
                    optimized_code = optimized_code.replace(
                        "async def",
                        "# TODO: 優化循環中的異步查詢以減少資料庫往返\nasync def"
                    )
            
            # 檢查並修復分頁問題
            if '.all()' in function_code and ('limit' not in function_code.lower() and 'skip' not in function_code.lower()):
                # 將 all() 調用更改為帶有分頁的調用
                all_replace_pattern = r'(\w+)\s*=\s*(.+?)\.all\(\)'
                
                def pagination_replacement(match):
                    var_name = match.group(1)
                    query = match.group(2)
                    return f"{var_name} = {query}.offset(skip).limit(limit)"
                
                optimized_code = re.sub(all_replace_pattern, pagination_replacement, optimized_code)
                
                # 添加分頁參數
                function_def_pattern = r'(async\s+def\s+\w+\s*\()([^)]*?)(\):)'
                
                def add_pagination_params(match):
                    prefix = match.group(1)
                    existing_params = match.group(2)
                    suffix = match.group(3)
                    
                    # 檢查是否已有參數
                    if existing_params.strip():
                        return f"{prefix}{existing_params}, skip: int = 0, limit: int = 100{suffix}"
                    else:
                        return f"{prefix}skip: int = 0, limit: int = 100{suffix}"
                
                optimized_code = re.sub(function_def_pattern, add_pagination_params, optimized_code)
                
                optimizations.append({
                    'type': 'pagination_added',
                    'description': '添加分頁參數 (skip, limit) 並應用於資料庫查詢'
                })
                
                # 添加依賴導入
                if 'from fastapi import Query' not in optimized_code:
                    query_import = "from fastapi import Query\n"
                    first_line_end = optimized_code.find('\n')
                    if first_line_end != -1:
                        optimized_code = optimized_code[:first_line_end + 1] + query_import + optimized_code[first_line_end + 1:]
                
                # 更新參數驗證
                params_pattern = r'(skip: int = 0, limit: int = 100)'
                validated_params = "skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)"
                optimized_code = re.sub(params_pattern, validated_params, optimized_code)
        
        # 返回優化結果
        return {
            'optimized_code': optimized_code,
            'optimizations': optimizations
        }