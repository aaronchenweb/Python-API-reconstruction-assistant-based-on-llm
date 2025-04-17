"""
用於分析和優化 Python 代碼性能的模塊。
"""
import sys
import ast
import os
import tempfile
import subprocess
import re
import textwrap
import time
from typing import Dict, List, Optional, Tuple, Any
import cProfile
import pstats
import io
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from utils.file_operations import read_file, write_file


class PerformanceIssue:
    """表示代碼中檢測到的性能問題。"""
    
    def __init__(self, 
                 issue_type: str, 
                 description: str, 
                 severity: str,
                 line_number: Optional[int] = None,
                 suggestion: Optional[str] = None,
                 code_example: Optional[str] = None):
        self.issue_type = issue_type
        self.description = description
        self.severity = severity  # 'low', 'medium', 'high'
        self.line_number = line_number
        self.suggestion = suggestion
        self.code_example = code_example
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典表示形式。"""
        return {
            'issue_type': self.issue_type,
            'description': self.description,
            'severity': self.severity,
            'line_number': self.line_number,
            'suggestion': self.suggestion,
            'code_example': self.code_example
        }


class PerformanceAnalyzer:
    """用於分析 Python 代碼性能的類。"""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.logger = logging.getLogger(__name__)
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        分析 Python 文件的性能問題。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含分析結果的字典
        """
        issues = []
        metrics = {}
        
        # 讀取文件
        file_content = read_file(file_path)
        
        # 靜態分析常見性能問題
        static_issues = self._static_analysis(file_content, file_path)
        issues.extend(static_issues)
        
        # 如果是可執行腳本，嘗試進行分析
        if self._is_executable(file_path):
            profile_metrics = self._profile_execution(file_path)
            if profile_metrics:
                metrics.update(profile_metrics)
        
        # 內存使用分析（如果可能）
        memory_usage = self._estimate_memory_usage(file_path)
        if memory_usage:
            metrics['estimated_memory_usage'] = memory_usage
        
        # 算法複雜度分析
        complexity_issues = self._analyze_algorithm_complexity(file_content)
        issues.extend(complexity_issues)
        
        # I/O 和網絡操作分析
        io_issues = self._analyze_io_operations(file_content)
        issues.extend(io_issues)
        
        return {
            'issues': [issue.to_dict() for issue in issues],
            'metrics': metrics
        }
    
    def _static_analysis(self, content: str, file_path: str) -> List[PerformanceIssue]:
        """
        執行靜態分析以識別常見性能問題。
        
        Args:
            content: Python 代碼內容
            file_path: 文件路徑（用於上下文）
            
        Returns:
            檢測到的性能問題列表
        """
        issues = []
        
        try:
            tree = ast.parse(content)
            
            # 檢查循環中的昂貴操作
            issues.extend(self._check_expensive_loops(tree))
            
            # 檢查低效的列表操作
            issues.extend(self._check_inefficient_list_operations(tree))
            
            # 檢查全局變量
            issues.extend(self._check_global_variables(tree))
            
            # 檢查數據結構的正確使用
            issues.extend(self._check_data_structures(tree))
            
            # 檢查循環中不必要的函數調用
            issues.extend(self._check_function_calls_in_loops(tree))
            
        except SyntaxError as e:
            issues.append(PerformanceIssue(
                'syntax_error',
                f"語法錯誤: {str(e)}",
                'high',
                e.lineno,
                "修復語法錯誤以啟用性能分析。"
            ))
        
        return issues
    
    def _check_expensive_loops(self, tree: ast.AST) -> List[PerformanceIssue]:
        """檢查循環內部的昂貴操作。"""
        issues = []
        
        for node in ast.walk(tree):
            # 檢查循環內的列表、集合或字典推導式
            if isinstance(node, (ast.For, ast.While)):
                for inner_node in ast.walk(node):
                    if isinstance(inner_node, (ast.ListComp, ast.SetComp, ast.DictComp)) and inner_node != node:
                        issues.append(PerformanceIssue(
                            'expensive_operation_in_loop',
                            "循環內的推導式可能會導致性能問題",
                            'medium',
                            inner_node.lineno,
                            "如果可能，考慮將推導式移到循環外",
                            "# 而不是：\nfor i in range(10):\n    result = [x*2 for x in large_list]\n\n# 使用：\nresult = [x*2 for x in large_list]\nfor i in range(10):\n    # 使用 result"
                        ))
            
            # 檢查具有大迭代潛力的嵌套循環
            if isinstance(node, ast.For):
                for inner_node in ast.walk(node):
                    if isinstance(inner_node, ast.For) and inner_node != node:
                        # 檢查是否在外部循環的主體內
                        if hasattr(inner_node, 'parent') and inner_node.parent == node:
                            issues.append(PerformanceIssue(
                                'nested_loops',
                                "檢測到嵌套循環，可能導致 O(n²) 或更差的複雜度",
                                'medium',
                                inner_node.lineno,
                                "考慮嵌套循環是否必要或可以優化"
                            ))
        
        return issues
    
    def _check_inefficient_list_operations(self, tree: ast.AST) -> List[PerformanceIssue]:
        """檢查低效的列表操作。"""
        issues = []
        
        for node in ast.walk(tree):
            # 檢查重複連接: something += item（在循環中）
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                if (isinstance(node.target, ast.Name) and 
                    isinstance(node.value, ast.Name)):
                    # 這是列表上潛在的 += 操作
                    # 檢查是否在循環中
                    parent_node = self._find_parent_loop(tree, node)
                    if parent_node:
                        issues.append(PerformanceIssue(
                            'inefficient_list_appending',
                            "在循環中使用 += 將項目添加到列表是低效的",
                            'medium',
                            node.lineno,
                            "對單個項目使用 list.append() 或對多個項目使用 extend()",
                            "# 而不是：\nresult = []\nfor item in items:\n    result += [item]\n\n# 使用：\nresult = []\nfor item in items:\n    result.append(item)"
                        ))
            
            # 檢查循環中的列表轉換
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'list':
                parent_node = self._find_parent_loop(tree, node)
                if parent_node:
                    issues.append(PerformanceIssue(
                        'list_conversion_in_loop',
                        "在循環內部轉換為列表可能效率低下",
                        'low',
                        node.lineno,
                        "如果可能，考慮將列表轉換移到循環外"
                    ))
        
        return issues
    
    def _check_global_variables(self, tree: ast.AST) -> List[PerformanceIssue]:
        """檢查過度使用全局變量。"""
        issues = []
        global_vars = set()
        
        # 查找所有全局語句
        for node in ast.walk(tree):
            if isinstance(node, ast.Global):
                for name in node.names:
                    global_vars.add(name)
        
        if len(global_vars) > 5:  # 任意閾值
            issues.append(PerformanceIssue(
                'excessive_globals',
                f"檢測到過度使用全局變量（{len(global_vars)} 個變量）",
                'medium',
                None,
                "考慮使用類或函數參數而不是全局變量"
            ))
        
        return issues
    
    def _check_data_structures(self, tree: ast.AST) -> List[PerformanceIssue]:
        """檢查數據結構的潛在低效使用。"""
        issues = []
        
        for node in ast.walk(tree):
            # 檢查循環中對列表的 'in' 操作（應使用集合或字典）
            if isinstance(node, ast.Compare):
                if any(isinstance(op, ast.In) for op in node.ops):
                    collection = node.comparators[0]
                    if isinstance(collection, ast.Name):
                        # 這是對變量的 'in' 操作
                        # 檢查是否在循環中
                        parent_node = self._find_parent_loop(tree, node)
                        if parent_node:
                            issues.append(PerformanceIssue(
                                'inefficient_lookup',
                                "在循環中對列表使用 'in' 運算符具有 O(n) 複雜度",
                                'medium',
                                node.lineno,
                                "考慮使用集合或字典進行 O(1) 查找",
                                "# 而不是：\nmy_list = [1, 2, 3, 4, 5]\nfor x in range(1000):\n    if x in my_list:  # O(n) 操作\n        print(x)\n\n# 使用：\nmy_set = set([1, 2, 3, 4, 5])  # 一次性轉換為集合\nfor x in range(1000):\n    if x in my_set:  # O(1) 操作\n        print(x)"
                            ))
        
        return issues
    
    def _check_function_calls_in_loops(self, tree: ast.AST) -> List[PerformanceIssue]:
        """檢查可以移到循環外的重複函數調用。"""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                function_calls = {}
                
                # 在循環體中查找函數調用
                for inner_node in ast.walk(node.body[0] if isinstance(node.body, list) else node.body):
                    if isinstance(inner_node, ast.Call) and isinstance(inner_node.func, ast.Name):
                        func_name = inner_node.func.id
                        
                        # 檢查此函數調用是否有依賴循環變量的參數
                        has_loop_dep = False
                        loop_var = None
                        
                        if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                            loop_var = node.target.id
                            
                            for arg in inner_node.args:
                                if isinstance(arg, ast.Name) and arg.id == loop_var:
                                    has_loop_dep = True
                                    break
                        
                        if not has_loop_dep and not self._is_builtin_function(func_name):
                            if func_name not in function_calls:
                                function_calls[func_name] = []
                            function_calls[func_name].append(inner_node.lineno)
                
                # 報告沒有循環變量依賴的重複函數調用問題
                for func_name, lines in function_calls.items():
                    if len(lines) > 1:
                        issues.append(PerformanceIssue(
                            'repeated_function_call',
                            f"函數 '{func_name}' 在循環中被多次調用，但不依賴循環變量",
                            'medium',
                            lines[0],
                            "考慮將函數調用移到循環外",
                            f"# 而不是：\nfor i in range(10):\n    result = {func_name}()  # 調用 10 次\n    # 使用結果\n\n# 使用：\nresult = {func_name}()  # 調用一次\nfor i in range(10):\n    # 使用結果"
                        ))
        
        return issues
    
    def _is_builtin_function(self, func_name: str) -> bool:
        """檢查函數名是否對應於內置函數。"""
        builtins = dir(__builtins__)
        return func_name in builtins
    
    def _find_parent_loop(self, tree: ast.AST, node: ast.AST) -> Optional[ast.AST]:
        """查找節點的父循環（如果存在）。"""
        # 簡化實現 - 這理想情況下需要完整的 AST 遍歷和父節點跟踪
        # 現在，只檢查節點是否在模塊級別的循環中
        for potential_parent in ast.walk(tree):
            if isinstance(potential_parent, (ast.For, ast.While)):
                # 檢查節點是否在循環的主體中
                for body_node in ast.walk(potential_parent.body[0] if isinstance(potential_parent.body, list) else potential_parent.body):
                    if body_node == node:
                        return potential_parent
        return None
    
    def _analyze_algorithm_complexity(self, content: str) -> List[PerformanceIssue]:
        """分析代碼中的算法複雜度。"""
        issues = []
        
        # 尋找潛在的二次算法
        if re.search(r'for\s+\w+\s+in\s+.+:\s*\n\s+for\s+\w+\s+in\s+.+:', content):
            issues.append(PerformanceIssue(
                'quadratic_complexity',
                "代碼包含嵌套循環，可能表示 O(n²) 時間複雜度",
                'medium',
                None,
                "考慮使用更高效的算法或數據結構"
            ))
        
        # 檢查潛在的低效排序
        if re.search(r'def\s+\w+sort\s*\(', content) or re.search(r'for\s+\w+\s+in\s+.+:\s*\n\s+for\s+\w+\s+in\s+.+:\s*\n\s+if\s+.+<.+:', content):
            issues.append(PerformanceIssue(
                'custom_sort',
                "檢測到自定義排序實現",
                'medium',
                None,
                "考慮使用內置排序函數（sorted()、list.sort()），它們用 C 實現"
            ))
        
        return issues
    
    def _analyze_io_operations(self, content: str) -> List[PerformanceIssue]:
        """分析 I/O 和網絡操作的性能問題。"""
        issues = []
        
        # 檢查循環中的文件操作
        if re.search(r'for\s+.+:\s*\n\s+(open|read|write|close)\(', content):
            issues.append(PerformanceIssue(
                'io_in_loop',
                "循環內的文件操作可能導致性能問題",
                'high',
                None,
                "考慮將文件操作移到循環外或使用緩衝操作"
            ))
        
        # 檢查循環中的網絡操作
        if re.search(r'for\s+.+:\s*\n\s+(requests\.get|requests\.post|urllib|http)', content):
            issues.append(PerformanceIssue(
                'network_in_loop',
                "循環內的網絡操作可能導致性能問題",
                'high',
                None,
                "考慮使用批處理請求或異步操作"
            ))
        
        return issues
    
    def _is_executable(self, file_path: str) -> bool:
        """檢查文件是否可直接執行。"""
        # 檢查文件是否有主塊或是腳本
        content = read_file(file_path)
        return "if __name__ == '__main__':" in content or "if __name__ == \"__main__\":" in content
    
    def _profile_execution(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        分析 Python 文件的執行。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含分析指標的字典，如果分析失敗則返回 None
        """
        metrics = {}
        
        try:
            # 創建分析器
            profiler = cProfile.Profile()
            
            # 創建模塊級命名空間
            namespace = {'__file__': file_path}
            
            # 讀取內容
            content = read_file(file_path)
            
            # 檢查這是否是 Flask 應用程序
            is_flask_app = 'from flask import' in content or 'import flask' in content
            
            # 開始分析
            profiler.enable()
            
            if is_flask_app:
                # 對於 Flask 應用，只分析導入和基本結構
                # 不執行應用本身
                try:
                    # 解析文件以分析結構，而不執行
                    tree = ast.parse(content)
                    # 查找重要函數進行報告
                    flask_functions = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            flask_functions.append(node.name)
                    
                    metrics['flask_app'] = True
                    metrics['detected_functions'] = flask_functions
                    metrics['execution_time'] = "未執行 - Flask 應用程序"
                    
                    # 添加有關 Flask 應用程序的消息
                    metrics['flask_note'] = "Flask 應用程序在此環境中無法完全分析。考慮使用 Flask 的內置分析中間件進行生產分析。"
                except Exception as e:
                    self.logger.error(f"分析 Flask 應用時出錯: {str(e)}")
            else:
                # 使用超時執行非 Flask 文件以防止掛起
                exec_thread = threading.Thread(target=exec, args=(content, namespace))
                exec_thread.daemon = True
                
                start_time = time.time()
                exec_thread.start()
                exec_thread.join(timeout=10)  # 10 秒超時
                
                execution_time = time.time() - start_time
                
                if exec_thread.is_alive():
                    # 執行時間過長
                    metrics['execution_timeout'] = True
                    metrics['execution_time'] = ">10s"
                else:
                    # 執行完成
                    metrics['execution_timeout'] = False
                    metrics['execution_time'] = f"{execution_time:.4f}s"
            
            # 停止分析
            profiler.disable()
            
            # 獲取統計數據
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # 前 20 個函數
            
            metrics['profile_output'] = stats_stream.getvalue()
            
            # 提取函數統計數據
            function_stats = []
            for line in stats_stream.getvalue().split('\n'):
                if re.match(r'\s+\d+\s+\d+', line):
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        function_stats.append({
                            'ncalls': parts[0],
                            'tottime': parts[1],
                            'percall': parts[2],
                            'cumtime': parts[3],
                            'percall_cum': parts[4],
                            'function': ' '.join(parts[5:])
                        })
            
            metrics['function_stats'] = function_stats
            
            return metrics
        except Exception as e:
            self.logger.error(f"分析 {file_path} 時出錯: {str(e)}")
            return None
    
    def _estimate_memory_usage(self, file_path: str) -> Optional[str]:
        """
        估計運行 Python 文件的內存使用情況。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            估計內存使用情況的字符串，如果估計失敗則返回 None
        """
        try:
            # 創建臨時文件添加 memory_profiler 檢測
            with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
                temp_path = temp_file.name
                
                # 讀取原始內容
                content = read_file(file_path)
                
                # 添加內存分析器
                instrumented_content = f"""
import memory_profiler
import sys

@memory_profiler.profile
def main():
{textwrap.indent(content, '    ')}

if __name__ == '__main__':
    main()
                """
                
                temp_file.write(instrumented_content.encode('utf-8'))
            
            # 使用 memory_profiler 運行
            try:
                result = subprocess.run([sys.executable, temp_path], 
                       capture_output=True, 
                       text=True,
                       timeout=10)
                
                # 從輸出中提取內存使用情況
                memory_usage = None
                for line in result.stderr.split('\n'):
                    if 'MiB' in line:
                        memory_match = re.search(r'(\d+\.\d+) MiB', line)
                        if memory_match:
                            memory_usage = memory_match.group(1) + ' MiB'
                            break
                
                return memory_usage
            except subprocess.TimeoutExpired:
                return "執行超時"
            finally:
                # 清理
                os.unlink(temp_path)
        except Exception as e:
            self.logger.error(f"估計 {file_path} 的內存使用情況時出錯: {str(e)}")
            return None
    
    def suggest_improvements(self, file_path: str, analysis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根據性能分析生成改進建議。
        
        Args:
            file_path: Python 文件的路徑
            analysis_result: analyze_file 的結果
            
        Returns:
            改進建議列表
        """
        suggestions = []
        
        # 處理問題
        for issue in analysis_result.get('issues', []):
            suggestion = {
                'type': 'performance',
                'description': issue['description'],
                'severity': issue['severity'],
                'line_number': issue['line_number'],
                'recommendation': issue['suggestion'] if issue['suggestion'] else "考慮重構此代碼以獲得更好的性能。",
                'code_example': issue['code_example']
            }
            suggestions.append(suggestion)
        
        # 根據指標添加一般建議
        metrics = analysis_result.get('metrics', {})
        
        # 檢查執行時間
        if 'execution_time' in metrics:
            execution_time = metrics['execution_time']
            if isinstance(execution_time, str) and execution_time.startswith('>'):
                suggestions.append({
                    'type': 'performance',
                    'description': f"執行時間 ({execution_time}) 超過閾值",
                    'severity': 'high',
                    'line_number': None,
                    'recommendation': "考慮優化算法或為長時間運行的任務使用多進程"
                })
            elif isinstance(execution_time, str) and execution_time.endswith('s'):
                try:
                    time_seconds = float(execution_time[:-1])
                    if time_seconds > 1.0:
                        suggestions.append({
                            'type': 'performance',
                            'description': f"執行時間 ({execution_time}) 相對較高",
                            'severity': 'medium',
                            'line_number': None,
                            'recommendation': "考慮優化代碼的關鍵部分"
                        })
                except ValueError:
                    pass
        
        # 檢查內存使用情況
        if 'estimated_memory_usage' in metrics:
            memory_usage = metrics['estimated_memory_usage']
            if isinstance(memory_usage, str) and 'MiB' in memory_usage:
                try:
                    memory_mb = float(memory_usage.split()[0])
                    if memory_mb > 100:
                        suggestions.append({
                            'type': 'performance',
                            'description': f"檢測到高內存使用 ({memory_usage})",
                            'severity': 'medium',
                            'line_number': None,
                            'recommendation': "考慮通過使用生成器、更有效地管理大型數據結構或分塊處理數據來優化內存使用"
                        })
                except ValueError:
                    pass
        
        # 檢查函數統計數據
        if 'function_stats' in metrics:
            for stat in metrics['function_stats'][:3]:  # 前 3 個函數
                if float(stat.get('cumtime', 0)) > 0.1:
                    suggestions.append({
                        'type': 'performance',
                        'description': f"函數 '{stat.get('function', 'unknown')}' 需要大量時間 ({stat.get('cumtime')}s)",
                        'severity': 'medium',
                        'line_number': None,
                        'recommendation': "優化此函數，因為它是性能熱點"
                    })
        
        return suggestions


class PerformanceOptimizer:
    """用於優化 Python 代碼性能的類。"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
    
    def optimize_code(self, file_path: str, issues: List[Dict[str, Any]]) -> Optional[str]:
        """
        根據性能問題生成優化代碼。
        
        Args:
            file_path: Python 文件的路徑
            issues: 性能問題列表
            
        Returns:
            優化後的代碼字符串，如果優化失敗則返回 None
        """
        # 讀取原始內容
        content = read_file(file_path)
        
        # 如果 LLM 客戶端可用，使用它進行智能優化
        if self.llm_client:
            return self._optimize_with_llm(content, issues)
        
        # 否則，使用基於規則的優化
        return self._optimize_with_rules(content, issues)
    
    def _optimize_with_llm(self, content: str, issues: List[Dict[str, Any]]) -> Optional[str]:
        """使用 LLM 優化代碼。"""
        if not self.llm_client:
            return None
        
        # 為提示格式化問題
        issues_text = ""
        for i, issue in enumerate(issues, 1):
            issues_text += f"問題 {i}:\n"
            issues_text += f"- 類型: {issue.get('type', 'unknown')}\n"
            issues_text += f"- 描述: {issue.get('description', 'unknown')}\n"
            issues_text += f"- 行號: {issue.get('line_number', 'unknown')}\n"
            issues_text += f"- 建議: {issue.get('recommendation', 'unknown')}\n\n"
        
        # 創建提示
        prompt = f"""
作為性能優化專家，請根據已識別的問題優化以下 Python 代碼。
確保優化後的代碼在功能上與原始代碼等效。

原始代碼:
```python
{content}
```

需要解決的性能問題:
{issues_text}

請提供優化後的代碼，並在註釋中說明您的更改。
"""
        
        # 從 LLM 獲取優化
        response = self.llm_client.get_completion(prompt)
        
        # 從回應中提取代碼
        code_match = re.search(r'```python\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        
        return response
    
    def _optimize_with_rules(self, content: str, issues: List[Dict[str, Any]]) -> str:
        """使用基於規則的轉換優化代碼。"""
        optimized = content
        
        # 跟踪所做的更改
        changes = []
        
        # 根據問題類型應用優化
        for issue in issues:
            issue_type = issue.get('type')
            line_number = issue.get('line_number')
            
            if issue_type == 'inefficient_list_appending':
                # 修復低效的列表附加
                pattern = r'(\w+)\s*\+=\s*\[(.*?)\]'
                replacement = r'\1.append(\2)'
                new_content = re.sub(pattern, replacement, optimized)
                if new_content != optimized:
                    optimized = new_content
                    changes.append(f"# 優化第 {line_number} 行: 將 += [item] 更改為 .append(item)")
            
            elif issue_type == 'inefficient_lookup':
                # 查找可能需要轉換為集合的列表
                list_usages = re.finditer(r'(\w+)\s*=\s*\[(.*?)\]', optimized)
                for match in list_usages:
                    list_name = match.group(1)
                    # 檢查此列表是否與 'in' 運算符一起使用
                    if re.search(rf'if\s+.*?\s+in\s+{list_name}', optimized):
                        # 將列表轉換為集合
                        set_decl = f"{list_name} = set([{match.group(2)}])  # 優化: 將列表轉換為集合以獲得 O(1) 查找速度"
                        optimized = optimized.replace(match.group(0), set_decl)
                        changes.append(f"# 優化: 將列表 '{list_name}' 轉換為集合以進行更快的查找")
            
            elif issue_type == 'repeated_function_call':
                # 這更難用正則表達式修復，需要完整的 AST 解析
                # 添加注釋提醒用戶
                optimized = optimized.replace(
                    f"\n",
                    f"\n# TODO: 考慮優化第 {line_number} 行的重複函數調用\n",
                    1
                )
            
            elif issue_type == 'io_in_loop' or issue_type == 'network_in_loop':
                # 添加警告注釋
                optimized = optimized.replace(
                    "for ",
                    f"# 警告: 性能問題 - 循環中的 I/O 或網絡操作\nfor ",
                    1
                )
        
        # 在頂部添加優化注釋
        if changes:
            header = "# 優化版本 - 性能改進:\n"
            for change in changes:
                header += f"{change}\n"
            optimized = header + "\n" + optimized
        
        return optimized