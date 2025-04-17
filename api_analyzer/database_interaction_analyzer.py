"""
數據庫交互分析器 - 分析 API 中的數據庫查詢和交互模式
"""
import ast
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any

from utils.file_operations import read_file


class DatabaseInteractionAnalyzer:
    """分析 API 中的數據庫查詢和交互模式"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化數據庫交互分析器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.db_operations = []
        self.db_config = None
        
    def analyze_db_operations(self) -> List[Dict[str, Any]]:
        """
        分析專案中的數據庫操作
        
        Returns:
            數據庫操作資訊的列表
        """
        if not self.framework:
            from .endpoint_analyzer import EndpointAnalyzer
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
        
        # 根據框架選擇適當的分析方法
        if self.framework == 'django':
            self._analyze_django_db_operations()
        elif self.framework == 'flask':
            self._analyze_flask_db_operations()
        elif self.framework == 'fastapi':
            self._analyze_fastapi_db_operations()
        
        # 通用分析方法
        self._analyze_generic_db_operations()
        
        return self.db_operations
    
    def detect_db_config(self) -> Dict[str, Any]:
        """
        檢測數據庫配置
        
        Returns:
            數據庫配置資訊
        """
        if not self.framework:
            from .endpoint_analyzer import EndpointAnalyzer
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
        
        # 根據框架選擇適當的分析方法
        if self.framework == 'django':
            self._detect_django_db_config()
        elif self.framework == 'flask':
            self._detect_flask_db_config()
        elif self.framework == 'fastapi':
            self._detect_fastapi_db_config()
        
        return self.db_config or {}
    
    def _analyze_django_db_operations(self) -> None:
        """分析 Django ORM 操作"""
        # 尋找 views.py 和其他包含視圖的文件
        view_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'views.py' or file == 'viewsets.py' or file == 'serializers.py':
                    view_files.append(os.path.join(root, file))
        
        # 常見的 Django ORM 查詢方法
        orm_methods = [
            'objects.get', 'objects.filter', 'objects.all', 'objects.create', 
            'objects.update', 'objects.delete', 'save', 'delete'
        ]
        
        # 分析每個視圖文件
        for file_path in view_files:
            content = read_file(file_path)
            
            # 檢查是否包含 ORM 方法
            if not any(method in content for method in orm_methods):
                continue
                
            try:
                tree = ast.parse(content)
                
                # 檢查每個函數和方法
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        self._extract_django_orm_calls(node, file_path)
            except SyntaxError:
                continue
    
    def _extract_django_orm_calls(self, func_node: ast.FunctionDef, file_path: str) -> None:
        """
        從函數中提取 Django ORM 調用
        
        Args:
            func_node: 函數節點
            file_path: 文件路徑
        """
        # 尋找 ORM 方法調用
        for node in ast.walk(func_node):
            # 模型實例的 save()/delete() 方法
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ['save', 'delete'] and not isinstance(node.func.value, ast.Attribute):
                    # 可能是 model_instance.save() 或 model_instance.delete()
                    self.db_operations.append({
                        'operation': node.func.attr,
                        'model': '',  # 無法確定模型名稱
                        'function': func_node.name,
                        'file': file_path,
                        'line': node.lineno,
                        'framework': 'django'
                    })
            
            # objects manager 方法
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Attribute):
                if node.func.value.attr == 'objects' and node.func.attr in ['get', 'filter', 'all', 'create', 'update', 'delete']:
                    model_name = ''
                    if isinstance(node.func.value.value, ast.Name):
                        model_name = node.func.value.value.id
                    
                    self.db_operations.append({
                        'operation': f"objects.{node.func.attr}",
                        'model': model_name,
                        'function': func_node.name,
                        'file': file_path,
                        'line': node.lineno,
                        'framework': 'django'
                    })
            
            # 檢查 raw SQL 使用
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'raw':
                # 例如 Model.objects.raw()
                self.db_operations.append({
                    'operation': 'raw_sql',
                    'model': '',
                    'function': func_node.name,
                    'file': file_path,
                    'line': node.lineno,
                    'framework': 'django'
                })
    
    def _analyze_flask_db_operations(self) -> None:
        """分析 Flask 數據庫操作 (SQLAlchemy)"""
        # 查找所有 Python 文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否使用 SQLAlchemy
                    if not ('db.session' in content or 'SQLAlchemy' in content):
                        continue
                    
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找函數和方法
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                self._extract_flask_sqlalchemy_calls(node, file_path)
                    except SyntaxError:
                        continue
    
    def _extract_flask_sqlalchemy_calls(self, func_node: ast.FunctionDef, file_path: str) -> None:
        """
        從函數中提取 Flask SQLAlchemy 調用
        
        Args:
            func_node: 函數節點
            file_path: 文件路徑
        """
        # SQLAlchemy 操作方法
        sqlalchemy_methods = ['query', 'add', 'delete', 'commit', 'rollback', 'execute']
        
        for node in ast.walk(func_node):
            # 檢查 db.session 方法
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'session':
                    # 例如 db.session.add(), db.session.commit()
                    if node.func.attr in sqlalchemy_methods:
                        self.db_operations.append({
                            'operation': f"session.{node.func.attr}",
                            'function': func_node.name,
                            'file': file_path,
                            'line': node.lineno,
                            'framework': 'flask'
                        })
                
                # 檢查 Model.query 方法
                elif isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'query':
                    # 例如 User.query.filter_by()
                    model_name = ''
                    if isinstance(node.func.value.value, ast.Name):
                        model_name = node.func.value.value.id
                    
                    self.db_operations.append({
                        'operation': f"query.{node.func.attr}",
                        'model': model_name,
                        'function': func_node.name,
                        'file': file_path,
                        'line': node.lineno,
                        'framework': 'flask'
                    })
                
                # 檢查 db.engine.execute (Raw SQL)
                elif (isinstance(node.func.value, ast.Attribute) and 
                      node.func.value.attr == 'engine' and 
                      node.func.attr == 'execute'):
                    
                    self.db_operations.append({
                        'operation': 'raw_sql',
                        'function': func_node.name,
                        'file': file_path,
                        'line': node.lineno,
                        'framework': 'flask'
                    })
    
    def _analyze_fastapi_db_operations(self) -> None:
        """分析 FastAPI 數據庫操作"""
        # FastAPI 常使用 SQLAlchemy 或其他 ORM
        # 尋找包含常見數據庫操作的文件
        db_keywords = ['database', 'db', 'session', 'orm']
        operation_keywords = ['query', 'filter', 'get', 'add', 'delete', 'commit']
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查文件名和內容是否包含數據庫關鍵字
                    file_name_lower = file.lower()
                    if not any(keyword in file_name_lower for keyword in db_keywords) and not any(keyword in content.lower() for keyword in operation_keywords):
                        continue
                    
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找函數和方法中的數據庫操作
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                # 檢查參數中是否包含 db 或 session 參數
                                has_db_param = False
                                for arg in node.args.args:
                                    if arg.arg in ['db', 'session', 'conn', 'connection']:
                                        has_db_param = True
                                        break
                                
                                if has_db_param:
                                    self._extract_fastapi_db_calls(node, file_path)
                    except SyntaxError:
                        continue
    
    def _extract_fastapi_db_calls(self, func_node: ast.FunctionDef, file_path: str) -> None:
        """
        從函數中提取 FastAPI 數據庫調用
        
        Args:
            func_node: 函數節點
            file_path: 文件路徑
        """
        # 尋找 db/session 參數名
        db_param_names = []
        for arg in func_node.args.args:
            if arg.arg in ['db', 'session', 'conn', 'connection']:
                db_param_names.append(arg.arg)
        
        if not db_param_names:
            return
        
        for node in ast.walk(func_node):
            # 檢查 db.query/session.query 類型的調用
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id in db_param_names:
                    # 例如 db.query(), session.add()
                    self.db_operations.append({
                        'operation': f"{node.func.value.id}.{node.func.attr}",
                        'function': func_node.name,
                        'file': file_path,
                        'line': node.lineno,
                        'framework': 'fastapi'
                    })
                
                # 檢查像 db.query(Model).filter_by() 這樣的鏈式調用
                elif isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Attribute):
                    if isinstance(node.func.value.func.value, ast.Name) and node.func.value.func.value.id in db_param_names:
                        # 提取模型名稱（如果可能）
                        model_name = ''
                        if node.func.value.args and isinstance(node.func.value.args[0], ast.Name):
                            model_name = node.func.value.args[0].id
                        
                        self.db_operations.append({
                            'operation': f"{node.func.value.func.value.id}.{node.func.value.func.attr}.{node.func.attr}",
                            'model': model_name,
                            'function': func_node.name,
                            'file': file_path,
                            'line': node.lineno,
                            'framework': 'fastapi'
                        })
    
    def _analyze_generic_db_operations(self) -> None:
        """分析通用數據庫操作模式"""
        # 搜尋常見數據庫庫的使用
        db_libraries = ['sqlite3', 'pymysql', 'psycopg2', 'pymongo']
        
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否導入數據庫庫
                    if not any(f"import {lib}" in content or f"from {lib}" in content for lib in db_libraries):
                        continue
                    
                    try:
                        tree = ast.parse(content)
                        
                        # 尋找數據庫操作函數
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                self._extract_generic_db_calls(node, file_path)
                    except SyntaxError:
                        continue
    
    def _extract_generic_db_calls(self, func_node: ast.FunctionDef, file_path: str) -> None:
        """
        從函數中提取通用數據庫調用
        
        Args:
            func_node: 函數節點
            file_path: 文件路徑
        """
        # 常見的數據庫操作方法
        db_methods = [
            'execute', 'executemany', 'fetchall', 'fetchone', 'fetchmany', 
            'commit', 'rollback', 'cursor', 'connect'
        ]
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in db_methods:
                    # 檢查是否是 SQL 語句
                    sql_statement = None
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        sql_text = node.args[0].value.lower()
                        if any(keyword in sql_text for keyword in ['select', 'insert', 'update', 'delete', 'create', 'alter']):
                            sql_statement = node.args[0].value
                    
                    self.db_operations.append({
                        'operation': node.func.attr,
                        'function': func_node.name,
                        'file': file_path,
                        'line': node.lineno,
                        'sql': sql_statement,
                        'framework': 'generic'
                    })
    
    def _detect_django_db_config(self) -> None:
        """檢測 Django 數據庫配置"""
        # 尋找 settings.py 文件
        settings_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file == 'settings.py':
                    settings_files.append(os.path.join(root, file))
        
        for settings_file in settings_files:
            content = read_file(settings_file)
            
            # 檢查是否包含數據庫配置
            if 'DATABASES' not in content:
                continue
                
            try:
                tree = ast.parse(content)
                
                # 尋找 DATABASES 設置
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == 'DATABASES':
                                if isinstance(node.value, ast.Dict):
                                    # 解析數據庫配置字典
                                    db_config = {}
                                    
                                    # 尋找默認數據庫配置
                                    for i, key in enumerate(node.value.keys):
                                        if isinstance(key, ast.Constant) and key.value == 'default':
                                            default_db = node.value.values[i]
                                            if isinstance(default_db, ast.Dict):
                                                # 解析默認數據庫的設置
                                                for j, db_key in enumerate(default_db.keys):
                                                    if isinstance(db_key, ast.Constant) and isinstance(default_db.values[j], ast.Constant):
                                                        db_config[db_key.value] = default_db.values[j].value
                                    
                                    if db_config:
                                        self.db_config = {
                                            'type': 'django',
                                            'engine': db_config.get('ENGINE', ''),
                                            'name': db_config.get('NAME', ''),
                                            'user': db_config.get('USER', ''),
                                            'password': '***',  # 隱藏密碼
                                            'host': db_config.get('HOST', ''),
                                            'port': db_config.get('PORT', ''),
                                            'file': settings_file
                                        }
            except SyntaxError:
                continue
    
    def _detect_flask_db_config(self) -> None:
        """檢測 Flask 數據庫配置"""
        # 尋找可能包含數據庫配置的文件
        config_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py') and (file.startswith('config') or file == 'app.py' or file == '__init__.py'):
                    config_files.append(os.path.join(root, file))
        
        for config_file in config_files:
            content = read_file(config_file)
            
            # 檢查是否包含數據庫 URI
            if not ('SQLALCHEMY_DATABASE_URI' in content or 'DB_URI' in content):
                continue
                
            try:
                tree = ast.parse(content)
                
                # 尋找數據庫 URI 設置
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id in ['SQLALCHEMY_DATABASE_URI', 'DB_URI', 'DATABASE_URL']:
                                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                    uri = node.value.value
                                    
                                    # 嘗試解析 URI
                                    import re
                                    uri_match = re.match(r'(\w+)://([^:]+):([^@]*)@([^:/]+):?(\d*)/([^?]*)', uri)
                                    
                                    if uri_match:
                                        dialect, user, password, host, port, db_name = uri_match.groups()
                                        self.db_config = {
                                            'type': 'flask_sqlalchemy',
                                            'dialect': dialect,
                                            'name': db_name,
                                            'user': user,
                                            'password': '***',  # 隱藏密碼
                                            'host': host,
                                            'port': port or '',
                                            'file': config_file,
                                            'line': node.lineno
                                        }
                                    else:
                                        # 無法解析 URI 格式
                                        self.db_config = {
                                            'type': 'flask_sqlalchemy',
                                            'uri': uri.replace(re.search(r'://[^:]+:([^@]+)@', uri).group(1) if re.search(r'://[^:]+:([^@]+)@', uri) else '', '***'),
                                            'file': config_file,
                                            'line': node.lineno
                                        }
            except SyntaxError:
                continue
    
    def _detect_fastapi_db_config(self) -> None:
        """檢測 FastAPI 數據庫配置"""
        # FastAPI 通常將數據庫配置放在 config.py 或 database.py 等文件中
        config_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py') and (file.startswith('config') or 'database' in file.lower() or 'db' in file.lower()):
                    config_files.append(os.path.join(root, file))
        
        for config_file in config_files:
            content = read_file(config_file)
            
            # 檢查是否包含常見的數據庫配置模式
            db_indicators = ['SQLALCHEMY_DATABASE_URL', 'DATABASE_URL', 'create_engine', 'connection_string']
            if not any(indicator in content for indicator in db_indicators):
                continue
                
            try:
                tree = ast.parse(content)
                
                # 尋找數據庫 URL 設置
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and any(db_str in target.id for db_str in ['DATABASE_URL', 'DB_URL', 'DB_CONNECTION']):
                                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                    url = node.value.value
                                    
                                    # 隱藏敏感資訊
                                    masked_url = url
                                    if '@' in url:
                                        # 嘗試隱藏密碼
                                        import re
                                        masked_url = re.sub(r'://[^:]+:([^@]+)@', '://user:***@', url)
                                    
                                    self.db_config = {
                                        'type': 'fastapi',
                                        'url': masked_url,
                                        'file': config_file,
                                        'line': node.lineno
                                    }
                                    break
                
                # 如果沒有找到數據庫 URL，則尋找 create_engine 調用
                if not self.db_config:
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'create_engine':
                            if node.args and isinstance(node.args[0], ast.Name):
                                # 引用了另一個變數
                                url_var = node.args[0].id
                                self.db_config = {
                                    'type': 'fastapi',
                                    'url_variable': url_var,
                                    'file': config_file,
                                    'line': node.lineno
                                }
                            elif node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                                # 直接提供 URL
                                url = node.args[0].value
                                
                                # 隱藏敏感資訊
                                masked_url = url
                                if '@' in url:
                                    # 嘗試隱藏密碼
                                    import re
                                    masked_url = re.sub(r'://[^:]+:([^@]+)@', '://user:***@', url)
                                
                                self.db_config = {
                                    'type': 'fastapi',
                                    'url': masked_url,
                                    'file': config_file,
                                    'line': node.lineno
                                }
            except SyntaxError:
                continue
    
    def get_db_operation_metrics(self) -> Dict[str, Any]:
        """
        計算數據庫操作相關指標
        
        Returns:
            含有數據庫操作指標的字典
        """
        if not self.db_operations:
            self.analyze_db_operations()
            
        if not self.db_config:
            self.detect_db_config()
            
        # 操作類型統計
        operation_types = {}
        for op in self.db_operations:
            op_type = op.get('operation', '')
            operation_types[op_type] = operation_types.get(op_type, 0) + 1
        
        # 按模型/表分類操作
        model_operations = {}
        for op in self.db_operations:
            model = op.get('model', '')
            if model:
                if model not in model_operations:
                    model_operations[model] = []
                model_operations[model].append(op.get('operation', ''))
        
        # 原始SQL使用統計
        raw_sql_count = sum(1 for op in self.db_operations if op.get('operation', '') == 'raw_sql' or op.get('sql') is not None)
        
        # 可能的 N+1 查詢問題
        potential_n_plus_1 = []
        files_analyzed = set()
        
        for op in self.db_operations:
            file_path = op.get('file', '')
            if file_path in files_analyzed:
                continue
                
            files_analyzed.add(file_path)
            content = read_file(file_path)
            
            # 檢查常見的 N+1 模式（這是一個簡化的啟發式檢測）
            if self.framework == 'django':
                # 尋找在循環中進行查詢的模式
                for_query_pattern = re.findall(r'for\s+\w+\s+in\s+.+?:\s+.*?objects\.\w+', content, re.DOTALL)
                if for_query_pattern:
                    potential_n_plus_1.append({
                        'file': file_path,
                        'pattern': 'for_loop_with_query'
                    })
            elif self.framework == 'flask':
                # 尋找在循環中進行查詢的模式
                for_query_pattern = re.findall(r'for\s+\w+\s+in\s+.+?:\s+.*?query\.\w+', content, re.DOTALL)
                if for_query_pattern:
                    potential_n_plus_1.append({
                        'file': file_path,
                        'pattern': 'for_loop_with_query'
                    })
        
        return {
            'total_operations': len(self.db_operations),
            'operation_types': operation_types,
            'model_operations': model_operations,
            'raw_sql_count': raw_sql_count,
            'db_config_type': self.db_config.get('type', 'unknown') if self.db_config else 'unknown',
            'potential_n_plus_1_issues': potential_n_plus_1,
            'framework': self.framework
        }