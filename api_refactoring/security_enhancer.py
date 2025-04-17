"""
API 安全增強器 - 識別和修復 API 安全問題
"""
import ast
import os
import re
from typing import Dict, List, Tuple, Optional, Any

from utils.file_operations import read_file, write_file
from api_analyzer.auth_analyzer import AuthAnalyzer


class APISecurityEnhancer:
    """識別和修復 API 安全問題"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化 API 安全增強器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.auth_analyzer = AuthAnalyzer(project_path, framework)
        
        # 如果未指定框架，則檢測框架
        if not self.framework:
            from api_analyzer.endpoint_analyzer import EndpointAnalyzer
            endpoint_analyzer = EndpointAnalyzer(self.project_path)
            self.framework = endpoint_analyzer.detect_framework()
    
    def analyze_security_issues(self) -> Dict[str, Any]:
        """
        分析專案中的安全問題
        
        Returns:
            安全問題分析結果
        """
        # 初始化分析結果
        analysis_result = {
            'auth_issues': [],
            'input_validation_issues': [],
            'data_exposure_issues': [],
            'infrastructure_issues': [],
            'overall_score': 0,
            'critical_issues_count': 0
        }
        
        # 使用身份驗證分析器獲取身份驗證問題
        auth_issues = self.auth_analyzer.identify_security_issues()
        analysis_result['auth_issues'] = auth_issues
        
        # 分析輸入驗證問題
        self._analyze_input_validation_issues(analysis_result)
        
        # 分析數據曝露問題
        self._analyze_data_exposure_issues(analysis_result)
        
        # 分析基礎設施問題
        self._analyze_infrastructure_issues(analysis_result)
        
        # 計算關鍵問題數量
        analysis_result['critical_issues_count'] = sum(
            1 for issue in auth_issues + analysis_result['input_validation_issues'] + 
            analysis_result['data_exposure_issues'] + analysis_result['infrastructure_issues']
            if issue.get('severity') == 'high'
        )
        
        # 計算安全評分
        analysis_result['overall_score'] = self._calculate_security_score(analysis_result)
        
        return analysis_result
    
    def _analyze_input_validation_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析輸入驗證問題
        
        Args:
            analysis_result: 分析結果字典
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否有視圖或路由處理
                    if not self._is_route_handler_file(content):
                        continue
                    
                    # 檢查 SQL 注入問題
                    self._check_sql_injection(file_path, content, analysis_result)
                    
                    # 檢查跨站腳本 (XSS) 問題
                    self._check_xss_vulnerabilities(file_path, content, analysis_result)
                    
                    # 檢查不安全的反序列化
                    self._check_insecure_deserialization(file_path, content, analysis_result)
                    
                    # 檢查缺少的輸入驗證
                    self._check_missing_input_validation(file_path, content, analysis_result)
    
    def _is_route_handler_file(self, content: str) -> bool:
        """
        檢查文件是否包含路由處理程式
        
        Args:
            content: 文件內容
            
        Returns:
            是否包含路由處理程式
        """
        # 檢查常見的路由處理模式
        if self.framework == 'django':
            return 'from django.http' in content or 'from rest_framework' in content
        elif self.framework == 'flask':
            return '@app.route' in content or '@blueprint.route' in content
        elif self.framework == 'fastapi':
            return '@app.' in content or '@router.' in content
        else:
            # 通用檢查
            route_patterns = [
                '@app.route', '@app.get', '@app.post', 
                '@blueprint.route', '@router.', 
                'from django.http', 'from rest_framework'
            ]
            return any(pattern in content for pattern in route_patterns)
    
    def _check_sql_injection(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查 SQL 注入問題
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查常見的 SQL 注入模式
        sql_injection_patterns = [
            (r'execute\s*\(\s*[\'"](.*?)%s(.*?)[\'"]', '字符串格式化用於 SQL 查詢'),
            (r'execute\s*\(\s*[\'"].*?\s*\+\s*', '使用字符串連接構建 SQL 查詢'),
            (r'raw\s*\(\s*[\'"].*?\s*\+\s*', '使用字符串連接構建原始 SQL'),
            (r'cursor\.execute\s*\(\s*f[\'"]', '使用 f-string 構建 SQL 查詢')
        ]
        
        for pattern, description in sql_injection_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                analysis_result['input_validation_issues'].append({
                    'type': 'sql_injection',
                    'file': file_path,
                    'description': description,
                    'severity': 'high',
                    'solution': '使用參數化查詢而非字符串拼接',
                    'line': self._find_line_number(content, matches[0] if isinstance(matches[0], str) else matches[0][0])
                })
    
    def _check_xss_vulnerabilities(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查跨站腳本 (XSS) 問題
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查是否直接返回用戶輸入
        if self.framework == 'django':
            # 檢查是否使用 mark_safe 或 safe 過濾器
            if 'mark_safe' in content or '|safe' in content:
                analysis_result['input_validation_issues'].append({
                    'type': 'xss',
                    'file': file_path,
                    'description': '使用 mark_safe 或 |safe 標記可能導致 XSS 漏洞',
                    'severity': 'high',
                    'solution': '在使用 mark_safe 之前確保對用戶輸入進行適當的清理',
                    'line': self._find_line_number(content, 'mark_safe') or self._find_line_number(content, '|safe')
                })
        elif self.framework == 'flask':
            # 檢查是否使用 Markup 或 |safe 過濾器
            if 'Markup' in content or '|safe' in content:
                analysis_result['input_validation_issues'].append({
                    'type': 'xss',
                    'file': file_path,
                    'description': '使用 Markup 或 |safe 標記可能導致 XSS 漏洞',
                    'severity': 'high',
                    'solution': '在使用 Markup 之前確保對用戶輸入進行適當的清理',
                    'line': self._find_line_number(content, 'Markup') or self._find_line_number(content, '|safe')
                })
            
        # 檢查是否直接在 HTML 中插入請求數據
        request_data_in_html_pattern = r'[\'"]>\s*\{\{\s*.*?(?:request|form|body|param)[^}]*\}\}'
        if re.search(request_data_in_html_pattern, content, re.IGNORECASE):
            analysis_result['input_validation_issues'].append({
                'type': 'xss',
                'file': file_path,
                'description': '請求數據直接插入 HTML，可能導致 XSS 漏洞',
                'severity': 'high',
                'solution': '在渲染前對所有用戶輸入進行轉義或清理',
                'line': self._find_line_number(content, re.search(request_data_in_html_pattern, content, re.IGNORECASE).group(0))
            })
    
    def _check_insecure_deserialization(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查不安全的反序列化
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查使用 pickle 或 eval 的不安全反序列化
        insecure_deserialization_patterns = [
            (r'pickle\.loads\s*\(\s*(?!.*?trusted)', '使用 pickle.loads 進行不安全的反序列化'),
            (r'eval\s*\(\s*(?!.*?safe)', '使用 eval 函數可能導致執行任意代碼'),
            (r'yaml\.load\s*\(\s*(?!.*?Loader=yaml\.SafeLoader)', '不安全的 YAML 載入')
        ]
        
        for pattern, description in insecure_deserialization_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                analysis_result['input_validation_issues'].append({
                    'type': 'insecure_deserialization',
                    'file': file_path,
                    'description': description,
                    'severity': 'high',
                    'solution': '使用更安全的替代方法，例如 JSON 或使用 pickle.loads 時驗證來源',
                    'line': self._find_line_number(content, re.search(pattern, content, re.IGNORECASE).group(0))
                })
    
    def _check_missing_input_validation(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查缺少的輸入驗證
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 根據框架檢查輸入驗證模式
        if self.framework == 'django':
            # 檢查是否使用表單或序列化器進行驗證
            if 'request.data' in content or 'request.POST' in content:
                # 檢查是否驗證
                if 'is_valid()' not in content and 'clean(' not in content:
                    analysis_result['input_validation_issues'].append({
                        'type': 'missing_validation',
                        'file': file_path,
                        'description': '使用請求數據但沒有明確的驗證',
                        'severity': 'medium',
                        'solution': '使用表單或序列化器進行數據驗證',
                        'line': self._find_line_number(content, 'request.data') or self._find_line_number(content, 'request.POST')
                    })
        elif self.framework == 'flask':
            # 檢查是否使用 request 但沒有驗證
            if 'request.' in content and ('request.form' in content or 'request.json' in content):
                # 檢查是否有驗證
                if 'validate' not in content and 'schema.' not in content:
                    analysis_result['input_validation_issues'].append({
                        'type': 'missing_validation',
                        'file': file_path,
                        'description': '使用請求數據但沒有明確的驗證',
                        'severity': 'medium',
                        'solution': '使用 marshmallow 或 WTForms 進行數據驗證',
                        'line': self._find_line_number(content, 'request.form') or self._find_line_number(content, 'request.json')
                    })
        elif self.framework == 'fastapi':
            # FastAPI 通常使用 Pydantic 進行自動驗證，所以風險較低
            pass
    
    def _analyze_data_exposure_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析數據曝露問題
        
        Args:
            analysis_result: 分析結果字典
        """
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查是否有視圖或路由處理
                    if not self._is_route_handler_file(content):
                        continue
                    
                    # 檢查敏感數據曝露
                    self._check_sensitive_data_exposure(file_path, content, analysis_result)
                    
                    # 檢查缺少的響應標頭
                    self._check_missing_security_headers(file_path, content, analysis_result)
                    
                    # 檢查不安全的直接對象引用
                    self._check_insecure_direct_object_references(file_path, content, analysis_result)
                    
                    # 檢查調試信息
                    self._check_debug_information(file_path, content, analysis_result)
    
    def _check_sensitive_data_exposure(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查敏感數據曝露
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查常見的敏感數據模式
        sensitive_data_patterns = [
            (r'password', '可能的密碼曝露'),
            (r'secret', '可能的機密曝露'),
            (r'token', '可能的令牌曝露'),
            (r'api_key', '可能的 API 密鑰曝露'),
            (r'credit_card', '可能的信用卡數據曝露'),
            (r'ssn', '可能的社會安全號碼曝露')
        ]
        
        # 尋找正在返回的敏感數據
        for pattern, description in sensitive_data_patterns:
            # 檢查是否在回應或序列化中包含敏感字段
            serializer_pattern = rf'fields\s*=\s*\[[^\]]*[\'"]{pattern}[\'"]\s*[^\]]*\]'
            response_pattern = rf'[\'\"]{pattern}[\'\"]:\s*'
            
            if re.search(serializer_pattern, content, re.IGNORECASE) or re.search(response_pattern, content, re.IGNORECASE):
                analysis_result['data_exposure_issues'].append({
                    'type': 'sensitive_data_exposure',
                    'file': file_path,
                    'description': description,
                    'severity': 'high',
                    'solution': f'避免在回應中包含 {pattern} 數據，或進行適當的模糊處理',
                    'line': self._find_line_number(content, pattern)
                })
    
    def _check_missing_security_headers(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查缺少的安全標頭
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查是否有設置常見的安全標頭
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'Content-Security-Policy',
            'Strict-Transport-Security',
            'X-XSS-Protection'
        ]
        
        # 如果這是一個主要的設置或配置文件
        if 'settings' in file_path.lower() or 'config' in file_path.lower() or 'app.' in content or 'middleware' in content:
            missing_headers = []
            
            for header in security_headers:
                if header.lower().replace('-', '_') not in content.lower():
                    missing_headers.append(header)
            
            if missing_headers:
                analysis_result['data_exposure_issues'].append({
                    'type': 'missing_security_headers',
                    'file': file_path,
                    'description': f'缺少重要的安全標頭: {", ".join(missing_headers)}',
                    'severity': 'medium',
                    'solution': '添加適當的安全標頭以增強應用防禦能力',
                    'headers': missing_headers
                })
    
    def _check_insecure_direct_object_references(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查不安全的直接對象引用
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查是否直接使用 ID 查詢而不進行授權檢查
        if self.framework == 'django':
            # 尋找 get(id=...) 或 filter(id=...) 模式但沒有權限檢查
            match = re.search(r'\.(?:get|filter)\(\s*(?:id|pk)\s*=\s*([^)]+)\)', content)
            if match and 'permission' not in content and 'has_perm' not in content:
                analysis_result['data_exposure_issues'].append({
                    'type': 'insecure_direct_object_reference',
                    'file': file_path,
                    'description': '根據 ID 訪問對象但沒有明確的授權檢查',
                    'severity': 'medium',
                    'solution': '在訪問對象之前實施授權檢查',
                    'line': self._find_line_number(content, match.group(0))
                })
        elif self.framework == 'flask':
            match = re.search(r'\.(?:get|query.get|query.filter_by)\(\s*(?:id)\s*=\s*([^)]+)\)', content)
            if match and 'permission' not in content and 'require' not in content:
                analysis_result['data_exposure_issues'].append({
                    'type': 'insecure_direct_object_reference',
                    'file': file_path,
                    'description': '根據 ID 訪問對象但沒有明確的授權檢查',
                    'severity': 'medium',
                    'solution': '在訪問對象之前實施授權檢查',
                    'line': self._find_line_number(content, match.group(0))
                })
        elif self.framework == 'fastapi':
            # 檢查路由參數
            match = re.search(r'@(?:app|router)\.(?:get|post|put|delete)\([^\)]*{([^}]+)}', content)
            if match and 'Depends' in content and 'security' not in content:
                analysis_result['data_exposure_issues'].append({
                    'type': 'insecure_direct_object_reference',
                    'file': file_path,
                    'description': '根據路由參數訪問對象但可能缺少授權檢查',
                    'severity': 'medium',
                    'solution': '使用依賴注入實施授權檢查',
                    'line': self._find_line_number(content, match.group(0))
                })
    
    def _check_debug_information(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查調試信息
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查是否在生產環境中啟用了調試模式
        if 'settings' in file_path.lower() or 'config' in file_path.lower():
            if 'DEBUG = True' in content or 'debug=True' in content:
                # 檢查是否有條件控制
                if 'if ' not in content.split('DEBUG = True')[0].splitlines()[-1]:
                    analysis_result['data_exposure_issues'].append({
                        'type': 'debug_enabled',
                        'file': file_path,
                        'description': '可能在生產環境中啟用了調試模式',
                        'severity': 'high',
                        'solution': '在生產環境中禁用調試模式',
                        'line': self._find_line_number(content, 'DEBUG = True') or self._find_line_number(content, 'debug=True')
                    })
        
        # 檢查異常處理
        if self._is_route_handler_file(content) and 'except' in content:
            # 檢查是否在異常處理中返回錯誤堆棧
            if 'traceback' in content and 'return' in content:
                analysis_result['data_exposure_issues'].append({
                    'type': 'traceback_exposure',
                    'file': file_path,
                    'description': '可能在回應中返回錯誤堆棧信息',
                    'severity': 'medium',
                    'solution': '避免向客戶端暴露詳細的錯誤信息',
                    'line': self._find_line_number(content, 'traceback')
                })
            
            # 檢查是否缺少適當的異常處理
            try_blocks = re.findall(r'try:.*?except', content, re.DOTALL)
            for block in try_blocks:
                if 'except:' in block or 'except Exception:' in block:
                    if not re.search(r'log', block, re.IGNORECASE):
                        analysis_result['data_exposure_issues'].append({
                            'type': 'broad_exception_handling',
                            'file': file_path,
                            'description': '使用過於廣泛的異常處理而沒有適當的日誌記錄',
                            'severity': 'low',
                            'solution': '使用更具體的異常類型並記錄錯誤詳情',
                            'line': self._find_line_number(content, 'except:') or self._find_line_number(content, 'except Exception:')
                        })
    
    def _analyze_infrastructure_issues(self, analysis_result: Dict[str, Any]) -> None:
        """
        分析基礎設施問題
        
        Args:
            analysis_result: 分析結果字典
        """
        # 檢查配置文件
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file in ['settings.py', 'config.py', 'app.py', '__init__.py']:
                    file_path = os.path.join(root, file)
                    content = read_file(file_path)
                    
                    # 檢查不安全的 CORS 配置
                    self._check_insecure_cors(file_path, content, analysis_result)
                    
                    # 檢查不安全的 cookie 設置
                    self._check_insecure_cookies(file_path, content, analysis_result)
                    
                    # 檢查缺少的速率限制
                    self._check_missing_rate_limiting(file_path, content, analysis_result)
        
        # 檢查 requirements.txt 或 setup.py 中的依賴版本
        requirement_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file in ['requirements.txt', 'setup.py', 'Pipfile', 'Pipfile.lock']:
                    requirement_files.append(os.path.join(root, file))
        
        if requirement_files:
            self._check_outdated_dependencies(requirement_files, analysis_result)
    
    def _check_insecure_cors(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查不安全的 CORS 配置
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查是否配置了允許所有源的 CORS
        cors_patterns = [
            (r'CORS_ALLOW_ALL_ORIGINS\s*=\s*True', 'Django CORS 配置允許所有源'),
            (r'CORS_ORIGIN_ALLOW_ALL\s*=\s*True', 'Django CORS 配置允許所有源'),
            (r'access-control-allow-origin[\s\'"]*:[\s\'"]*\*', '設置允許所有源的 CORS 標頭'),
            (r'CORS\s*\([^\)]*\*', 'Flask-CORS 配置允許所有源')
        ]
        
        for pattern, description in cors_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                analysis_result['infrastructure_issues'].append({
                    'type': 'insecure_cors',
                    'file': file_path,
                    'description': description,
                    'severity': 'medium',
                    'solution': '限制 CORS 訪問至特定的可信域',
                    'line': self._find_line_number(content, re.search(pattern, content, re.IGNORECASE).group(0))
                })
    
    def _check_insecure_cookies(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查不安全的 cookie 設置
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查是否設置了不安全的 cookie
        cookie_patterns = [
            (r'SESSION_COOKIE_SECURE\s*=\s*False', 'Django 會話 cookie 未設置為安全'),
            (r'SESSION_COOKIE_HTTPONLY\s*=\s*False', 'Django 會話 cookie 未設置為 HttpOnly'),
            (r'CSRF_COOKIE_SECURE\s*=\s*False', 'Django CSRF cookie 未設置為安全'),
            (r'set_cookie\([^,]*,\s*[^,]*,[^,]*secure=False', 'Cookie 被設置為不安全'),
            (r'set_cookie\([^,]*,\s*[^,]*,[^,]*httponly=False', 'Cookie 未設置為 HttpOnly')
        ]
        
        for pattern, description in cookie_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                analysis_result['infrastructure_issues'].append({
                    'type': 'insecure_cookies',
                    'file': file_path,
                    'description': description,
                    'severity': 'medium',
                    'solution': '設置 Cookie 的 Secure 和 HttpOnly 標誌',
                    'line': self._find_line_number(content, re.search(pattern, content, re.IGNORECASE).group(0))
                })
        
        # 檢查 Cookie 設置中是否缺少 SameSite 屬性
        if 'set_cookie' in content and 'samesite' not in content.lower():
            analysis_result['infrastructure_issues'].append({
                'type': 'missing_samesite',
                'file': file_path,
                'description': 'Cookie 未設置 SameSite 屬性',
                'severity': 'low',
                'solution': '設置 Cookie 的 SameSite 屬性 (建議使用 "Lax" 或 "Strict")',
                'line': self._find_line_number(content, 'set_cookie')
            })
    
    def _check_missing_rate_limiting(self, file_path: str, content: str, analysis_result: Dict[str, Any]) -> None:
        """
        檢查缺少的速率限制
        
        Args:
            file_path: 文件路徑
            content: 文件內容
            analysis_result: 分析結果字典
        """
        # 檢查是否實施了速率限制
        rate_limit_keywords = [
            'rate_limit', 'throttle', 'ratelimit', 'limiter', 'throttling'
        ]
        
        # 只在主要配置文件中檢查
        if ('settings' in file_path.lower() or 'config' in file_path.lower() or 'app.py' in file_path) and not any(keyword in content.lower() for keyword in rate_limit_keywords):
            # 檢查框架特定的速率限制配置
            if self.framework == 'django' and 'DEFAULT_THROTTLE_CLASSES' not in content:
                analysis_result['infrastructure_issues'].append({
                    'type': 'missing_rate_limiting',
                    'file': file_path,
                    'description': '未檢測到 Django REST Framework 速率限制配置',
                    'severity': 'medium',
                    'solution': '配置 REST Framework 的 DEFAULT_THROTTLE_CLASSES 和 DEFAULT_THROTTLE_RATES'
                })
            elif self.framework == 'flask' and 'Flask-Limiter' not in content:
                analysis_result['infrastructure_issues'].append({
                    'type': 'missing_rate_limiting',
                    'file': file_path,
                    'description': '未檢測到 Flask 速率限制配置',
                    'severity': 'medium',
                    'solution': '使用 Flask-Limiter 或類似庫實施速率限制'
                })
            elif self.framework == 'fastapi' and 'RateLimiter' not in content and 'Limiter' not in content:
                analysis_result['infrastructure_issues'].append({
                    'type': 'missing_rate_limiting',
                    'file': file_path,
                    'description': '未檢測到 FastAPI 速率限制配置',
                    'severity': 'medium',
                    'solution': '使用如 fastapi-limiter 的庫實施速率限制'
                })
    
    def _check_outdated_dependencies(self, requirement_files: List[str], analysis_result: Dict[str, Any]) -> None:
        """
        檢查過時的依賴
        
        Args:
            requirement_files: 要檢查的需求文件列表
            analysis_result: 分析結果字典
        """
        # 這個功能需要外部數據源以檢查漏洞
        # 這裡僅作簡單檢查，提示用戶進行更詳細的掃描
        
        # 檢查是否有固定版本的依賴項
        has_pinned_versions = False
        has_too_permissive_versions = False
        
        for file_path in requirement_files:
            content = read_file(file_path)
            
            # 檢查已固定版本
            if re.search(r'==\d+\.\d+\.\d+', content):
                has_pinned_versions = True
            
            # 檢查過於寬鬆的版本
            if re.search(r'>=', content):
                has_too_permissive_versions = True
        
        if not has_pinned_versions or has_too_permissive_versions:
            analysis_result['infrastructure_issues'].append({
                'type': 'dependency_management',
                'file': requirement_files[0],  # 僅報告第一個文件
                'description': '依賴項版本管理可能不安全' + 
                              ('' if has_pinned_versions else '（未固定版本）') +
                              (', 使用過於寬鬆的版本限定' if has_too_permissive_versions else ''),
                'severity': 'medium',
                'solution': '固定依賴項到特定版本，並定期運行漏洞掃描以更新有安全問題的依賴項'
            })
    
    def _find_line_number(self, content: str, pattern: str) -> Optional[int]:
        """
        在內容中找到模式的行號
        
        Args:
            content: 文件內容
            pattern: 要查找的模式
            
        Returns:
            模式出現的行號，如果未找到則為 None
        """
        if not pattern:
            return None
            
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if pattern in line:
                return i
        return None
    
    def _calculate_security_score(self, analysis_result: Dict[str, Any]) -> int:
            """
            計算安全評分
            
            Args:
                analysis_result: 分析結果字典
                
            Returns:
                安全評分 (0-100)
            """
            # 基礎分數
            base_score = 100
            
            # 根據問題數量和嚴重性減少分數
            severity_penalties = {
                'high': 15,
                'medium': 7,
                'low': 3
            }
            
            # 計算每個嚴重性級別的問題數量
            issue_types = ['auth_issues', 'input_validation_issues', 'data_exposure_issues', 'infrastructure_issues']
            
            # 從每個問題類型中計算不同嚴重性級別的問題數量
            issue_counts = {'high': 0, 'medium': 0, 'low': 0}
            
            for issue_type in issue_types:
                for issue in analysis_result[issue_type]:
                    severity = issue.get('severity', 'medium')  # 預設為中等嚴重性
                    if severity in issue_counts:
                        issue_counts[severity] += 1
            
            # 計算總扣分
            total_penalty = 0
            for severity, count in issue_counts.items():
                total_penalty += count * severity_penalties[severity]
            
            # 確保分數不低於 0
            final_score = max(0, base_score - total_penalty)
            
            return final_score

    def fix_security_issues(self, analysis_result: Dict[str, Any], auto_fix: bool = False) -> Dict[str, Any]:
            """
            根據安全分析結果修復安全問題
            
            Args:
                analysis_result: 安全分析結果
                auto_fix: 是否自動修復問題
                
            Returns:
                修復結果報告
            """
            # 初始化修復報告
            fix_report = {
                'fixed_issues': [],
                'manual_fixes_needed': [],
                'unfixed_issues': []
            }
            
            # 如果沒有提供分析結果，先進行分析
            if not analysis_result:
                analysis_result = self.analyze_security_issues()
            
            # 處理各類問題
            self._fix_auth_issues(analysis_result.get('auth_issues', []), fix_report, auto_fix)
            self._fix_input_validation_issues(analysis_result.get('input_validation_issues', []), fix_report, auto_fix)
            self._fix_data_exposure_issues(analysis_result.get('data_exposure_issues', []), fix_report, auto_fix)
            self._fix_infrastructure_issues(analysis_result.get('infrastructure_issues', []), fix_report, auto_fix)
            
            # 更新安全評分
            if auto_fix and fix_report['fixed_issues']:
                updated_analysis = self.analyze_security_issues()
                fix_report['new_score'] = updated_analysis['overall_score']
                fix_report['score_improvement'] = updated_analysis['overall_score'] - analysis_result['overall_score']
            
            return fix_report
    
    def _fix_auth_issues(self, issues: List[Dict[str, Any]], fix_report: Dict[str, Any], auto_fix: bool) -> None:
        """
        修復身份驗證問題
        
        Args:
            issues: 身份驗證問題列表
            fix_report: 修復報告
            auto_fix: 是否自動修復
        """
        from utils.file_operations import read_file, write_file, backup_file
        
        for issue in issues:
            issue_type = issue.get('type', '')
            file_path = issue.get('file', '')
            
            if not file_path or not os.path.exists(file_path):
                fix_report['unfixed_issues'].append({
                    'issue': issue,
                    'reason': '找不到文件'
                })
                continue
            
            # 根據問題類型進行修復
            if issue_type == 'hardcoded_secret':
                # 硬編碼機密需要手動修復
                fix_report['manual_fixes_needed'].append({
                    'issue': issue,
                    'fix_suggestion': '將硬編碼的機密移動到環境變數或安全的配置存儲'
                })
            
            elif issue_type == 'missing_auth' and auto_fix and self.framework == 'django':
                # 嘗試為 Django 視圖添加登入要求裝飾器
                content = read_file(file_path)
                line_num = issue.get('line', 0)
                
                if line_num > 0:
                    lines = content.splitlines()
                    if line_num <= len(lines):
                        # 尋找函數定義
                        function_line = lines[line_num - 1]
                        if 'def ' in function_line:
                            # 備份文件
                            backup = backup_file(file_path)
                            if backup:
                                # 添加裝飾器並更新導入
                                import_line = 'from django.contrib.auth.decorators import login_required'
                                if import_line not in content:
                                    if 'import ' in content or 'from ' in content:
                                        # 在第一個導入後添加我們的導入
                                        lines = content.splitlines()
                                        for i, line in enumerate(lines):
                                            if 'import ' in line or 'from ' in line:
                                                lines.insert(i + 1, import_line)
                                                break
                                    else:
                                        # 在文件開頭添加導入
                                        lines = content.splitlines()
                                        lines.insert(0, import_line)
                                
                                # 添加裝飾器
                                for i, line in enumerate(lines):
                                    if line.strip() == function_line.strip():
                                        lines.insert(i, '@login_required')
                                        break
                                
                                # 寫回文件
                                new_content = '\n'.join(lines)
                                if write_file(file_path, new_content):
                                    fix_report['fixed_issues'].append({
                                        'issue': issue,
                                        'fix': '添加了 @login_required 裝飾器'
                                    })
                                else:
                                    # 如果寫入失敗，恢復備份
                                    from utils.file_operations import restore_file
                                    restore_file(backup, file_path)
                                    fix_report['unfixed_issues'].append({
                                        'issue': issue,
                                        'reason': '寫入文件失敗'
                                    })
                            else:
                                fix_report['unfixed_issues'].append({
                                    'issue': issue,
                                    'reason': '創建備份失敗'
                                })
                        else:
                            fix_report['unfixed_issues'].append({
                                'issue': issue,
                                'reason': '無法識別函數定義'
                            })
                    else:
                        fix_report['unfixed_issues'].append({
                            'issue': issue,
                            'reason': '行號超出文件範圍'
                        })
                else:
                    fix_report['unfixed_issues'].append({
                        'issue': issue,
                        'reason': '沒有有效的行號'
                    })
            else:
                # 其他身份驗證問題需要手動修復
                fix_report['manual_fixes_needed'].append({
                    'issue': issue,
                    'fix_suggestion': '檢查授權機制並實施適當的保護'
            })

    def _fix_input_validation_issues(self, issues: List[Dict[str, Any]], fix_report: Dict[str, Any], auto_fix: bool) -> None:
        """
        修復輸入驗證問題
        
        Args:
            issues: 輸入驗證問題列表
            fix_report: 修復報告
            auto_fix: 是否自動修復
        """
        from utils.file_operations import read_file, write_file, backup_file
        
        for issue in issues:
            issue_type = issue.get('type', '')
            file_path = issue.get('file', '')
            
            if not file_path or not os.path.exists(file_path):
                fix_report['unfixed_issues'].append({
                    'issue': issue,
                    'reason': '找不到文件'
                })
                continue
            
            # 根據問題類型提供修復建議
            if issue_type == 'sql_injection':
                fix_report['manual_fixes_needed'].append({
                    'issue': issue,
                    'fix_suggestion': '使用參數化查詢替代字符串拼接。例如使用 cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])'
                })
            
            elif issue_type == 'xss':
                fix_report['manual_fixes_needed'].append({
                    'issue': issue,
                    'fix_suggestion': '始終轉義用戶提供的內容，使用 escape() 或框架提供的自動轉義功能'
                })
                
            elif issue_type == 'insecure_deserialization':
                fix_report['manual_fixes_needed'].append({
                    'issue': issue,
                    'fix_suggestion': '避免使用 pickle 反序列化不受信任的數據；使用 JSON 或其他安全的反序列化方法'
                })
                
            elif issue_type == 'missing_validation' and auto_fix:
                # 嘗試根據框架添加基本的數據驗證
                content = read_file(file_path)
                
                if self.framework == 'django':
                    # 為 Django 添加表單驗證
                    if 'request.POST' in content or 'request.data' in content:
                        # 已經有問題，需要添加表單驗證
                        # 這可能需要更複雜的代碼分析，這裡只提供建議
                        fix_report['manual_fixes_needed'].append({
                            'issue': issue,
                            'fix_suggestion': '添加 Django 表單或 DRF 序列化器進行數據驗證'
                        })
                
                elif self.framework == 'flask':
                    # 為 Flask 添加請求數據驗證
                    if 'request.form' in content or 'request.json' in content:
                        fix_report['manual_fixes_needed'].append({
                            'issue': issue,
                            'fix_suggestion': '使用 Flask-WTF 或 marshmallow 進行輸入驗證'
                        })
                else:
                    fix_report['unfixed_issues'].append({
                        'issue': issue,
                        'reason': '未支援的框架或自動修復'
                    })
            else:
                fix_report['unfixed_issues'].append({
                    'issue': issue,
                    'reason': '不支援自動修復此類型問題'
                })

        def _fix_data_exposure_issues(self, issues: List[Dict[str, Any]], fix_report: Dict[str, Any], auto_fix: bool) -> None:
            """
            修復數據曝露問題
            
            Args:
                issues: 數據曝露問題列表
                fix_report: 修復報告
                auto_fix: 是否自動修復
            """
            from utils.file_operations import read_file, write_file, backup_file
            
            for issue in issues:
                issue_type = issue.get('type', '')
                file_path = issue.get('file', '')
                
                if not file_path or not os.path.exists(file_path):
                    fix_report['unfixed_issues'].append({
                        'issue': issue,
                        'reason': '找不到文件'
                    })
                    continue
                
                # 根據問題類型提供修復建議
                if issue_type == 'sensitive_data_exposure':
                    fix_report['manual_fixes_needed'].append({
                        'issue': issue,
                        'fix_suggestion': '避免在響應中包含敏感字段，或確保對這些字段進行適當的隱藏或混淆'
                    })
                    
                elif issue_type == 'missing_security_headers' and auto_fix and self.framework == 'django':
                    # 嘗試為 Django 設置添加安全標頭
                    content = read_file(file_path)
                    
                    if 'settings.py' in file_path and 'MIDDLEWARE' in content:
                        # 備份文件
                        backup = backup_file(file_path)
                        if backup:
                            # 添加安全標頭中間件
                            middleware_to_add = "    'django.middleware.security.SecurityMiddleware',"
                            
                            # 看看是否已包含
                            if middleware_to_add not in content:
                                lines = content.splitlines()
                                for i, line in enumerate(lines):
                                    if 'MIDDLEWARE' in line and '[' in line:
                                        # 在中間件列表開頭添加安全中間件
                                        lines.insert(i + 1, middleware_to_add)
                                        break
                                
                                # 添加安全設置
                                security_settings = """
        # 安全標頭設置
        SECURE_CONTENT_TYPE_NOSNIFF = True
        SECURE_BROWSER_XSS_FILTER = True
        X_FRAME_OPTIONS = 'DENY'
        """
                                lines.append(security_settings)
                                
                                # 寫回文件
                                new_content = '\n'.join(lines)
                                if write_file(file_path, new_content):
                                    fix_report['fixed_issues'].append({
                                        'issue': issue,
                                        'fix': '添加了安全中間件和標頭配置'
                                    })
                                else:
                                    # 如果寫入失敗，恢復備份
                                    from utils.file_operations import restore_file
                                    restore_file(backup, file_path)
                                    fix_report['unfixed_issues'].append({
                                        'issue': issue,
                                        'reason': '寫入文件失敗'
                                    })
                            else:
                                fix_report['unfixed_issues'].append({
                                    'issue': issue,
                                    'reason': '安全中間件已存在'
                                })
                        else:
                            fix_report['unfixed_issues'].append({
                                'issue': issue,
                                'reason': '創建備份失敗'
                            })
                    else:
                        fix_report['manual_fixes_needed'].append({
                            'issue': issue,
                            'fix_suggestion': '添加必要的安全 HTTP 標頭'
                        })
                        
                elif issue_type == 'insecure_direct_object_reference':
                    fix_report['manual_fixes_needed'].append({
                        'issue': issue,
                        'fix_suggestion': '實施授權檢查以確保用戶只能訪問他們有權訪問的數據'
                    })
                    
                elif issue_type == 'debug_enabled' and auto_fix:
                    # 嘗試禁用調試模式
                    content = read_file(file_path)
                    line_num = issue.get('line', 0)
                    
                    if 'DEBUG = True' in content:
                        # 備份文件
                        backup = backup_file(file_path)
                        if backup:
                            # 將 DEBUG = True 替換為 DEBUG = False
                            new_content = content.replace('DEBUG = True', 'DEBUG = False')
                            
                            # 寫回文件
                            if write_file(file_path, new_content):
                                fix_report['fixed_issues'].append({
                                    'issue': issue,
                                    'fix': '禁用了調試模式'
                                })
                            else:
                                # 如果寫入失敗，恢復備份
                                from utils.file_operations import restore_file
                                restore_file(backup, file_path)
                                fix_report['unfixed_issues'].append({
                                    'issue': issue,
                                    'reason': '寫入文件失敗'
                                })
                        else:
                            fix_report['unfixed_issues'].append({
                                'issue': issue,
                                'reason': '創建備份失敗'
                            })
                    else:
                        fix_report['unfixed_issues'].append({
                            'issue': issue,
                            'reason': '無法找到 DEBUG = True'
                        })
                        
                else:
                    fix_report['unfixed_issues'].append({
                        'issue': issue,
                        'reason': '不支援自動修復此類型問題'
                    })

        def _fix_infrastructure_issues(self, issues: List[Dict[str, Any]], fix_report: Dict[str, Any], auto_fix: bool) -> None:
            """
            修復基礎設施問題
            
            Args:
                issues: 基礎設施問題列表
                fix_report: 修復報告
                auto_fix: 是否自動修復
            """
            from utils.file_operations import read_file, write_file, backup_file
            
            for issue in issues:
                issue_type = issue.get('type', '')
                file_path = issue.get('file', '')
                
                if not file_path or not os.path.exists(file_path):
                    fix_report['unfixed_issues'].append({
                        'issue': issue,
                        'reason': '找不到文件'
                    })
                    continue
                
                # 根據問題類型提供修復建議
                if issue_type == 'insecure_cors':
                    fix_report['manual_fixes_needed'].append({
                        'issue': issue,
                        'fix_suggestion': '限制 CORS 設置為特定的可信來源，避免使用 * 通配符'
                    })
                    
                elif issue_type == 'insecure_cookies':
                    fix_report['manual_fixes_needed'].append({
                        'issue': issue,
                        'fix_suggestion': '設置 cookie 的 Secure 和 HttpOnly 標誌'
                    })
                    
                elif issue_type == 'missing_rate_limiting':
                    if self.framework == 'django':
                        fix_report['manual_fixes_needed'].append({
                            'issue': issue,
                            'fix_suggestion': '使用 Django REST Framework 的限流類，配置 DEFAULT_THROTTLE_CLASSES 和 DEFAULT_THROTTLE_RATES'
                        })
                    elif self.framework == 'flask':
                        fix_report['manual_fixes_needed'].append({
                            'issue': issue,
                            'fix_suggestion': '安裝並配置 Flask-Limiter 進行速率限制'
                        })
                    elif self.framework == 'fastapi':
                        fix_report['manual_fixes_needed'].append({
                            'issue': issue,
                            'fix_suggestion': '使用 slowapi 或類似庫實施速率限制'
                        })
                        
                elif issue_type == 'dependency_management':
                    fix_report['manual_fixes_needed'].append({
                        'issue': issue,
                        'fix_suggestion': '固定依賴項到特定版本，定期運行漏洞掃描以更新有安全問題的依賴項'
                    })
                    
                else:
                    fix_report['unfixed_issues'].append({
                        'issue': issue,
                        'reason': '不支援自動修復此類型問題'
                    })
                    
        def generate_security_report(self, analysis_result: Dict[str, Any]) -> str:
            """
            根據安全分析結果生成報告
            
            Args:
                analysis_result: 安全分析結果
                
            Returns:
                安全報告的 Markdown 格式
            """
            if not analysis_result:
                analysis_result = self.analyze_security_issues()
                
            # 創建 Markdown 報告
            report = []
            
            # 標題和總體評分
            report.append(f"# API 安全分析報告\n")
            report.append(f"框架: {self.framework}\n")
            
            # 安全評分
            score = analysis_result['overall_score']
            report.append(f"## 安全評分: {score}/100\n")
            
            if score >= 80:
                report.append("🟢 **優秀** - 安全性良好，但仍有改進空間。\n")
            elif score >= 60:
                report.append("🟠 **一般** - 存在一些安全問題，需要注意。\n")
            else:
                report.append("🔴 **不佳** - 存在重大安全問題，需要立即修復。\n")
            
            # 關鍵問題摘要
            report.append(f"## 關鍵問題\n")
            critical_issues_count = analysis_result['critical_issues_count']
            report.append(f"發現 {critical_issues_count} 個高風險問題。\n")
            
            # 問題細節
            issue_categories = [
                ('auth_issues', '身份驗證問題'),
                ('input_validation_issues', '輸入驗證問題'),
                ('data_exposure_issues', '數據曝露問題'),
                ('infrastructure_issues', '基礎設施問題')
            ]
            
            for key, title in issue_categories:
                issues = analysis_result.get(key, [])
                if issues:
                    report.append(f"## {title} ({len(issues)})\n")
                    
                    for i, issue in enumerate(issues, 1):
                        severity = issue.get('severity', 'medium')
                        severity_icon = '🔴' if severity == 'high' else '🟠' if severity == 'medium' else '🟡'
                        
                        report.append(f"### {i}. {severity_icon} {issue.get('type', '未知問題類型')}\n")
                        report.append(f"**描述**: {issue.get('description', '無描述')}\n")
                        report.append(f"**文件**: {issue.get('file', '未知')}\n")
                        
                        if 'line' in issue:
                            report.append(f"**行號**: {issue['line']}\n")
                            
                        if 'solution' in issue:
                            report.append(f"**解決方案**: {issue['solution']}\n")
                            
                        report.append("\n")
            
            # 安全建議
            report.append("## 安全建議\n")
            
            # 身份驗證建議
            auth_issues = analysis_result.get('auth_issues', [])
            if any(issue.get('type') == 'missing_auth' for issue in auth_issues):
                report.append("- 為所有敏感端點實施適當的身份驗證機制\n")
            if any(issue.get('type') == 'hardcoded_secret' for issue in auth_issues):
                report.append("- 移除代碼中的硬編碼機密，使用環境變數或安全存儲\n")
                
            # 輸入驗證建議
            input_issues = analysis_result.get('input_validation_issues', [])
            if any(issue.get('type') == 'sql_injection' for issue in input_issues):
                report.append("- 使用參數化查詢而非字符串拼接來防止 SQL 注入\n")
            if any(issue.get('type') == 'xss' for issue in input_issues):
                report.append("- 始終轉義用戶提供的內容以防止 XSS 攻擊\n")
            if any(issue.get('type') == 'missing_validation' for issue in input_issues):
                report.append("- 對所有用戶輸入進行徹底驗證\n")
                
            # 數據曝露建議
            exposure_issues = analysis_result.get('data_exposure_issues', [])
            if any(issue.get('type') == 'sensitive_data_exposure' for issue in exposure_issues):
                report.append("- 避免在響應中包含敏感數據\n")
            if any(issue.get('type') == 'missing_security_headers' for issue in exposure_issues):
                report.append("- 添加適當的安全 HTTP 標頭\n")
            if any(issue.get('type') == 'debug_enabled' for issue in exposure_issues):
                report.append("- 在生產環境中禁用調試模式\n")
                
            # 基礎設施建議
            infra_issues = analysis_result.get('infrastructure_issues', [])
            if any(issue.get('type') == 'insecure_cookies' for issue in infra_issues):
                report.append("- 設置 cookie 的 Secure 和 HttpOnly 標誌\n")
            if any(issue.get('type') == 'missing_rate_limiting' for issue in infra_issues):
                report.append("- 實施 API 速率限制以防止濫用\n")
            if any(issue.get('type') == 'dependency_management' for issue in infra_issues):
                report.append("- 維護依賴項並定期進行漏洞掃描\n")
                
            # 返回完整報告
            return '\n'.join(report)
        
    def generate_security_report(self, analysis_result: Dict[str, Any]) -> str:
        """
        根據安全分析結果生成報告
        
        Args:
            analysis_result: 安全分析結果
                
        Returns:
            安全報告的 Markdown 格式
        """
        if not analysis_result:
            analysis_result = self.analyze_security_issues()
                
        # 創建 Markdown 報告
        report = []
        
        # 標題和總體評分
        report.append(f"# API 安全分析報告\n")
        report.append(f"框架: {self.framework}\n")
        
        # 安全評分
        score = analysis_result['overall_score']
        report.append(f"## 安全評分: {score}/100\n")
        
        if score >= 80:
            report.append("🟢 **優秀** - 安全性良好，但仍有改進空間。\n")
        elif score >= 60:
            report.append("🟠 **一般** - 存在一些安全問題，需要注意。\n")
        else:
            report.append("🔴 **不佳** - 存在重大安全問題，需要立即修復。\n")
        
        # 關鍵問題摘要
        report.append(f"## 關鍵問題\n")
        critical_issues_count = analysis_result['critical_issues_count']
        report.append(f"發現 {critical_issues_count} 個高風險問題。\n")
        
        # 問題細節
        issue_categories = [
            ('auth_issues', '身份驗證問題'),
            ('input_validation_issues', '輸入驗證問題'),
            ('data_exposure_issues', '數據曝露問題'),
            ('infrastructure_issues', '基礎設施問題')
        ]
        
        for key, title in issue_categories:
            issues = analysis_result.get(key, [])
            if issues:
                report.append(f"## {title} ({len(issues)})\n")
                
                for i, issue in enumerate(issues, 1):
                    severity = issue.get('severity', 'medium')
                    severity_icon = '🔴' if severity == 'high' else '🟠' if severity == 'medium' else '🟡'
                    
                    report.append(f"### {i}. {severity_icon} {issue.get('type', '未知問題類型')}\n")
                    report.append(f"**描述**: {issue.get('description', '無描述')}\n")
                    report.append(f"**文件**: {issue.get('file', '未知')}\n")
                    
                    if 'line' in issue:
                        report.append(f"**行號**: {issue['line']}\n")
                        
                    if 'solution' in issue:
                        report.append(f"**解決方案**: {issue['solution']}\n")
                        
                    report.append("\n")
        
        # 安全建議
        report.append("## 安全建議\n")
        
        # 身份驗證建議
        auth_issues = analysis_result.get('auth_issues', [])
        if any(issue.get('type') == 'missing_auth' for issue in auth_issues):
            report.append("- 為所有敏感端點實施適當的身份驗證機制\n")
        if any(issue.get('type') == 'hardcoded_secret' for issue in auth_issues):
            report.append("- 移除代碼中的硬編碼機密，使用環境變數或安全存儲\n")
            
        # 輸入驗證建議
        input_issues = analysis_result.get('input_validation_issues', [])
        if any(issue.get('type') == 'sql_injection' for issue in input_issues):
            report.append("- 使用參數化查詢而非字符串拼接來防止 SQL 注入\n")
        if any(issue.get('type') == 'xss' for issue in input_issues):
            report.append("- 始終轉義用戶提供的內容以防止 XSS 攻擊\n")
        if any(issue.get('type') == 'missing_validation' for issue in input_issues):
            report.append("- 對所有用戶輸入進行徹底驗證\n")
            
        # 數據曝露建議
        exposure_issues = analysis_result.get('data_exposure_issues', [])
        if any(issue.get('type') == 'sensitive_data_exposure' for issue in exposure_issues):
            report.append("- 避免在響應中包含敏感數據\n")
        if any(issue.get('type') == 'missing_security_headers' for issue in exposure_issues):
            report.append("- 添加適當的安全 HTTP 標頭\n")
        if any(issue.get('type') == 'debug_enabled' for issue in exposure_issues):
            report.append("- 在生產環境中禁用調試模式\n")
            
        # 基礎設施建議
        infra_issues = analysis_result.get('infrastructure_issues', [])
        if any(issue.get('type') == 'insecure_cookies' for issue in infra_issues):
            report.append("- 設置 cookie 的 Secure 和 HttpOnly 標誌\n")
        if any(issue.get('type') == 'missing_rate_limiting' for issue in infra_issues):
            report.append("- 實施 API 速率限制以防止濫用\n")
        if any(issue.get('type') == 'dependency_management' for issue in infra_issues):
            report.append("- 維護依賴項並定期進行漏洞掃描\n")
            
        # 返回完整報告
        return '\n'.join(report)