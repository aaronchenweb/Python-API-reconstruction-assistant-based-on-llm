import ast
import logging
from typing import Dict, List, Any, Tuple

class PythonASTVisitor(ast.NodeVisitor):
    """
    訪問者模式實現，用於遍歷Python AST並收集代碼結構信息
    """
    def __init__(self):
        self.imports = []
        self.functions = []
        self.classes = []
        self.global_vars = []
        self.function_calls = []
        
    def visit_Import(self, node):
        for name in node.names:
            self.imports.append({
                'name': name.name,
                'alias': name.asname,
                'line': node.lineno
            })
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node):
        for name in node.names:
            self.imports.append({
                'name': f"{node.module}.{name.name}" if node.module else name.name,
                'alias': name.asname,
                'line': node.lineno,
                'from_import': True,
                'module': node.module
            })
        self.generic_visit(node)
        
    def visit_FunctionDef(self, node):
        args = [arg.arg for arg in node.args.args]
        doc = ast.get_docstring(node)
        
        function_info = {
            'name': node.name,
            'args': args,
            'line': node.lineno,
            'end_line': node.end_lineno if hasattr(node, 'end_lineno') else None,
            'decorator_list': [d.id if isinstance(d, ast.Name) else None for d in node.decorator_list],
            'docstring': doc
        }
        
        self.functions.append(function_info)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}" if hasattr(base.value, 'id') else "unknown")
        
        doc = ast.get_docstring(node)
        
        class_info = {
            'name': node.name,
            'bases': bases,
            'line': node.lineno,
            'end_line': node.end_lineno if hasattr(node, 'end_lineno') else None,
            'methods': [],
            'docstring': doc
        }
        
        # 記錄類當前方法，暫存當前狀態
        current_functions = self.functions
        self.functions = []
        
        # 遍歷類的內容
        self.generic_visit(node)
        
        # 保存類的方法
        class_info['methods'] = self.functions
        
        # 恢復原來的方法列表
        self.functions = current_functions
        
        self.classes.append(class_info)
    
    def visit_Assign(self, node):
        # 只處理模塊級別的全局變量
        if isinstance(node.targets[0], ast.Name):
            self.global_vars.append({
                'name': node.targets[0].id,
                'line': node.lineno
            })
        self.generic_visit(node)
        
    def visit_Call(self, node):
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if hasattr(node.func.value, 'id'):
                func_name = f"{node.func.value.id}.{node.func.attr}"
            else:
                func_name = f"(...).{node.func.attr}"
        
        if func_name:
            self.function_calls.append({
                'name': func_name,
                'line': node.lineno
            })
        
        self.generic_visit(node)

def analyze_python_file(file_content: str) -> Dict[str, Any]:
    """
    分析Python文件內容，返回代碼結構分析結果
    
    Args:
        file_content: Python文件的內容字符串
        
    Returns:
        包含代碼結構信息的字典
    """
    try:
        # 解析代碼為AST
        tree = ast.parse(file_content)
        
        # 訪問AST
        visitor = PythonASTVisitor()
        visitor.visit(tree)
        
        # 代碼基本信息
        num_lines = len(file_content.splitlines())
        code_lines = num_lines - file_content.count('\n\n')  # 簡單估計非空行
        
        # 返回分析結果
        return {
            'imports': visitor.imports,
            'functions': visitor.functions,
            'classes': visitor.classes,
            'global_vars': visitor.global_vars,
            'function_calls': visitor.function_calls,
            'num_lines': num_lines,
            'code_lines': code_lines,
            'num_functions': len(visitor.functions),
            'num_classes': len(visitor.classes)
        }
    
    except SyntaxError as e:
        logging.error(f"語法錯誤: {str(e)}")
        return {
            'error': f"語法錯誤: {str(e)}",
            'line': e.lineno,
            'offset': e.offset,
            'text': e.text
        }
    except Exception as e:
        logging.error(f"分析錯誤: {str(e)}")
        return {'error': f"分析錯誤: {str(e)}"}
