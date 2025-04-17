"""
RESTful API 設計分析和改進工具 - 識別和改進 API 的 RESTful 設計
"""
import ast
import os
import re
from typing import Dict, List, Tuple, Optional, Any

from utils.file_operations import read_file, write_file
from api_analyzer.endpoint_analyzer import EndpointAnalyzer
from api_analyzer.schema_extractor import SchemaExtractor
from llm_integration.llm_client import LLMClient


class RESTfulDesignAnalyzer:
    """識別和改進 API 的 RESTful 設計"""
    
    def __init__(self, project_path: str, framework: Optional[str] = None):
        """
        初始化 RESTful 設計分析器
        
        Args:
            project_path: API 專案的路徑
            framework: 專案使用的框架（如果已知）
        """
        self.project_path = project_path
        self.framework = framework
        self.endpoint_analyzer = EndpointAnalyzer(project_path)
        self.schema_extractor = SchemaExtractor(project_path)
        
        # 如果未指定框架，則檢測框架
        if not self.framework:
            self.framework = self.endpoint_analyzer.detect_framework()
    
    def analyze_restful_design(self) -> Dict[str, Any]:
        """
        分析 API 的 RESTful 設計
        
        Returns:
            RESTful 設計分析結果
        """
        # 初始化分析結果
        analysis_result = {
            'endpoints': [],
            'restful_issues': [],
            'restful_score': 0,
            'improvement_suggestions': []
        }
        
        # 獲取所有端點
        endpoints = self.endpoint_analyzer.analyze_endpoints()
        analysis_result['endpoints'] = endpoints
        
        # 分析 RESTful 設計問題
        self._analyze_endpoint_naming(endpoints, analysis_result)
        self._analyze_http_methods(endpoints, analysis_result)
        self._analyze_resource_hierarchy(endpoints, analysis_result)
        self._analyze_response_status_codes(endpoints, analysis_result)
        self._analyze_content_negotiation(endpoints, analysis_result)
        
        # 計算 RESTful 設計評分
        analysis_result['restful_score'] = self._calculate_restful_score(analysis_result)
        
        # 生成改進建議
        analysis_result['improvement_suggestions'] = self._generate_improvement_suggestions(analysis_result)
        
        return analysis_result
    
    def _analyze_endpoint_naming(self, endpoints: List[Dict[str, Any]], analysis_result: Dict[str, Any]) -> None:
        """
        分析端點命名是否符合 RESTful 設計原則
        
        Args:
            endpoints: 端點列表
            analysis_result: 分析結果字典
        """
        for endpoint in endpoints:
            route = endpoint.get('route', '')
            
            # 檢查是否使用動詞而非名詞
            verb_patterns = [
                r'/get[A-Z]', r'/create[A-Z]', r'/update[A-Z]', r'/delete[A-Z]',
                r'/add[A-Z]', r'/remove[A-Z]', r'/list[A-Z]', r'/fetch[A-Z]'
            ]
            
            for pattern in verb_patterns:
                if re.search(pattern, route, re.IGNORECASE):
                    analysis_result['restful_issues'].append({
                        'type': 'endpoint_naming',
                        'severity': 'medium',
                        'description': f"端點 '{route}' 使用了動詞而非資源名詞",
                        'endpoint': route,
                        'suggestion': "使用資源名詞而非動詞，並依靠 HTTP 方法表達操作",
                        'file': endpoint.get('file', ''),
                        'line': endpoint.get('line', 0)
                    })
                    break
            
            # 檢查是否使用複數名詞表示集合
            if '/user/' in route and not '/users/' in route:
                analysis_result['restful_issues'].append({
                    'type': 'endpoint_naming',
                    'severity': 'low',
                    'description': f"端點 '{route}' 使用單數名詞而非複數名詞表示資源集合",
                    'endpoint': route,
                    'suggestion': "使用複數名詞表示資源集合（例如：/users 而非 /user）",
                    'file': endpoint.get('file', ''),
                    'line': endpoint.get('line', 0)
                })
            
            # 檢查是否使用 snake_case 或 kebab-case
            if '_' in route and '-' not in route:
                analysis_result['restful_issues'].append({
                    'type': 'endpoint_naming',
                    'severity': 'low',
                    'description': f"端點 '{route}' 使用 snake_case 而非 kebab-case",
                    'endpoint': route,
                    'suggestion': "考慮使用 kebab-case （例如：/user-profiles 而非 /user_profiles）",
                    'file': endpoint.get('file', ''),
                    'line': endpoint.get('line', 0)
                })
    
    def _analyze_http_methods(self, endpoints: List[Dict[str, Any]], analysis_result: Dict[str, Any]) -> None:
        """
        分析 HTTP 方法使用是否符合 RESTful 設計原則
        
        Args:
            endpoints: 端點列表
            analysis_result: 分析結果字典
        """
        # 檢查各端點的 HTTP 方法使用
        for endpoint in endpoints:
            route = endpoint.get('route', '')
            methods = endpoint.get('methods', [])
            
            # 檢查是否存在不符合 RESTful 原則的方法使用
            if 'GET' in methods:
                # GET 應該是安全和冪等的，不應修改資源
                if any(verb in route.lower() for verb in ['create', 'update', 'delete', 'modify', 'remove']):
                    analysis_result['restful_issues'].append({
                        'type': 'http_method',
                        'severity': 'high',
                        'description': f"端點 '{route}' 使用 GET 方法但路徑暗示資源修改操作",
                        'endpoint': route,
                        'suggestion': "使用 POST, PUT 或 DELETE 方法進行資源修改操作",
                        'file': endpoint.get('file', ''),
                        'line': endpoint.get('line', 0)
                    })
            
            # 檢查是否使用 POST 進行更新操作
            if 'POST' in methods and 'update' in route.lower():
                analysis_result['restful_issues'].append({
                    'type': 'http_method',
                    'severity': 'medium',
                    'description': f"端點 '{route}' 使用 POST 方法進行更新操作",
                    'endpoint': route,
                    'suggestion': "使用 PUT 或 PATCH 方法進行資源更新操作",
                    'file': endpoint.get('file', ''),
                    'line': endpoint.get('line', 0)
                })
            
            # 檢查是否有包含操作動詞的端點沒有用適當的 HTTP 方法
            if 'delete' in route.lower() and 'DELETE' not in methods:
                analysis_result['restful_issues'].append({
                    'type': 'http_method',
                    'severity': 'medium',
                    'description': f"端點 '{route}' 包含 'delete' 但沒有使用 DELETE 方法",
                    'endpoint': route,
                    'suggestion': "使用 DELETE 方法進行刪除操作",
                    'file': endpoint.get('file', ''),
                    'line': endpoint.get('line', 0)
                })
    
    def _analyze_resource_hierarchy(self, endpoints: List[Dict[str, Any]], analysis_result: Dict[str, Any]) -> None:
        """
        分析資源層次結構是否符合 RESTful 設計原則
        
        Args:
            endpoints: 端點列表
            analysis_result: 分析結果字典
        """
        # 構建資源樹
        resource_tree = {}
        
        for endpoint in endpoints:
            route = endpoint.get('route', '')
            
            # 忽略靜態資源、文檔等非 API 端點
            if any(pattern in route for pattern in ['/static/', '/docs/', '/swagger/', '/redoc/']):
                continue
            
            # 分割路徑
            parts = [p for p in route.split('/') if p and not '{' in p and not '}' in p]
            
            # 將路徑添加到資源樹
            current = resource_tree
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        # 檢查資源層次是否過深
        def check_depth(tree, path="", depth=0):
            if depth > 3:  # 一般建議資源層次不超過 3 層
                analysis_result['restful_issues'].append({
                    'type': 'resource_hierarchy',
                    'severity': 'medium',
                    'description': f"資源路徑 '{path}' 層次過深（{depth} 層）",
                    'suggestion': "考慮扁平化資源結構或使用查詢參數代替某些路徑段",
                })
            
            for resource, subtree in tree.items():
                new_path = f"{path}/{resource}" if path else f"/{resource}"
                check_depth(subtree, new_path, depth + 1)
        
        check_depth(resource_tree)
        
        # 檢查是否有不一致的複數/單數用法
        resources = {}
        
        for endpoint in endpoints:
            route = endpoint.get('route', '')
            parts = route.split('/')
            
            for part in parts:
                if part and not '{' in part and not '}' in part:
                    resources[part] = resources.get(part, 0) + 1
        
        # 識別可能的單複數不一致
        singular_plural_pairs = []
        
        for resource in resources.keys():
            # 檢查常見的英文複數形式
            if resource.endswith('s') and resource[:-1] in resources:
                singular_plural_pairs.append((resource[:-1], resource))
            elif resource.endswith('ies') and resource[:-3] + 'y' in resources:
                singular_plural_pairs.append((resource[:-3] + 'y', resource))
        
        for singular, plural in singular_plural_pairs:
            analysis_result['restful_issues'].append({
                'type': 'resource_naming',
                'severity': 'medium',
                'description': f"資源命名不一致：同時使用了單數形式 '{singular}' 和複數形式 '{plural}'",
                'suggestion': f"統一使用複數形式 '{plural}' 表示資源集合",
            })
    
    def _analyze_response_status_codes(self, endpoints: List[Dict[str, Any]], analysis_result: Dict[str, Any]) -> None:
        """
        分析回應狀態碼使用是否符合 RESTful 設計原則
        
        Args:
            endpoints: 端點列表
            analysis_result: 分析結果字典
        """
        for endpoint in endpoints:
            file_path = endpoint.get('file', '')
            if not file_path or not os.path.exists(file_path):
                continue
            
            # 讀取檔案內容
            content = read_file(file_path)
            if not content:
                continue
            
            # 檢查是否使用了適當的狀態碼
            route = endpoint.get('route', '')
            methods = endpoint.get('methods', [])
            line_no = endpoint.get('line', 0)
            
            # 提取相關函數/方法的內容
            func_content = self._extract_function_content(content, line_no)
            if not func_content:
                continue
            
            # 檢查常見的狀態碼使用問題
            common_status_codes = {
                200: 'GET, 成功返回',
                201: 'POST, 成功創建',
                204: 'DELETE, 成功刪除',
                400: '客戶端錯誤',
                401: '未授權',
                403: '禁止訪問',
                404: '資源未找到',
                405: '方法不允許',
                500: '服務器錯誤'
            }
            
            # 檢查是否有回應但沒有指定狀態碼
            if ('return' in func_content and 
                not re.search(r'status[_=](?:code|code=)?[ ]*=[ ]*\d+', func_content, re.IGNORECASE) and
                not re.search(r'\.status\([ ]*\d+[ ]*\)', func_content)):
                analysis_result['restful_issues'].append({
                    'type': 'status_code',
                    'severity': 'medium',
                    'description': f"端點 '{route}' 可能沒有明確指定回應狀態碼",
                    'endpoint': route,
                    'suggestion': "明確指定適當的 HTTP 狀態碼",
                    'file': file_path,
                    'line': line_no
                })
            
            # 檢查是否有創建資源的 POST 但沒有返回 201
            if 'POST' in methods and 'create' in route.lower() and '201' not in func_content:
                analysis_result['restful_issues'].append({
                    'type': 'status_code',
                    'severity': 'low',
                    'description': f"創建資源的 POST 端點 '{route}' 可能沒有返回 201 Created 狀態碼",
                    'endpoint': route,
                    'suggestion': "創建資源時返回 201 Created 狀態碼",
                    'file': file_path,
                    'line': line_no
                })
            
            # 檢查是否有刪除資源的 DELETE 但沒有返回 204
            if 'DELETE' in methods and '204' not in func_content:
                analysis_result['restful_issues'].append({
                    'type': 'status_code',
                    'severity': 'low',
                    'description': f"刪除資源的 DELETE 端點 '{route}' 可能沒有返回 204 No Content 狀態碼",
                    'endpoint': route,
                    'suggestion': "刪除資源時返回 204 No Content 狀態碼",
                    'file': file_path,
                    'line': line_no
                })
    
    def _analyze_content_negotiation(self, endpoints: List[Dict[str, Any]], analysis_result: Dict[str, Any]) -> None:
        """
        分析內容協商是否符合 RESTful 設計原則
        
        Args:
            endpoints: 端點列表
            analysis_result: 分析結果字典
        """
        for endpoint in endpoints:
            file_path = endpoint.get('file', '')
            if not file_path or not os.path.exists(file_path):
                continue
            
            # 讀取檔案內容
            content = read_file(file_path)
            if not content:
                continue
            
            # 檢查是否支持不同的內容類型
            route = endpoint.get('route', '')
            line_no = endpoint.get('line', 0)
            
            # 提取相關函數/方法的內容
            func_content = self._extract_function_content(content, line_no)
            if not func_content:
                continue
            
            # 檢查是否有處理 Accept 頭
            if 'application/json' in func_content and 'application/xml' not in func_content:
                # 检查是否有 content-type 或 accept 的处理逻辑
                has_content_type_handling = (
                    re.search(r'content[-_]type', func_content, re.IGNORECASE) or
                    re.search(r'accept', func_content, re.IGNORECASE)
                )
                
                if not has_content_type_handling:
                    analysis_result['restful_issues'].append({
                        'type': 'content_negotiation',
                        'severity': 'low',
                        'description': f"端點 '{route}' 可能只支持 JSON 格式而沒有內容協商",
                        'endpoint': route,
                        'suggestion': "考慮支持多種內容類型（如 JSON 和 XML）並處理 Accept 頭",
                        'file': file_path,
                        'line': line_no
                    })
            
            # 檢查是否有設置正確的 Content-Type 回應頭
            if 'return' in func_content and 'content-type' not in func_content.lower():
                analysis_result['restful_issues'].append({
                    'type': 'content_negotiation',
                    'severity': 'low',
                    'description': f"端點 '{route}' 可能沒有明確設置 Content-Type 回應頭",
                    'endpoint': route,
                    'suggestion': "明確設置適當的 Content-Type 回應頭",
                    'file': file_path,
                    'line': line_no
                })
    
    def _extract_function_content(self, file_content: str, line_no: int) -> str:
        """
        提取特定行號附近的函數/方法內容
        
        Args:
            file_content: 文件內容
            line_no: 行號
            
        Returns:
            函數/方法的內容
        """
        lines = file_content.splitlines()
        
        # 確保行號有效
        if line_no <= 0 or line_no > len(lines):
            return ""
        
        # 向上搜尋函數/方法定義
        func_start = line_no
        while func_start > 0:
            if re.match(r'^\s*(?:async\s+)?def\s+\w+\s*\(', lines[func_start - 1]):
                break
            func_start -= 1
        
        if func_start == 0:
            return ""
        
        # 向下找到函數/方法結束
        func_end = line_no
        indent_level = None
        while func_end < len(lines):
            if indent_level is None:
                match = re.match(r'^(\s*)', lines[func_start - 1])
                if match:
                    indent_level = len(match.group(1))
            else:
                # 檢查非空行的縮進
                if lines[func_end].strip() and not re.match(r'^\s*#', lines[func_end]):
                    match = re.match(r'^(\s*)', lines[func_end])
                    if match and len(match.group(1)) <= indent_level:
                        break
            func_end += 1
        
        # 提取函數/方法內容
        func_content = "\n".join(lines[func_start - 1:func_end])
        return func_content
    
    def _calculate_restful_score(self, analysis_result: Dict[str, Any]) -> int:
        """
        計算 RESTful 設計評分
        
        Args:
            analysis_result: 分析結果字典
            
        Returns:
            RESTful 設計評分 (0-100)
        """
        # 基礎分數
        base_score = 100
        
        # 根據問題扣分
        severity_penalties = {
            'high': 15,
            'medium': 10,
            'low': 5
        }
        
        for issue in analysis_result['restful_issues']:
            severity = issue.get('severity', 'low')
            base_score -= severity_penalties.get(severity, 5)
        
        # 確保分數在 0-100 範圍內
        return max(0, min(100, base_score))
    
    def _generate_improvement_suggestions(self, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成改進建議
        
        Args:
            analysis_result: 分析結果字典
            
        Returns:
            改進建議列表
        """
        suggestions = []
        
        # 按問題類型分組的問題
        issues_by_type = {}
        for issue in analysis_result['restful_issues']:
            issue_type = issue.get('type', 'other')
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        # 為每種問題類型生成建議
        for issue_type, issues in issues_by_type.items():
            if issue_type == 'endpoint_naming':
                suggestions.append(self._generate_endpoint_naming_suggestion(issues))
            elif issue_type == 'http_method':
                suggestions.append(self._generate_http_method_suggestion(issues))
            elif issue_type == 'resource_hierarchy':
                suggestions.append(self._generate_resource_hierarchy_suggestion(issues))
            elif issue_type == 'resource_naming':
                suggestions.append(self._generate_resource_naming_suggestion(issues))
            elif issue_type == 'status_code':
                suggestions.append(self._generate_status_code_suggestion(issues))
            elif issue_type == 'content_negotiation':
                suggestions.append(self._generate_content_negotiation_suggestion(issues))
        
        # 添加通用的 RESTful 最佳實踐建議
        if analysis_result['restful_score'] < 80:
            suggestions.append({
                'title': 'RESTful API 最佳實踐',
                'description': '實施 RESTful API 設計的常見最佳實踐',
                'priority': 'medium',
                'issues': [],
                'implementation_guide': self._get_restful_best_practices_guide()
            })
        
        return suggestions
    
    def _generate_endpoint_naming_suggestion(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成端點命名建議
        
        Args:
            issues: 問題列表
            
        Returns:
            改進建議
        """
        return {
            'title': '改進 API 端點命名',
            'description': '使 API 端點命名符合 RESTful 設計原則',
            'priority': 'high' if any(issue.get('severity') == 'high' for issue in issues) else 'medium',
            'issues': issues,
            'implementation_guide': {
                'principles': [
                    '使用資源名詞而非動詞',
                    '使用複數名詞表示資源集合',
                    '一致使用 kebab-case 或 camelCase',
                    '使用清晰的資源層次結構'
                ],
                'examples': {
                    'bad': [
                        '/getUserProfile', 
                        '/createItem', 
                        '/api/update_user'
                    ],
                    'good': [
                        '/users/{id}',
                        '/items',
                        '/api/users/{id}'
                    ]
                },
                'framework_examples': self._get_framework_examples('endpoint_naming')
            }
        }
    
    def _generate_http_method_suggestion(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成 HTTP 方法使用建議
        
        Args:
            issues: 問題列表
            
        Returns:
            改進建議
        """
        return {
            'title': '正確使用 HTTP 方法',
            'description': '確保 HTTP 方法與資源操作一致',
            'priority': 'high' if any(issue.get('severity') == 'high' for issue in issues) else 'medium',
            'issues': issues,
            'implementation_guide': {
                'principles': [
                    'GET: 獲取資源 (安全、冪等)',
                    'POST: 創建資源',
                    'PUT: 完全替換資源 (冪等)',
                    'PATCH: 部分更新資源',
                    'DELETE: 刪除資源 (冪等)'
                ],
                'examples': {
                    'bad': [
                        'GET /users/create',
                        'POST /users/1/update',
                        'GET /users/1/delete'
                    ],
                    'good': [
                        'POST /users',
                        'PUT /users/1 或 PATCH /users/1',
                        'DELETE /users/1'
                    ]
                },
                'framework_examples': self._get_framework_examples('http_method')
            }
        }
    
    def _generate_resource_hierarchy_suggestion(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成資源層次結構建議
        
        Args:
            issues: 問題列表
            
        Returns:
            改進建議
        """
        return {
            'title': '優化資源層次結構',
            'description': '確保 API 資源層次結構清晰合理',
            'priority': 'medium',
            'issues': issues,
            'implementation_guide': {
                'principles': [
                    '保持資源層次結構扁平',
                    '通常不超過 3 層',
                    '使用查詢參數表示過濾、排序和分頁',
                    '使用子資源表示關係'
                ],
                'examples': {
                    'bad': [
                        '/api/departments/1/teams/2/projects/3/tasks/4',
                    ],
                    'good': [
                        '/api/tasks?project=3',
                        '/api/projects/3/tasks'
                    ]
                }
            }
        }
    
    def _generate_resource_naming_suggestion(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成資源命名建議
        
        Args:
            issues: 問題列表
            
        Returns:
            改進建議
        """
        return {
            'title': '統一資源命名約定',
            'description': '確保 API 資源命名一致',
            'priority': 'medium',
            'issues': issues,
            'implementation_guide': {
                'principles': [
                    '一致使用複數名詞表示資源集合',
                    '一致使用單一命名約定 (kebab-case 或 camelCase)',
                    '避免使用特殊字符',
                    '考慮使用版本前綴'
                ],
                'examples': {
                    'bad': [
                        '/user 與 /companies',
                        '/userProfiles 與 /user-settings'
                    ],
                    'good': [
                        '/users 與 /companies',
                        '/user-profiles 與 /user-settings'
                    ]
                }
            }
        }
    
    def _generate_status_code_suggestion(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成狀態碼使用建議
        
        Args:
            issues: 問題列表
            
        Returns:
            改進建議
        """
        return {
            'title': '正確使用 HTTP 狀態碼',
            'description': '確保 API 回應使用適當的 HTTP 狀態碼',
            'priority': 'high' if any(issue.get('severity') == 'high' for issue in issues) else 'medium',
            'issues': issues,
            'implementation_guide': {
                'principles': [
                    '使用標準 HTTP 狀態碼',
                    '適當分類：2xx 成功、4xx 客戶端錯誤、5xx 服務器錯誤',
                    '為創建資源返回 201 Created',
                    '為刪除資源返回 204 No Content',
                    '為無法找到的資源返回 404 Not Found',
                    '為授權錯誤返回 401 Unauthorized 或 403 Forbidden'
                ],
                'common_codes': {
                    '200 OK': 'GET, 成功返回',
                    '201 Created': 'POST, 成功創建',
                    '204 No Content': 'DELETE, 成功刪除',
                    '400 Bad Request': '客戶端請求有誤',
                    '401 Unauthorized': '未授權',
                    '403 Forbidden': '禁止訪問',
                    '404 Not Found': '資源未找到',
                    '405 Method Not Allowed': '不允許的方法',
                    '500 Internal Server Error': '服務器錯誤'
                },
                'framework_examples': self._get_framework_examples('status_code')
            }
        }
    
    def _generate_content_negotiation_suggestion(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成內容協商建議
        
        Args:
            issues: 問題列表
            
        Returns:
            改進建議
        """
        return {
            'title': '實施內容協商',
            'description': '確保 API 支持適當的內容協商',
            'priority': 'low',
            'issues': issues,
            'implementation_guide': {
                'principles': [
                    '尊重 Accept 頭指定的內容類型',
                    '設置正確的 Content-Type 回應頭',
                    '支持多種內容類型 (如 JSON, XML)',
                    '確保錯誤回應採用相同的格式'
                ],
                'examples': {
                    'request': 'GET /api/users/1\nAccept: application/xml',
                    'response': 'HTTP/1.1 200 OK\nContent-Type: application/xml\n\n<user><id>1</id>...</user>'
                },
                'framework_examples': self._get_framework_examples('content_negotiation')
            }
        }
    
    def _get_restful_best_practices_guide(self) -> Dict[str, Any]:
        """
        獲取 RESTful 最佳實踐指南
        
        Returns:
            RESTful 最佳實踐指南
        """
        return {
            'core_principles': [
                '使用資源命名端點（名詞而非動詞）',
                '使用適當的 HTTP 方法（GET, POST, PUT, PATCH, DELETE）',
                '為資源層次結構制定清晰的策略',
                '正確使用 HTTP 狀態碼',
                '實施適當的內容協商',
                '支持 HATEOAS 以提高可發現性',
                '保持 API 版本控制一致',
                '實施適當的錯誤處理',
                '確保 API 安全'
            ],
            'hateoas_example': {
                'description': 'HATEOAS（超媒體作為應用狀態引擎）允許客戶端通過回應中的鏈接發現可用操作',
                'example': '''{
  "id": 1,
  "name": "John Smith",
  "email": "john@example.com",
  "_links": {
    "self": { "href": "/api/users/1" },
    "profile": { "href": "/api/users/1/profile" },
    "orders": { "href": "/api/users/1/orders" }
  }
}'''
            },
            'versioning_strategies': [
                {
                    'name': 'URL 路徑',
                    'example': '/api/v1/users',
                    'pros': '簡單明確',
                    'cons': '更改版本需要更改 URL'
                },
                {
                    'name': '查詢參數',
                    'example': '/api/users?version=1',
                    'pros': '不更改基本 URL',
                    'cons': '容易被忽略'
                },
                {
                    'name': '請求頭',
                    'example': 'Accept: application/vnd.company.v1+json',
                    'pros': '不污染 URL',
                    'cons': '對開發人員較不明顯'
                }
            ],
            'schema_validation': {
                'description': '使用 JSON Schema 或類似工具驗證請求和回應',
                'benefits': [
                    '提前捕捉錯誤',
                    '自動生成文檔',
                    '提高 API 的一致性和可靠性'
                ]
            }
        }
    
    def _get_framework_examples(self, feature: str) -> Dict[str, str]:
        """
        獲取特定框架的示例代碼
        
        Args:
            feature: 功能類型
            
        Returns:
            框架示例代碼字典
        """
        examples = {}
        
        if feature == 'endpoint_naming':
            if self.framework == 'django':
                examples['django'] = '''
# urls.py - 良好的 RESTful URL 配置
from django.urls import path
from . import views

urlpatterns = [
    # 資源集合 - 複數名詞
    path('api/users/', views.user_list, name='user-list'),
    # 特定資源 - 帶 ID 的複數名詞
    path('api/users/<int:pk>/', views.user_detail, name='user-detail'),
    # 子資源 - 清晰的層次結構
    path('api/users/<int:user_id>/orders/', views.user_orders, name='user-orders'),
]
'''
            elif self.framework == 'flask':
                examples['flask'] = '''
# app.py - 良好的 RESTful 路由
from flask import Flask
app = Flask(__name__)

# 資源集合 - 複數名詞
@app.route('/api/users', methods=['GET', 'POST'])
def users():
    # 實現...

# 特定資源 - 帶 ID 的複數名詞
@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def user(user_id):
    # 實現...

# 子資源 - 清晰的層次結構
@app.route('/api/users/<int:user_id>/orders', methods=['GET'])
def user_orders(user_id):
    # 實現...
'''
            elif self.framework == 'fastapi':
                examples['fastapi'] = '''
# main.py - 良好的 RESTful 端點
from fastapi import FastAPI, APIRouter

app = FastAPI()
router = APIRouter(prefix="/api")

# 資源集合 - 複數名詞
@router.get("/users")
def read_users():
    # 實現...

# 特定資源 - 帶 ID 的複數名詞
@router.get("/users/{user_id}")
def read_user(user_id: int):
    # 實現...

# 子資源 - 清晰的層次結構
@router.get("/users/{user_id}/orders")
def read_user_orders(user_id: int):
    # 實現...

app.include_router(router)
'''
        
        elif feature == 'http_method':
            if self.framework == 'django':
                examples['django'] = '''
# views.py - 正確使用 HTTP 方法
from rest_framework.decorators import api_view
from rest_framework.response import Response

# 資源集合 - GET 獲取列表，POST 創建
@api_view(['GET', 'POST'])
def user_list(request):
    if request.method == 'GET':
        # 獲取用戶列表
        return Response(users)
    elif request.method == 'POST':
        # 創建新用戶
        return Response(new_user, status=201)

# 特定資源 - GET 獲取，PUT 更新，DELETE 刪除
@api_view(['GET', 'PUT', 'DELETE'])
def user_detail(request, pk):
    if request.method == 'GET':
        # 獲取特定用戶
        return Response(user)
    elif request.method == 'PUT':
        # 更新用戶
        return Response(updated_user)
    elif request.method == 'DELETE':
        # 刪除用戶
        return Response(status=204)
'''
            elif self.framework == 'flask':
                examples['flask'] = '''
# app.py - 正確使用 HTTP 方法
from flask import Flask, request, jsonify

app = Flask(__name__)

# 資源集合 - GET 獲取列表，POST 創建
@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        # 獲取用戶列表
        return jsonify(users)
    elif request.method == 'POST':
        # 創建新用戶
        return jsonify(new_user), 201

# 特定資源 - GET 獲取，PUT 更新，DELETE 刪除
@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def user(user_id):
    if request.method == 'GET':
        # 獲取特定用戶
        return jsonify(user)
    elif request.method == 'PUT':
        # 更新用戶
        return jsonify(updated_user)
    elif request.method == 'DELETE':
        # 刪除用戶
        return '', 204
'''
            elif self.framework == 'fastapi':
                examples['fastapi'] = '''
# main.py - 正確使用 HTTP 方法
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

app = FastAPI()
router = APIRouter(prefix="/api")

# GET 獲取列表
@router.get("/users")
def read_users():
    # 獲取用戶列表
    return users

# POST 創建
@router.post("/users", status_code=201)
def create_user(user: User):
    # 創建新用戶
    return new_user

# GET 獲取特定資源
@router.get("/users/{user_id}")
def read_user(user_id: int):
    # 獲取特定用戶
    return user

# PUT 更新
@router.put("/users/{user_id}")
def update_user(user_id: int, user: User):
    # 更新用戶
    return updated_user

# DELETE 刪除
@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    # 刪除用戶
    return None

app.include_router(router)
'''
        
        elif feature == 'status_code':
            if self.framework == 'django':
                examples['django'] = '''
# views.py - 正確使用 HTTP 狀態碼
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

@api_view(['GET', 'POST'])
def user_list(request):
    if request.method == 'GET':
        # 獲取用戶列表
        return Response(users, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        # 創建新用戶
        if valid:
            return Response(new_user, status=status.HTTP_201_CREATED)
        else:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def user_detail(request, pk):
    try:
        user = get_user(pk)
    except UserNotFound:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        return Response(user)
    elif request.method == 'PUT':
        if valid:
            return Response(updated_user)
        else:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        # 刪除用戶
        return Response(status=status.HTTP_204_NO_CONTENT)
'''
            elif self.framework == 'flask':
                examples['flask'] = '''
# app.py - 正確使用 HTTP 狀態碼
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        # 獲取用戶列表
        return jsonify(users), 200
    elif request.method == 'POST':
        # 創建新用戶
        if valid:
            return jsonify(new_user), 201
        else:
            return jsonify({"errors": errors}), 400

@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
def user(user_id):
    user = get_user(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    
    if request.method == 'GET':
        return jsonify(user), 200
    elif request.method == 'PUT':
        if valid:
            return jsonify(updated_user), 200
        else:
            return jsonify({"errors": errors}), 400
    elif request.method == 'DELETE':
        # 刪除用戶
        return '', 204
'''
            elif self.framework == 'fastapi':
                examples['fastapi'] = '''
# main.py - 正確使用 HTTP 狀態碼
from fastapi import FastAPI, APIRouter, HTTPException, status
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str

app = FastAPI()
router = APIRouter(prefix="/api")

@router.get("/users")
def read_users():
    # 獲取用戶列表 (默認 200 OK)
    return users

@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_user(user: User):
    # 創建新用戶 (明確設置 201 Created)
    try:
        return create_new_user(user)
    except ValidationError as e:
        # 處理驗證錯誤
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/users/{user_id}")
def read_user(user_id: int):
    # 獲取特定用戶
    user = get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    # 刪除用戶 (明確設置 204 No Content)
    user = get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    delete_user_from_db(user_id)
    return None

app.include_router(router)
'''
        
        elif feature == 'content_negotiation':
            if self.framework == 'django':
                examples['django'] = '''
# views.py - 內容協商
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer, XMLRenderer
from rest_framework.parsers import JSONParser, XMLParser

class UserViewSet(APIView):
    renderer_classes = [JSONRenderer, XMLRenderer]
    parser_classes = [JSONParser, XMLParser]
    
    def get(self, request, format=None):
        # format 參數將根據請求自動確定
        users = get_users()
        # Response 會根據請求的 Accept 頭選擇適當的渲染器
        return Response(users)

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.XMLRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.XMLParser',
    ],
}
'''
            elif self.framework == 'flask':
                examples['flask'] = '''
# app.py - 內容協商
from flask import Flask, request, jsonify, make_response
import json
import dicttoxml

app = Flask(__name__)

@app.route('/api/users', methods=['GET'])
def users():
    users_data = get_users()
    
    # 檢查 Accept 頭
    best = request.accept_mimetypes.best_match(['application/json', 'application/xml'])
    
    if best == 'application/xml':
        # 返回 XML
        xml = dicttoxml.dicttoxml(users_data)
        response = make_response(xml)
        response.headers['Content-Type'] = 'application/xml'
        return response
    else:
        # 默認返回 JSON
        return jsonify(users_data)

@app.route('/api/users', methods=['POST'])
def create_user():
    content_type = request.headers.get('Content-Type', '')
    
    if 'application/json' in content_type:
        # 解析 JSON
        data = request.get_json()
    elif 'application/xml' in content_type:
        # 解析 XML
        import xml.etree.ElementTree as ET
        data = parse_xml_to_dict(request.data)
    else:
        return jsonify({"error": "Unsupported Media Type"}), 415
    
    # 處理數據...
    return jsonify(new_user), 201
'''
            elif self.framework == 'fastapi':
                examples['fastapi'] = '''
# main.py - 內容協商
from fastapi import FastAPI, APIRouter, Response
from fastapi.responses import JSONResponse, XMLResponse
from pydantic import BaseModel
import dicttoxml

class User(BaseModel):
    name: str
    email: str

app = FastAPI()
router = APIRouter(prefix="/api")

@router.get("/users")
def read_users(response: Response, accept: str = None):
    users_data = get_users()
    
    # 檢查 Accept 頭或查詢參數
    if accept == "xml" or "application/xml" in response.headers.get("Accept", ""):
        xml = dicttoxml.dicttoxml(users_data)
        return Response(content=xml, media_type="application/xml")
    
    # 默認返回 JSON
    return users_data

# 使用內容類型路徑後綴
@router.get("/users.json")
def read_users_json():
    return get_users()

@router.get("/users.xml", response_class=XMLResponse)
def read_users_xml():
    users_data = get_users()
    xml = dicttoxml.dicttoxml(users_data)
    return Response(content=xml, media_type="application/xml")

app.include_router(router)
'''
        
        return examples
    
    def generate_restful_migration_plan(self, api_endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成將 API 遷移到 RESTful 設計的計劃
        
        Args:
            api_endpoints: 端點列表
            
        Returns:
            遷移計劃
        """
        # 分析當前 API 的 RESTful 合規性
        analysis_result = self.analyze_restful_design()
        
        # 初始化遷移計劃
        migration_plan = {
            'current_score': analysis_result['restful_score'],
            'target_score': min(100, analysis_result['restful_score'] + 30),  # 目標提高 30 分或達到滿分
            'phases': [],
            'example_changes': []
        }
        
        # 根據問題類型分組
        issues_by_type = {}
        for issue in analysis_result['restful_issues']:
            issue_type = issue.get('type', 'other')
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)
        
        # 生成遷移階段
        phases = []
        
        # 1. 資源命名和 URL 結構（最基本的變化）
        if 'endpoint_naming' in issues_by_type or 'resource_hierarchy' in issues_by_type:
            phases.append({
                'name': '改進資源命名和 URL 結構',
                'description': '重構 API 端點以遵循 RESTful 命名約定並優化資源層次結構',
                'priority': 'high',
                'tasks': [
                    '識別需要重命名的端點',
                    '設計新的 URL 結構',
                    '更新路由配置',
                    '實施重定向以支持舊路徑（可選）'
                ]
            })
            
            # 添加示例變更
            naming_issues = issues_by_type.get('endpoint_naming', [])
            if naming_issues:
                for issue in naming_issues[:3]:  # 最多 3 個示例
                    old_path = issue.get('endpoint', '')
                    if not old_path:
                        continue
                        
                    # 生成建議的新路徑
                    new_path = self._suggest_restful_path(old_path)
                    
                    migration_plan['example_changes'].append({
                        'type': 'endpoint_rename',
                        'old': old_path,
                        'new': new_path,
                        'reason': issue.get('description', '')
                    })
        
        # 2. HTTP 方法正確使用
        if 'http_method' in issues_by_type:
            phases.append({
                'name': '正確使用 HTTP 方法',
                'description': '更新控制器/處理器以使用適當的 HTTP 方法進行各種操作',
                'priority': 'high',
                'tasks': [
                    '識別使用不當方法的端點',
                    '重構控制器以使用正確的 HTTP 方法',
                    '更新請求處理邏輯',
                    '更新客戶端代碼以使用新的方法'
                ]
            })
            
            # 添加示例變更
            method_issues = issues_by_type.get('http_method', [])
            if method_issues:
                for issue in method_issues[:3]:  # 最多 3 個示例
                    endpoint = issue.get('endpoint', '')
                    if not endpoint:
                        continue
                    
                    # 從問題描述中提取方法信息
                    old_method = None
                    new_method = None
                    description = issue.get('description', '')
                    
                    if 'GET' in description and 'POST' not in description:
                        old_method = 'GET'
                        # 根據端點推斷合適的方法
                        if any(verb in endpoint.lower() for verb in ['create', 'add']):
                            new_method = 'POST'
                        elif any(verb in endpoint.lower() for verb in ['update', 'edit']):
                            new_method = 'PUT'
                        elif any(verb in endpoint.lower() for verb in ['delete', 'remove']):
                            new_method = 'DELETE'
                    elif 'POST' in description and 'update' in description:
                        old_method = 'POST'
                        new_method = 'PUT'
                    
                    if old_method and new_method:
                        migration_plan['example_changes'].append({
                            'type': 'http_method_change',
                            'endpoint': endpoint,
                            'old_method': old_method,
                            'new_method': new_method,
                            'reason': description
                        })
        
        # 3. 狀態碼正確使用
        if 'status_code' in issues_by_type:
            phases.append({
                'name': '改進狀態碼使用',
                'description': '更新回應以使用適當的 HTTP 狀態碼',
                'priority': 'medium',
                'tasks': [
                    '識別狀態碼使用不當的處理器',
                    '更新回應以包含正確的狀態碼',
                    '確保錯誤處理使用適當的狀態碼',
                    '記錄狀態碼的使用'
                ]
            })
        
        # 4. 內容協商
        if 'content_negotiation' in issues_by_type:
            phases.append({
                'name': '實施內容協商',
                'description': '更新 API 以支持內容協商並尊重 Accept 頭',
                'priority': 'low',
                'tasks': [
                    '識別需要支持多種內容類型的端點',
                    '實施內容類型協商',
                    '設置適當的 Content-Type 回應頭',
                    '測試不同的內容類型'
                ]
            })
        
        # 5. 最後階段 - 文檔和測試
        phases.append({
            'name': '更新文檔和測試',
            'description': '更新 API 文檔和測試以反映 RESTful 設計變更',
            'priority': 'medium',
            'tasks': [
                '更新 API 文檔',
                '更新和擴展測試套件',
                '更新客戶端示例和說明書',
                '驗證所有變更'
            ]
        })
        
        migration_plan['phases'] = phases
        
        # 添加框架特定的實施指南
        migration_plan['implementation_guide'] = self._get_framework_migration_guide()
        
        return migration_plan
    
    def _suggest_restful_path(self, old_path: str) -> str:
        """
        根據 RESTful 原則建議更好的路徑
        
        Args:
            old_path: 原路徑
            
        Returns:
            建議的新路徑
        """
        # 分析路徑組件
        parts = old_path.split('/')
        new_parts = []
        
        # 保留前綴（如 /api）
        api_prefix = ''
        if parts and parts[0] == '':
            new_parts.append('')
        if len(parts) > 1 and parts[1].lower() == 'api':
            api_prefix = 'api'
            new_parts.append('api')
            parts = parts[2:]
        else:
            parts = parts[1:] if parts and parts[0] == '' else parts
        
        # 處理其餘部分
        i = 0
        while i < len(parts):
            part = parts[i]
            if not part:
                i += 1
                continue
                
            # 處理版本前綴
            if part.startswith('v') and part[1:].isdigit():
                new_parts.append(part)
                i += 1
                continue
            
            # 處理動詞前綴
            verb_prefixes = ['get', 'create', 'update', 'delete', 'add', 'remove', 'list', 'fetch']
            found_verb = False
            
            for verb in verb_prefixes:
                if part.lower().startswith(verb) and len(part) > len(verb) and part[len(verb)].isupper():
                    # 提取資源名稱並轉換為複數
                    resource = part[len(verb):]
                    if verb in ['get', 'update', 'delete'] and i+1 < len(parts) and parts[i+1].isdigit():
                        # 如果後面跟著 ID，則保留單數形式表示單一資源
                        new_parts.append(self._to_kebab_case(resource.lower()))
                        new_parts.append(parts[i+1])  # 添加 ID
                        i += 2
                    else:
                        # 否則使用複數形式表示集合
                        resource_plural = self._pluralize(resource)
                        new_parts.append(self._to_kebab_case(resource_plural.lower()))
                        i += 1
                    found_verb = True
                    break
            
            if found_verb:
                continue
            
            # 處理普通資源名稱
            new_parts.append(self._to_kebab_case(part.lower()))
            i += 1
        
        # 組合新路徑
        new_path = '/'.join(new_parts)
        
        return new_path
    
    def _pluralize(self, word: str) -> str:
        """
        將單詞轉換為複數形式（簡單規則）
        
        Args:
            word: 單詞
            
        Returns:
            複數形式
        """
        # 特殊情況
        if word.endswith('y'):
            return word[:-1] + 'ies'
        elif word.endswith('s') or word.endswith('x') or word.endswith('z') or word.endswith('ch') or word.endswith('sh'):
            return word + 'es'
        else:
            return word + 's'
    
    def _to_kebab_case(self, text: str) -> str:
        """
        將文本轉換為 kebab-case
        
        Args:
            text: 文本
            
        Returns:
            kebab-case 文本
        """
        # 替換下劃線
        text = text.replace('_', '-')
        
        # 處理駝峰命名法
        result = ''
        for i, char in enumerate(text):
            if i > 0 and char.isupper() and text[i-1] != '-':
                result += '-' + char.lower()
            else:
                result += char.lower()
        
        return result
    
    def _get_framework_migration_guide(self) -> Dict[str, Any]:
        """
        獲取框架特定的遷移指南
        
        Returns:
            遷移指南
        """
        guide = {
            'general_tips': [
                '使用 URL 參數而非查詢字符串來表示資源 ID',
                '使用查詢字符串進行過濾、排序和分頁',
                '返回有意義的錯誤訊息和適當的狀態碼',
                '為新的 URL 結構實施臨時重定向以支持現有客戶端'
            ]
        }
        
        if self.framework == 'django':
            guide['django'] = {
                'routing': '''
# urls.py - RESTful 路由配置
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'products', views.ProductViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    # 臨時支持舊路徑
    path('api/getUser/<int:pk>/', views.legacy_get_user),
]

# views.py - 重定向
from django.shortcuts import redirect

def legacy_get_user(request, pk):
    # 臨時重定向到新 URL
    return redirect('api:user-detail', pk=pk)
''',
                'viewsets': '''
# views.py - 使用 ViewSet 實施 RESTful API
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    提供標準的 list, create, retrieve, update, destroy 操作
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
'''
            }
        elif self.framework == 'flask':
            guide['flask'] = {
                'routing': '''
# app.py - RESTful 路由
from flask import Flask, jsonify, request, redirect, url_for
from flask_restful import Api, Resource

app = Flask(__name__)
api = Api(app, prefix='/api')

# 資源類
class UserList(Resource):
    def get(self):
        # 獲取用戶列表
        return jsonify(users)
    
    def post(self):
        # 創建用戶
        return jsonify(user), 201

class UserDetail(Resource):
    def get(self, user_id):
        # 獲取單個用戶
        return jsonify(user)
    
    def put(self, user_id):
        # 更新用戶
        return jsonify(user)
    
    def delete(self, user_id):
        # 刪除用戶
        return '', 204

# 註冊資源
api.add_resource(UserList, '/users')
api.add_resource(UserDetail, '/users/<int:user_id>')

# 舊路徑支持
@app.route('/getUser/<int:user_id>')
def legacy_get_user(user_id):
    return redirect(url_for('userdetail', user_id=user_id))
''',
                'blueprints': '''
# api/__init__.py - 使用藍圖組織 API
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

from . import users, products

# api/users.py - 用戶資源
from flask import jsonify, request
from . import api_bp

@api_bp.route('/users', methods=['GET'])
def get_users():
    # 獲取用戶列表
    return jsonify(users)

@api_bp.route('/users', methods=['POST'])
def create_user():
    # 創建用戶
    return jsonify(user), 201

@api_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    # 獲取單個用戶
    return jsonify(user)

@api_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    # 更新用戶
    return jsonify(user)

@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    # 刪除用戶
    return '', 204
'''
            }
        elif self.framework == 'fastapi':
            guide['fastapi'] = {
                'routing': '''
# main.py - RESTful API 路由
from fastapi import FastAPI, APIRouter, HTTPException, status, Response
from pydantic import BaseModel
from typing import List

class User(BaseModel):
    id: int = None
    name: str
    email: str

app = FastAPI()
api_router = APIRouter(prefix="/api")

# 內存中的用戶存儲（示例用）
users_db = {}

@api_router.get("/users", response_model=List[User])
def read_users():
    return list(users_db.values())

@api_router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(user: User):
    user_id = max(users_db.keys() or [0]) + 1
    user.id = user_id
    users_db[user_id] = user
    return user

@api_router.get("/users/{user_id}", response_model=User)
def read_user(user_id: int):
    if user_id not in users_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return users_db[user_id]

@api_router.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, user: User):
    if user_id not in users_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.id = user_id
    users_db[user_id] = user
    return user

@api_router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int):
    if user_id not in users_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    del users_db[user_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 路由到舊路徑（重定向）
@app.get("/getUser/{user_id}")
def legacy_get_user(user_id: int):
    return Response(status_code=status.HTTP_307_TEMPORARY_REDIRECT, 
                  headers={"Location": f"/api/users/{user_id}"})

app.include_router(api_router)
''',
                'dependencies': '''
# dependencies.py - 使用依賴項進行授權等
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme)):
    # 驗證令牌並獲取用戶
    if invalid_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                          detail="Invalid authentication credentials")
    return user

# 在路由中使用依賴項
@api_router.get("/users/me")
def read_users_me(current_user = Depends(get_current_user)):
    return current_user
'''
            }
        
        return guide


def generate_restful_api_proposal(framework: str, base_url: str = '/api', 
                                  with_auth: bool = True, version: str = 'v1') -> Dict[str, Any]:
    """
    為從頭開始的 RESTful API 生成建議
    
    Args:
        framework: 要使用的框架 ('django', 'flask' 或 'fastapi')
        base_url: API 的基本 URL 前綴
        with_auth: 是否包括身份驗證
        version: API 版本
        
    Returns:
        API 建議
    """
    # 確保版本有前綴 'v'
    if version and not version.startswith('v'):
        version = 'v' + version
    
    # 構建基本 URL
    api_base = base_url
    if version:
        api_base = f"{base_url}/{version}"
    
    # 初始化建議
    proposal = {
        'framework': framework,
        'base_url': api_base,
        'with_auth': with_auth,
        'resources': [
            {
                'name': 'users',
                'endpoints': [
                    {'method': 'GET', 'path': '/users', 'description': '獲取所有用戶'},
                    {'method': 'POST', 'path': '/users', 'description': '創建新用戶'},
                    {'method': 'GET', 'path': '/users/{id}', 'description': '獲取特定用戶'},
                    {'method': 'PUT', 'path': '/users/{id}', 'description': '更新特定用戶'},
                    {'method': 'DELETE', 'path': '/users/{id}', 'description': '刪除特定用戶'}
                ],
                'model': {
                    'fields': [
                        {'name': 'id', 'type': 'integer', 'description': '用戶 ID'},
                        {'name': 'username', 'type': 'string', 'description': '用戶名'},
                        {'name': 'email', 'type': 'string', 'description': '電子郵件地址'},
                        {'name': 'created_at', 'type': 'datetime', 'description': '創建時間'}
                    ]
                }
            },
            {
                'name': 'products',
                'endpoints': [
                    {'method': 'GET', 'path': '/products', 'description': '獲取所有產品'},
                    {'method': 'POST', 'path': '/products', 'description': '創建新產品'},
                    {'method': 'GET', 'path': '/products/{id}', 'description': '獲取特定產品'},
                    {'method': 'PUT', 'path': '/products/{id}', 'description': '更新特定產品'},
                    {'method': 'DELETE', 'path': '/products/{id}', 'description': '刪除特定產品'}
                ],
                'model': {
                    'fields': [
                        {'name': 'id', 'type': 'integer', 'description': '產品 ID'},
                        {'name': 'name', 'type': 'string', 'description': '產品名稱'},
                        {'name': 'price', 'type': 'decimal', 'description': '產品價格'},
                        {'name': 'created_at', 'type': 'datetime', 'description': '創建時間'}
                    ]
                }
            }
        ],
        'best_practices': [
            '使用標準 HTTP 方法和狀態碼',
            '實施基於 JWT 的身份驗證',
            '支持內容協商 (JSON/XML)',
            '使用查詢參數進行篩選、分頁和排序',
            '實施速率限制以防止濫用',
            '提供詳細的 API 文檔'
        ]
    }
    
    # 如果包括身份驗證，添加相關端點
    if with_auth:
        auth_resource = {
            'name': 'auth',
            'endpoints': [
                {'method': 'POST', 'path': '/auth/token', 'description': '獲取訪問令牌'},
                {'method': 'POST', 'path': '/auth/refresh', 'description': '刷新訪問令牌'},
                {'method': 'POST', 'path': '/auth/register', 'description': '註冊新用戶'}
            ]
        }
        proposal['resources'].append(auth_resource)
    
    # 添加框架特定的建議
    proposal['framework_implementation'] = _get_framework_implementation_guide(framework, api_base, with_auth)
    
    return proposal


def _get_framework_implementation_guide(framework: str, api_base: str, with_auth: bool) -> Dict[str, Any]:
    """
    獲取框架特定的實施指南
    
    Args:
        framework: 框架名稱
        api_base: API 基礎 URL
        with_auth: 是否包括身份驗證
        
    Returns:
        實施指南
    """
    if framework == 'django':
        return {
            'project_setup': '''
# 創建項目
django-admin startproject myapi
cd myapi

# 創建 API 應用
python manage.py startapp api

# 安裝依賴
pip install djangorestframework djangorestframework-simplejwt
''',
            'settings': '''
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'api',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}
''' if with_auth else '''
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'api',
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}
''',
            'models': '''
# api/models.py
from django.db import models

class User(models.Model):
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.username

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
''',
            'serializers': '''
# api/serializers.py
from rest_framework import serializers
from .models import User, Product

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'created_at']

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'created_at']
''',
            'views': '''
# api/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User, Product
from .serializers import UserSerializer, ProductSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
''' if with_auth else '''
# api/views.py
from rest_framework import viewsets
from .models import User, Product
from .serializers import UserSerializer, ProductSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
''',
            'urls': f'''
# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'products', views.ProductViewSet)

urlpatterns = [
    path('{api_base.lstrip("/")}/', include(router.urls)),
]

# myapi/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls')),
]
'''
        }
    elif framework == 'flask':
        return {
            'project_setup': '''
# 創建項目結構
mkdir flask_api
cd flask_api

# 創建虛擬環境
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# 安裝依賴
pip install flask flask-restful flask-sqlalchemy flask-jwt-extended
''',
            'app_structure': '''
/flask_api
  /app
    __init__.py
    models.py
    resources.py
  config.py
  run.py
''',
            'config': '''
# config.py
import os

class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
''' if with_auth else '''
# config.py
class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
''',
            'models': '''
# app/models.py
from app import db
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Product {self.name}>'
''',
            'resources': f'''
# app/resources.py
from flask_restful import Resource, reqparse, fields, marshal_with
from app.models import User, Product
from app import db

# 定義序列化字段
user_fields = {{
    'id': fields.Integer,
    'username': fields.String,
    'email': fields.String,
    'created_at': fields.DateTime
}}

product_fields = {{
    'id': fields.Integer,
    'name': fields.String,
    'price': fields.Float,
    'created_at': fields.DateTime
}}

# 用戶資源
class UserListResource(Resource):
    @marshal_with(user_fields)
    def get(self):
        users = User.query.all()
        return users
    
    @marshal_with(user_fields)
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', required=True)
        parser.add_argument('email', required=True)
        args = parser.parse_args()
        
        user = User(username=args['username'], email=args['email'])
        db.session.add(user)
        db.session.commit()
        return user, 201

class UserResource(Resource):
    @marshal_with(user_fields)
    def get(self, user_id):
        user = User.query.get_or_404(user_id)
        return user
    
    @marshal_with(user_fields)
    def put(self, user_id):
        parser = reqparse.RequestParser()
        parser.add_argument('username')
        parser.add_argument('email')
        args = parser.parse_args()
        
        user = User.query.get_or_404(user_id)
        if args['username']:
            user.username = args['username']
        if args['email']:
            user.email = args['email']
        
        db.session.commit()
        return user
    
    def delete(self, user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return '', 204

# 產品資源
class ProductListResource(Resource):
    @marshal_with(product_fields)
    def get(self):
        products = Product.query.all()
        return products
    
    @marshal_with(product_fields)
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True)
        parser.add_argument('price', type=float, required=True)
        args = parser.parse_args()
        
        product = Product(name=args['name'], price=args['price'])
        db.session.add(product)
        db.session.commit()
        return product, 201

class ProductResource(Resource):
    @marshal_with(product_fields)
    def get(self, product_id):
        product = Product.query.get_or_404(product_id)
        return product
    
    @marshal_with(product_fields)
    def put(self, product_id):
        parser = reqparse.RequestParser()
        parser.add_argument('name')
        parser.add_argument('price', type=float)
        args = parser.parse_args()
        
        product = Product.query.get_or_404(product_id)
        if args['name']:
            product.name = args['name']
        if args['price']:
            product.price = args['price']
        
        db.session.commit()
        return product
    
    def delete(self, product_id):
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        return '', 204
''',
            'init': f'''
# app/__init__.py
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config import Config

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    jwt.init_app(app)
    
    from app.resources import UserListResource, UserResource, ProductListResource, ProductResource
    
    api = Api(app)
    api.add_resource(UserListResource, '{api_base}/users')
    api.add_resource(UserResource, '{api_base}/users/<int:user_id>')
    api.add_resource(ProductListResource, '{api_base}/products')
    api.add_resource(ProductResource, '{api_base}/products/<int:product_id>')
    
    return app
''' if with_auth else f'''
# app/__init__.py
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    
    from app.resources import UserListResource, UserResource, ProductListResource, ProductResource
    
    api = Api(app)
    api.add_resource(UserListResource, '{api_base}/users')
    api.add_resource(UserResource, '{api_base}/users/<int:user_id>')
    api.add_resource(ProductListResource, '{api_base}/products')
    api.add_resource(ProductResource, '{api_base}/products/<int:product_id>')
    
    return app
''',
            'run': '''
# run.py
from app import create_app, db

app = create_app()

@app.before_first_request
def create_tables():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
'''
        }
    elif framework == 'fastapi':
        return {
            'project_setup': '''
# 創建項目結構
mkdir fastapi_api
cd fastapi_api

# 創建虛擬環境
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# 安裝依賴
pip install fastapi uvicorn sqlalchemy pydantic python-jose passlib
''',
            'app_structure': '''
/fastapi_api
  /app
    __init__.py
    /api
      __init__.py
      /endpoints
        __init__.py
        users.py
        products.py
    /core
      __init__.py
      config.py
      security.py
    /db
      __init__.py
      models.py
      session.py
    /schemas
      __init__.py
      user.py
      product.py
  main.py
''',
            'config': '''
# app/core/config.py
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./app.db"
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

settings = Settings()
''' if with_auth else '''
# app/core/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./app.db"

settings = Settings()
''',
            'models': '''
# app/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
''',
            'schemas': '''
# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None

class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class User(UserInDBBase):
    pass

# app/schemas/product.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProductBase(BaseModel):
    name: str
    price: float

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

class ProductInDBBase(ProductBase):
    id: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class Product(ProductInDBBase):
    pass
''',
            'endpoints': f'''
# app/api/endpoints/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import User
from app.schemas.user import User as UserSchema, UserCreate, UserUpdate

router = APIRouter()

@router.get("/", response_model=List[UserSchema])
def read_users(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/{{user_id}}", response_model=UserSchema) 
def read_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.put("/{{user_id}}", response_model=UserSchema)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    update_data = user.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{{user_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    db.delete(user)
    db.commit()
    return None

# app/api/endpoints/products.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Product
from app.schemas.product import Product as ProductSchema, ProductCreate, ProductUpdate

router = APIRouter()

@router.get("/", response_model=List[ProductSchema])
def read_products(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    products = db.query(Product).offset(skip).limit(limit).all()
    return products

@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = Product(name=product.name, price=product.price)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/{{product_id}}", response_model=ProductSchema)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product

@router.put("/{{product_id}}", response_model=ProductSchema)
def update_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    update_data = product.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value)
    
    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/{{product_id}}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    db.delete(product)
    db.commit()
    return None

# app/api/__init__.py
from fastapi import APIRouter
from app.api.endpoints import users, products

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(products.router, prefix="/products", tags=["products"])

# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.db.session import engine
from app.db.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="RESTful API")

# 設置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)'''
        }
    else:
        return {'error': f'不支持的框架: {framework}'}