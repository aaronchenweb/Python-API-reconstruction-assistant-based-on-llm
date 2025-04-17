"""
用於生成和應用代碼重構建議的引擎。
"""
import ast
import os
import re
from typing import Dict, List, Optional, Tuple, Union

from rope.base import project, libutils
from rope.refactor.rename import Rename
from rope.refactor.extract import ExtractMethod
from rope.refactor.move import MoveModule

from code_analyzer import ast_parser, code_metrics
from design_patterns.pattern_detector import PatternDetector
from design_patterns.patterns_registry import PatternsRegistry
from llm_integration.llm_client import LLMClient
from llm_integration.prompt_templates import get_template
from utils.file_operations import read_file, write_file


class RefactoringEngine:
    """用於生成和應用代碼重構建議的引擎。"""
    
    def __init__(self, llm_client: LLMClient, project_path: str):
        self.llm_client = llm_client
        self.project_path = project_path
        self.pattern_detector = PatternDetector()
        self.patterns_registry = PatternsRegistry()
        self.rope_project = project.Project(project_path)
    
    def analyze_code_quality(self, file_path: str) -> Dict:
        """
        分析文件的代碼質量指標。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含代碼質量指標的字典
        """
        # 讀取文件內容
        file_content = read_file(file_path)
        
        # 計算代碼指標
        metrics = code_metrics.get_code_metrics(file_content)
        
        # 根據指標閾值確定問題
        issues = []
        
        if metrics.get('total_complexity', 0) > 10:
            issues.append({
                'type': 'high_complexity',
                'description': '高循環複雜度表明代碼可能難以維護。',
                'suggestion': '考慮將複雜函數分解為更小、更易於管理的部分。'
            })
            
        if 'avg_function_complexity' in metrics and metrics['avg_function_complexity'] > 5:
            issues.append({
                'type': 'high_average_complexity',
                'description': '高平均函數複雜度表明代碼可能難以維護。',
                'suggestion': '改進代碼結構，降低複雜度，並添加適當的文檔。'
            })
            
        # 檢查複雜函數
        if 'function_complexities' in metrics:
            for func in metrics['function_complexities']:
                if func['complexity'] > 7:
                    issues.append({
                        'type': 'complex_function',
                        'description': f"函數 '{func['name']}' 具有高複雜度 ({func['complexity']})。",
                        'suggestion': f"將 {func['line']} 行的函數 '{func['name']}' 重構為更小的函數。"
                    })
            
        return {
            'metrics': metrics,
            'issues': issues
        }
    
    def detect_design_patterns(self, file_path: str) -> Dict:
        """
        檢測文件中的設計模式。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含檢測到的模式和建議的字典
        """
        patterns = self.pattern_detector.detect_patterns(file_path)
        
        result = {
            'detected_patterns': patterns,
            'suggestions': []
        }
        
        # 根據檢測到的模式生成建議
        for pattern_name, occurrences in patterns.items():
            pattern_info = self.patterns_registry.get_pattern(pattern_name)
            if pattern_info:
                for class_name, line_number in occurrences:
                    result['suggestions'].append({
                        'pattern': pattern_name,
                        'class': class_name,
                        'line': line_number,
                        'description': pattern_info.description,
                        'refactoring_tips': pattern_info.refactoring_tips
                    })
        
        return result
    
    def suggest_refactorings(self, file_path: str) -> Dict:
        """
        使用代碼分析和 LLM 為文件生成重構建議。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含重構建議的字典
        """
        # 讀取文件內容
        file_content = read_file(file_path)
        
        # 分析代碼質量
        quality_analysis = self.analyze_code_quality(file_path)
        
        # 檢測設計模式
        patterns_analysis = self.detect_design_patterns(file_path)
        
        # 為 LLM 準備提示
        prompt_template = get_template('refactoring_suggestions')
        
        # 如果未找到模板，則使用默認模板
        if prompt_template:
            prompt = prompt_template.format(
                code=file_content,
                quality_metrics=quality_analysis['metrics'],
                quality_issues=quality_analysis['issues'],
                detected_patterns=patterns_analysis['detected_patterns']
            )
        else:
            # 默認模板
            prompt = f"""
Analyze the following Python code and provide refactoring suggestions based on the quality metrics and detected patterns.

Code:
```python
{file_content}
```

Quality Metrics:
{quality_analysis['metrics']}

Quality Issues:
{quality_analysis['issues']}

Detected Design Patterns:
{patterns_analysis['detected_patterns']}

Please suggest specific refactorings to improve the code quality. For each suggestion, include:
1. The type of refactoring (e.g., Extract Method, Rename Variable, etc.)
2. The location in the code where it should be applied
3. A detailed description of the proposed change
4. Code example of how it might look after refactoring

Format your response as follows:

## Suggestion 1
### Type
(Type of refactoring)

### Description
(Description of the issue)

### Location
(Where to apply the refactoring)

### Recommendation
(Detailed explanation of the proposed change)

```python
# Example code after refactoring
```

Repeat for each suggestion.
"""
        
        # 從 LLM 獲取建議
        llm_response = self.llm_client.get_completion(prompt)
        
        # 解析 LLM 回應以提取結構化建議
        suggestions = self._parse_llm_refactoring_suggestions(llm_response)
        
        return {
            'quality_analysis': quality_analysis,
            'patterns_analysis': patterns_analysis,
            'llm_suggestions': suggestions
        }
    
    def _parse_llm_refactoring_suggestions(self, llm_response: str) -> List[Dict]:
        """
        解析 LLM 回應以提取結構化重構建議。
        
        Args:
            llm_response: LLM 的回應
            
        Returns:
            結構化重構建議列表
        """
        suggestions = []
        
        # 確保我們有有效的回應可供解析
        if not llm_response or not isinstance(llm_response, str):
            print(f"警告：無效的 LLM 回應：{type(llm_response)}")
            return suggestions
        
        try:
            # 嘗試提取 JSON 格式（如果存在）
            json_regex = r'```json\s*([\s\S]*?)\s*```'
            json_matches = re.findall(json_regex, llm_response)
            
            if json_matches:
                import json
                try:
                    parsed_json = json.loads(json_matches[0])
                    # 處理數組和對象回應
                    if isinstance(parsed_json, list):
                        suggestions = parsed_json
                    elif isinstance(parsed_json, dict) and 'suggestions' in parsed_json:
                        suggestions = parsed_json['suggestions']
                    else:
                        suggestions = [parsed_json]  # 將單個建議作為對象
                except json.JSONDecodeError:
                    print("無法解析 LLM 回應中的 JSON，回退到正則表達式解析")
            
            # 退回到按部分解析建議
            if not suggestions:
                try:
                    # 首先嘗試 "## Suggestion N" 格式
                    suggestion_regex = r'## Suggestion (\d+)[\s\S]*?(?=## Suggestion \d+|$)'
                    matches = re.findall(suggestion_regex, llm_response)
                    
                    if not matches:
                        # 嘗試可能存在的替代格式
                        suggestion_regex = r'Suggestion (\d+):([\s\S]*?)(?=Suggestion \d+:|$)'
                        matches = re.findall(suggestion_regex, llm_response)
                    
                    if matches:
                        for i, match in enumerate(matches):
                            suggestion_num = match[0] if isinstance(match, tuple) else match
                            content = match[1] if isinstance(match, tuple) else llm_response
                            
                            # 提取部分
                            type_match = re.search(r'Type[:\s]+([\s\S]*?)(?=Description|Location|\n\n)', content)
                            desc_match = re.search(r'Description[:\s]+([\s\S]*?)(?=Type|Location|Recommendation|\n\n)', content)
                            loc_match = re.search(r'Location[:\s]+([\s\S]*?)(?=Type|Description|Recommendation|\n\n)', content)
                            rec_match = re.search(r'Recommendation[:\s]+([\s\S]*?)(?=\n```|\n\n|$)', content)
                            
                            # 提取代碼示例（如果可用）
                            code_match = re.search(r'```python\s*([\s\S]*?)\s*```', content)
                            
                            suggestion = {
                                'id': int(suggestion_num) if suggestion_num.isdigit() else i + 1,
                                'type': type_match.group(1).strip() if type_match else "未知",
                                'description': desc_match.group(1).strip() if desc_match else "",
                                'location': loc_match.group(1).strip() if loc_match else "",
                                'recommendation': rec_match.group(1).strip() if rec_match else "",
                                'code_example': code_match.group(1) if code_match else ""
                            }
                            
                            suggestions.append(suggestion)
                except Exception as regex_error:
                    print(f"正則表達式解析錯誤：{regex_error}")
                    
            # 如果未提取任何建議，請從整個回應創建一個通用建議
            if not suggestions:
                suggestions.append({
                    'id': 1,
                    'type': "一般重構",
                    'description': "來自 LLM 的重構建議",
                    'location': "整個文件",
                    'recommendation': llm_response[:500] + ("..." if len(llm_response) > 500 else ""),
                    'code_example': ""
                })
            
            # 去除重複建議
            unique_suggestions = {}
            for suggestion in suggestions:
                # 根據類型和描述創建唯一鍵
                key = f"{suggestion['type']}|{suggestion['description']}"
                if key not in unique_suggestions:
                    unique_suggestions[key] = suggestion
            
            # 用去重後的建議替換原始建議列表
            suggestions = list(unique_suggestions.values())
                    
            # 去重後重新分配 ID
            for i, suggestion in enumerate(suggestions):
                suggestion['id'] = i + 1
                    
        except Exception as e:
            print(f"解析 LLM 建議時出錯：{e}")
            import traceback
            print(traceback.format_exc())
            
        return suggestions
    
    def generate_refactored_code(self, file_path: str, suggestion_id: int) -> Optional[str]:
        """
        根據特定建議生成重構代碼。
        
        Args:
            file_path: Python 文件的路徑
            suggestion_id: 要應用的建議的 ID
            
        Returns:
            重構代碼的字符串，如果生成失敗則返回 None
        """
        # 直接從 suggestion_store 獲取建議
        from refactoring.suggestion_generator import SuggestionGenerator
        suggestion_store = SuggestionGenerator().suggestion_store
        suggestion = suggestion_store.get_suggestion(suggestion_id)
        
        if not suggestion:
            print(f"未找到 ID 為 {suggestion_id} 的建議。")
            return None
        
        # 讀取原始文件內容
        file_content = read_file(file_path)
        
        # 為重構代碼生成準備提示
        prompt_template = get_template('generate_refactored_code')
        
        # 為模板創建兼容字典
        target_suggestion = {
            'type': suggestion.type,
            'description': suggestion.description,
            'location': f"行 {suggestion.location.get('start_line', '未知')}-{suggestion.location.get('end_line', '未知')}",
            'recommendation': suggestion.recommendation
        }
        
        # 如果未找到模板，則使用默認模板
        if prompt_template:
            prompt = prompt_template.format(
                original_code=file_content,
                suggestion_type=target_suggestion['type'],
                suggestion_description=target_suggestion['description'],
                suggestion_location=target_suggestion['location'],
                suggestion_recommendation=target_suggestion['recommendation']
            )
        else:
            # 默認模板
            prompt = f"""
    Refactor the following Python code based on the suggestion:

    Original Code:
    ```python
    {file_content}

Refactoring Suggestion:
- Type: {target_suggestion['type']}
- Description: {target_suggestion['description']}
- Location: {target_suggestion['location']}
- Recommendation: {target_suggestion['recommendation']}

Please provide the complete refactored code (the entire file with the changes applied). 
Ensure the refactored code maintains the same functionality while addressing the suggestion. 
Include comments explaining the changes you made.
"""
        
        # 從 LLM 獲取重構代碼
        refactored_code = self.llm_client.get_completion(prompt)
        
        # 如果包裝在 markdown 代碼塊中，則從回應中提取代碼
        code_match = re.search(r'```python\s*([\s\S]*?)\s*```', refactored_code)
        if code_match:
            refactored_code = code_match.group(1)
        
        return refactored_code
    
    def apply_refactoring(self, file_path: str, refactored_code: str) -> bool:
        """
        將重構代碼應用於文件。
        
        Args:
            file_path: Python 文件的路徑
            refactored_code: 要應用的重構代碼
            
        Returns:
            如果重構成功應用則返回 True，否則返回 False
        """
        # 驗證重構代碼是有效的 Python
        try:
            ast.parse(refactored_code)
        except SyntaxError:
            return False
        
        # 將重構代碼寫入文件
        return write_file(file_path, refactored_code)
    
    def perform_automated_refactoring(self, file_path: str, refactoring_type: str, **kwargs) -> bool:
        """
        使用 rope 庫執行自動重構。
        
        Args:
            file_path: Python 文件的路徑
            refactoring_type: 要執行的重構類型
            **kwargs: 重構的其他參數
            
        Returns:
            如果重構成功應用則返回 True，否則返回 False
        """
        try:
            # 獲取 rope 資源
            resource = libutils.path_to_resource(self.rope_project, file_path)
            
            if refactoring_type == 'rename':
                # 執行重命名重構
                offset = kwargs.get('offset', 0)
                new_name = kwargs.get('new_name', '')
                
                if not new_name:
                    return False
                
                renamer = Rename(self.rope_project, resource, offset)
                changes = renamer.get_changes(new_name)
                self.rope_project.do(changes)
                return True
                
            elif refactoring_type == 'extract_method':
                # 執行提取方法重構
                start_offset = kwargs.get('start_offset', 0)
                end_offset = kwargs.get('end_offset', 0)
                method_name = kwargs.get('method_name', '')
                
                if not method_name or start_offset >= end_offset:
                    return False
                
                extractor = ExtractMethod(self.rope_project, resource, start_offset, end_offset)
                changes = extractor.get_changes(method_name)
                self.rope_project.do(changes)
                return True
                
            elif refactoring_type == 'move_module':
                # 執行移動模塊重構
                destination = kwargs.get('destination', '')
                
                if not destination:
                    return False
                
                mover = MoveModule(self.rope_project, resource)
                destination_folder = libutils.path_to_resource(self.rope_project, destination)
                changes = mover.get_changes(destination_folder)
                self.rope_project.do(changes)
                return True
                
            else:
                return False
                
        except Exception as e:
            print(f"自動重構錯誤：{e}")
            return False
            
        finally:
            # 保存項目
            self.rope_project.close()