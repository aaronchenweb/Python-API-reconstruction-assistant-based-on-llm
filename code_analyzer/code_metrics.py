import ast
import os
from typing import Dict, Any, List
import re

def calculate_code_complexity(node: ast.AST) -> int:
    """
    計算代碼的循環複雜度
    使用McCabe複雜度算法的簡化版本
    """
    complexity = 1  # 基礎複雜度為1
    
    # 遍歷AST並計數分支節點
    for child in ast.walk(node):
        # 條件分支
        if isinstance(child, (ast.If, ast.While, ast.For)):
            complexity += 1
        # 邏輯操作符增加複雜度
        elif isinstance(child, ast.BoolOp) and isinstance(child.op, ast.And):
            complexity += len(child.values) - 1
        # 異常處理
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
    
    return complexity

def get_code_metrics(file_content: str) -> Dict[str, Any]:
    """
    計算代碼的各種指標，包括對docstring的處理
    
    Args:
        file_content: Python文件的內容字符串
        
    Returns:
        包含代碼指標的字典
    """
    try:
        tree = ast.parse(file_content)
        
        # 計算總體複雜度
        total_complexity = calculate_code_complexity(tree)
        
        # 計算每個函數的複雜度
        function_complexities = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = calculate_code_complexity(node)
                function_complexities.append({
                    'name': node.name,
                    'complexity': complexity,
                    'line': node.lineno
                })
        
        # 代碼行數統計
        lines = file_content.splitlines()
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        
        # 計算普通註釋行（以#開頭）
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        
        # 計算docstring行數（使用正則表達式查找三引號文檔字符串）
        docstring_pattern = re.compile(r'""".*?"""', re.DOTALL)
        docstring_matches = docstring_pattern.findall(file_content)
        docstring_lines = sum(s.count('\n') + 1 for s in docstring_matches)
        
        # 調整註釋行計數，包括docstring
        total_comment_lines = comment_lines + docstring_lines
        
        # 計算代碼行（排除空行和所有形式的註釋）
        code_lines = total_lines - blank_lines - total_comment_lines
        
        # 計算可維護性指數 - 使用簡化公式
        # 標準MI = 171 - 5.2 * ln(V) - 0.23 * C - 16.2 * ln(L)
        # 這裡使用簡化計算，主要考慮複雜度和註釋率
        comment_ratio = total_comment_lines / total_lines if total_lines > 0 else 0
        avg_complexity = sum(f['complexity'] for f in function_complexities) / len(function_complexities) if function_complexities else 1
        
        # 使用一個更寬容的可維護性計算
        # 範圍大約在0-100之間，較高的值表示更好的可維護性
        maintainability_index = max(0, min(100, 100 - (avg_complexity * 5) + (comment_ratio * 50)))
        
        # 返回所有計算的指標
        return {
            'total_complexity': total_complexity,
            'function_complexities': function_complexities,
            'total_lines': total_lines,
            'blank_lines': blank_lines,
            'comment_lines': total_comment_lines,  # 現在包括docstring
            'code_lines': code_lines,
            'avg_function_complexity': avg_complexity,
            'comment_ratio': comment_ratio,
            'maintainability_index': maintainability_index,
            'function_count': len(function_complexities)
        }

    except Exception as e:
        return {'error': str(e)}
    
def calculate_metrics(file_path):
    """
    讀取檔案並對其內容呼叫 get_code_metrics。
    
    Args:
        file_path: 要分析的Python文件路徑
        
    Returns:
        包含代碼指標的字典
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    return get_code_metrics(content)