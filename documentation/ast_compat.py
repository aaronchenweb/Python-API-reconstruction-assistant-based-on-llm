"""
為僅在較新的 Python 版本中可用的 AST 操作提供向後兼容性。
"""
import ast
import sys


def ast_unparse(node):
    """
    ast.unparse() 的兼容性函數，該函數在 Python 3.9 中引入。
    此函數為常見節點類型提供基本實現。
    
    Args:
        node: 一個 AST 節點
        
    Returns:
        節點的字符串表示
    """
    if node is None:
        return "None"
    
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            # 處理字符串常量，適當轉義
            return repr(node.value)
        return str(node.value)
        
    elif isinstance(node, ast.Name):
        return node.id
        
    elif isinstance(node, ast.Attribute):
        return f"{ast_unparse(node.value)}.{node.attr}"
        
    elif isinstance(node, ast.Subscript):
        if hasattr(node, 'slice') and isinstance(node.slice, ast.Index):
            # Python 3.8 有 Index 節點
            return f"{ast_unparse(node.value)}[{ast_unparse(node.slice.value)}]"
        else:
            # Python 3.9+ 有簡化的切片表示
            return f"{ast_unparse(node.value)}[{ast_unparse(node.slice)}]"
            
    elif isinstance(node, ast.BinOp):
        # 處理二元運算，如 1 + 2
        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.FloorDiv: "//",
            ast.Mod: "%",
            ast.Pow: "**"
        }
        op_str = op_map.get(type(node.op), "?")
        return f"{ast_unparse(node.left)} {op_str} {ast_unparse(node.right)}"
        
    elif isinstance(node, ast.UnaryOp):
        # 處理一元運算，如 -1
        op_map = {
            ast.UAdd: "+",
            ast.USub: "-",
            ast.Not: "not "
        }
        op_str = op_map.get(type(node.op), "?")
        return f"{op_str}{ast_unparse(node.operand)}"
        
    elif isinstance(node, ast.List):
        # 處理列表字面量
        items = [ast_unparse(elt) for elt in node.elts]
        return f"[{', '.join(items)}]"
        
    elif isinstance(node, ast.Tuple):
        # 處理元組字面量
        items = [ast_unparse(elt) for elt in node.elts]
        if len(items) == 1:
            return f"({items[0]},)"
        return f"({', '.join(items)})"
        
    elif isinstance(node, ast.Dict):
        # 處理字典字面量
        items = []
        for key, value in zip(node.keys, node.values):
            key_str = ast_unparse(key)
            value_str = ast_unparse(value)
            items.append(f"{key_str}: {value_str}")
        return f"{{{', '.join(items)}}}"
        
    elif isinstance(node, ast.Call):
        # 處理函數調用
        func_str = ast_unparse(node.func)
        args = [ast_unparse(arg) for arg in node.args]
        keywords = [f"{kw.arg}={ast_unparse(kw.value)}" for kw in node.keywords]
        all_args = args + keywords
        return f"{func_str}({', '.join(all_args)})"
    
    # 對其他節點類型使用簡單的字符串表示
    return f"<{node.__class__.__name__}>"


# 如果不可用，提供 ast.unparse
if not hasattr(ast, 'unparse'):
    ast.unparse = ast_unparse