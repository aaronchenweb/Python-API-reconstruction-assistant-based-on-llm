"""
用於從 Python 代碼生成 API 文檔的模組。
"""
import ast
import os
import re
import inspect
import importlib.util
from typing import Dict, List, Optional, Any, Set, Tuple
import logging
from dataclasses import dataclass

from utils.file_operations import read_file, write_file


@dataclass
class DocstringInfo:
    """從文檔字符串中提取的信息。"""
    summary: str = ""
    description: str = ""
    params: Dict[str, str] = None
    returns: str = ""
    raises: Dict[str, str] = None
    examples: List[str] = None
    todo: List[str] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}
        if self.raises is None:
            self.raises = {}
        if self.examples is None:
            self.examples = []
        if self.todo is None:
            self.todo = []

class DocGenerator:
    """從 Python 代碼生成 API 文檔的class。"""
    
    def __init__(self, project_path: str, output_dir: str = "docs"):
        self.project_path = project_path
        self.output_dir = os.path.join(project_path, output_dir)
        self.logger = logging.getLogger(__name__)
        
        # 如果輸出目錄不存在，則創建它
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_docs_for_project(self) -> Dict[str, Any]:
        """
        為整個項目生成文檔。
        
        Returns:
            包含生成統計信息和結果的字典
        """
        stats = {
            'files_processed': 0,
            'modules_documented': 0,
            'classes_documented': 0,
            'functions_documented': 0,
            'missing_docstrings': [],
            'generated_files': []
        }
        
        # 獲取所有 Python 文件
        python_files = self._get_python_files(self.project_path)
        
        # 為每個文件生成文檔
        for file_path in python_files:
            try:
                rel_path = os.path.relpath(file_path, self.project_path)
                self.logger.info(f"為 {rel_path} 生成文檔")
                
                # 生成文檔
                doc_result = self.generate_docs_for_file(file_path)
                if doc_result:
                    stats['files_processed'] += 1
                    stats['modules_documented'] += 1
                    stats['classes_documented'] += doc_result.get('classes_documented', 0)
                    stats['functions_documented'] += doc_result.get('functions_documented', 0)
                    stats['missing_docstrings'].extend(doc_result.get('missing_docstrings', []))
                    stats['generated_files'].append(doc_result.get('output_file'))
            except Exception as e:
                self.logger.error(f"為 {file_path} 生成文檔時出錯: {str(e)}")
        
        # 生成索引文件
        self._generate_index(stats)
        
        return stats
    
    def generate_docs_for_file(self, file_path: str) -> Dict[str, Any]:
        """
        為單個 Python 文件生成文檔。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含生成統計信息和結果的字典
        """
        result = {
            'classes_documented': 0,
            'functions_documented': 0,
            'missing_docstrings': [],
            'output_file': None
        }
        
        # 讀取文件
        file_content = read_file(file_path)
        if not file_content:
            return None
        
        # 解析代碼
        try:
            tree = ast.parse(file_content)
        except SyntaxError as e:
            self.logger.error(f"{file_path} 中的語法錯誤: {str(e)}")
            return None
        
        # 提取模組信息
        module_name = self._get_module_name(file_path)
        module_docstring = ast.get_docstring(tree)
        
        # 準備輸出文件路徑
        rel_path = os.path.relpath(file_path, self.project_path)
        doc_path = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
        output_file = os.path.join(self.output_dir, f"{doc_path}.md")
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 初始化文檔內容
        doc_content = f"# module `{module_name}`\n\n"
        
        # 添加模組文檔字符串
        if module_docstring:
            docstring_info = self._parse_docstring(module_docstring)
            doc_content += f"{docstring_info.description}\n\n"
        else:
            result['missing_docstrings'].append(f"{module_name} (module)")
        
        # 提取class
        classes = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append(self._document_class(node, file_content))
                result['classes_documented'] += 1
        
        # 提取函數（非方法）
        functions = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                functions.append(self._document_function(node, file_content))
                result['functions_documented'] += 1
        
        # 添加class部分
        if classes:
            doc_content += "## class\n\n"
            
            # 添加class摘要表
            doc_content += "| class | description |\n"
            doc_content += "|-------|-------------|\n"
            for cls in classes:
                summary = cls.get('docstring_info', DocstringInfo()).summary or "no description"
                doc_content += f"| [`{cls['name']}`](#{cls['name'].lower()}) | {summary} |\n"
            
            doc_content += "\n"
            
            # 添加詳細class文檔
            for cls in classes:
                doc_content += self._format_class_doc(cls)
        
        # 添加函數部分
        if functions:
            doc_content += "## Functions\n\n"
            
            # 添加函數摘要表
            doc_content += "| Functions | description |\n"
            doc_content += "|----------|-------------|\n"
            for func in functions:
                summary = func.get('docstring_info', DocstringInfo()).summary or "no description"
                doc_content += f"| [`{func['name']}()`](#{func['name'].lower()}) | {summary} |\n"
            
            doc_content += "\n"
            
            # 添加詳細函數文檔
            for func in functions:
                doc_content += self._format_function_doc(func)
        
        # 將文檔寫入文件
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        write_file(output_file, doc_content)
        result['output_file'] = output_file
        
        return result
    
    def check_documentation_coverage(self, file_path: str) -> Dict[str, Any]:
        """
        檢查 Python 文件的文檔覆蓋率。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含覆蓋率統計信息的字典
        """
        coverage = {
            'module_has_docstring': False,
            'classes_total': 0,
            'classes_with_docstrings': 0,
            'methods_total': 0,
            'methods_with_docstrings': 0,
            'functions_total': 0,
            'functions_with_docstrings': 0,
            'missing_docstrings': [],
            'overall_coverage': 0.0
        }
        
        # 讀取文件
        file_content = read_file(file_path)
        if not file_content:
            return coverage
        
        # 解析代碼
        try:
            tree = ast.parse(file_content)
        except SyntaxError:
            return coverage
        
        # 檢查模組文檔字符串
        module_name = self._get_module_name(file_path)
        module_docstring = ast.get_docstring(tree)
        coverage['module_has_docstring'] = bool(module_docstring)
        if not module_docstring:
            coverage['missing_docstrings'].append(f"{module_name} (module)")
        
        # 檢查class和方法
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                coverage['classes_total'] += 1
                class_name = node.name
                class_docstring = ast.get_docstring(node)
                
                if class_docstring:
                    coverage['classes_with_docstrings'] += 1
                else:
                    coverage['missing_docstrings'].append(f"{class_name} (class)")
                
                # 檢查方法
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        coverage['methods_total'] += 1
                        method_name = item.name
                        method_docstring = ast.get_docstring(item)
                        
                        if method_docstring:
                            coverage['methods_with_docstrings'] += 1
                        else:
                            coverage['missing_docstrings'].append(f"{class_name}.{method_name} (method)")
        
        # 檢查函數
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                coverage['functions_total'] += 1
                function_name = node.name
                function_docstring = ast.get_docstring(node)
                
                if function_docstring:
                    coverage['functions_with_docstrings'] += 1
                else:
                    coverage['missing_docstrings'].append(f"{function_name} (function)")
        
        # 計算總體覆蓋率
        total_items = 1 + coverage['classes_total'] + coverage['methods_total'] + coverage['functions_total']
        documented_items = (1 if coverage['module_has_docstring'] else 0) + coverage['classes_with_docstrings'] + coverage['methods_with_docstrings'] + coverage['functions_with_docstrings']
        
        if total_items > 0:
            coverage['overall_coverage'] = round(documented_items / total_items * 100, 2)
        
        return coverage
    
    def analyze_docstring_quality(self, file_path: str) -> Dict[str, Any]:
        """
        分析 Python 文件中文檔字符串的品質。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含品質度量的字典
        """
        quality = {
            'complete_docstrings': 0,
            'incomplete_docstrings': 0,
            'detailed_metrics': [],
            'overall_quality': 0.0
        }
        
        # 讀取文件
        file_content = read_file(file_path)
        if not file_content:
            return quality
        
        # 解析代碼
        try:
            tree = ast.parse(file_content)
        except SyntaxError:
            return quality
        
        # 分析模組文檔字符串
        module_name = self._get_module_name(file_path)
        module_docstring = ast.get_docstring(tree)
        
        if module_docstring:
            module_quality = self._analyze_docstring_quality(module_docstring, 'module', module_name)
            quality['detailed_metrics'].append(module_quality)
            
            if module_quality['score'] > 0.7:
                quality['complete_docstrings'] += 1
            else:
                quality['incomplete_docstrings'] += 1
        
        # 分析class和方法
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                class_docstring = ast.get_docstring(node)
                
                if class_docstring:
                    class_quality = self._analyze_docstring_quality(class_docstring, 'class', class_name)
                    quality['detailed_metrics'].append(class_quality)
                    
                    if class_quality['score'] > 0.7:
                        quality['complete_docstrings'] += 1
                    else:
                        quality['incomplete_docstrings'] += 1
                
                # 分析方法
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = f"{class_name}.{item.name}"
                        method_docstring = ast.get_docstring(item)
                        
                        if method_docstring:
                            method_quality = self._analyze_docstring_quality(method_docstring, 'method', method_name)
                            quality['detailed_metrics'].append(method_quality)
                            
                            if method_quality['score'] > 0.7:
                                quality['complete_docstrings'] += 1
                            else:
                                quality['incomplete_docstrings'] += 1
        
        # 分析函數
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                function_docstring = ast.get_docstring(node)
                
                if function_docstring:
                    function_quality = self._analyze_docstring_quality(function_docstring, 'function', function_name)
                    quality['detailed_metrics'].append(function_quality)
                    
                    if function_quality['score'] > 0.7:
                        quality['complete_docstrings'] += 1
                    else:
                        quality['incomplete_docstrings'] += 1
        
        # 計算總體品質
        total_docstrings = quality['complete_docstrings'] + quality['incomplete_docstrings']
        
        if total_docstrings > 0:
            quality['overall_quality'] = round(quality['complete_docstrings'] / total_docstrings * 100, 2)
        
        return quality
    
    def _generate_docstring_with_llm(self, code_context: str, element_type: str, element_name: str, parent_node: Optional[ast.AST], llm_client) -> str:
        """使用 LLM 生成文檔字符串。"""
        if not llm_client:
            return self._generate_simple_docstring(None, element_type, element_name)
        
        # Parent context preparation (unchanged)
        parent_context = ""
        if element_type == 'method' and parent_node:
            parent_context = f"此方法是class '{parent_node.name}' 的一部分。\n"
            parent_docstring = ast.get_docstring(parent_node)
            if parent_docstring:
                parent_context += f"class描述為: {parent_docstring}\n"
        
        # Clearer prompt with explicit formatting instructions
        prompt = f"""
    為以下 Python {element_type} 生成一個全面的文檔字符串:

    {parent_context}
    {code_context}

    文檔字符串應遵循 Google 風格格式並包括:
    1. 簡短的一行摘要
    2. 更詳細的描述（如適用）
    3. 參數及其class型和描述（對於函數/方法）
    4. 返回值及其class型和描述（對於函數/方法）
    5. 拋出的異常（如有）
    6. 示例（可選）

    重要：返回純文本格式的文檔字符串。不要包含任何Markdown格式（如```或```python）。
    不要添加文檔字符串外的三重引號，僅返回文檔字符串的實際內容。
    """
        
        # 使用 LLM 生成文檔字符串
        response = llm_client.get_completion(prompt)
        
        # Enhanced cleaning of response
        docstring = response.strip()
        
        # Remove all markdown formatting
        docstring = re.sub(r'```python', '', docstring)
        docstring = re.sub(r'```', '', docstring)
        
        return docstring.strip()
    
    def _generate_simple_docstring(self, node: ast.AST, element_type: str, element_name: str) -> str:
        """
        基於代碼分析生成簡單的文檔字符串，無需 LLM。
        
        Args:
            node: AST 節點
            element_type: 元素class型
            element_name: 元素名稱
            
        Returns:
            生成的文檔字符串
        """
        if element_type == 'module':
            return f"{element_name} 模組。\n\n模組功能的描述。"
        
        elif element_type == 'class':
            return f"{element_name.lower()} 的class。\n\n提供與 {element_name.lower()} 相關的功能。"
        
        elif element_type == 'function':
            params = []
            returns = ""
            
            if isinstance(node, ast.FunctionDef):
                # 提取參數
                for arg in node.args.args:
                    if arg.arg != 'self':
                        arg_type = "Any"
                        if arg.annotation and hasattr(arg.annotation, 'id'):
                            arg_type = arg.annotation.id
                        params.append(f"{arg.arg}: {arg_type}")
                
                # 提取返回class型
                if node.returns:
                    if hasattr(node.returns, 'id'):
                        returns = f"Returns:\n    {node.returns.id}: 返回值的描述。"
                    else:
                        returns = "Returns:\n    返回值的描述。"
            
            param_text = ""
            if params:
                param_text = "Args:\n    " + "\n    ".join(f"{p}: 參數描述" for p in params) + "\n\n"
            
            return f"函數用於 {element_name.lower().replace('_', ' ')}。\n\n{param_text}{returns}"
        
        elif element_type == 'method':
            class_name = element_name.split('.')[0]
            method_name = element_name.split('.')[1]
            
            params = []
            returns = ""
            
            if isinstance(node, ast.FunctionDef):
                # 提取參數
                for arg in node.args.args:
                    if arg.arg != 'self':
                        arg_type = "Any"
                        if arg.annotation and hasattr(arg.annotation, 'id'):
                            arg_type = arg.annotation.id
                        params.append(f"{arg.arg}: {arg_type}")
                
                # 提取返回class型
                if node.returns:
                    if hasattr(node.returns, 'id'):
                        returns = f"Returns:\n    {node.returns.id}: 返回值的描述。"
                    else:
                        returns = "Returns:\n    返回值的描述。"
            
            param_text = ""
            if params:
                param_text = "Args:\n    " + "\n    ".join(f"{p}: 參數描述" for p in params) + "\n\n"
            
            return f"方法用於 {method_name.lower().replace('_', ' ')}。\n\n{param_text}{returns}"
        
        return "需要描述。"
    
    def _find_class_node(self, tree: ast.AST, class_name: str) -> Optional[ast.ClassDef]:
        """按名稱查找class節點。"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
        return None
    
    def _find_function_node(self, tree: ast.AST, function_name: str) -> Optional[ast.FunctionDef]:
        """按名稱查找函數節點。"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                return node
        return None
    
    def _analyze_docstring_quality(self, docstring: str, element_type: str, element_name: str) -> Dict[str, Any]:
        """
        分析文檔字符串的品質。
        
        Args:
            docstring: 要分析的文檔字符串
            element_type: 元素class型
            element_name: 元素名稱
            
        Returns:
            包含品質度量的字典
        """
        quality = {
            'type': element_type,
            'name': element_name,
            'issues': [],
            'score': 0.0
        }
        
        # 解析文檔字符串
        docstring_info = self._parse_docstring(docstring)
        
        # 檢查基本組件
        if not docstring_info.summary:
            quality['issues'].append('Missing summary')
        
        if element_type in ['function', 'method']:
            # 參數檢查
            if not docstring_info.params:
                quality['issues'].append('Missing parameter descriptions')
            
            # 返回值檢查
            if not docstring_info.returns:
                quality['issues'].append('Missing return description')
            
            # 異常檢查
            if not docstring_info.raises:
                quality['issues'].append('Missing exception descriptions')
        
        # 風格和內容品質
        lines = docstring.splitlines()
        if len(lines) > 0 and not lines[0].strip():
            quality['issues'].append('First line should be a summary')
        
        if len(docstring.strip()) < 10:
            quality['issues'].append('Docstring is too short')
        
        # 基於問題計算分數
        base_score = 1.0
        deduction_per_issue = 0.15
        quality['score'] = max(0.0, base_score - len(quality['issues']) * deduction_per_issue)
        
        return quality
    
    def _parse_docstring(self, docstring: str) -> DocstringInfo:
        """
        解析文檔字符串以提取組件。
        
        Args:
            docstring: 要解析的文檔字符串
            
        Returns:
            帶有解析組件的 DocstringInfo 對象
        """
        if not docstring:
            return DocstringInfo()
        
        info = DocstringInfo()
        
        # 將文檔字符串分割為行
        lines = docstring.splitlines()
        
        # 提取摘要（第一行）
        if lines and lines[0].strip():
            info.summary = lines[0].strip()
        
        # 提取描述
        description_lines = []
        section = 'description'
        
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            
            if not line:
                continue
            
            # 檢查部分標題
            if line.lower().startswith(('args:', 'arguments:', 'parameters:')):
                section = 'params'
                continue
            elif line.lower().startswith('returns:'):
                section = 'returns'
                continue
            elif line.lower().startswith(('raises:', 'exceptions:', 'throws:')):
                section = 'raises'
                continue
            elif line.lower().startswith('examples:'):
                section = 'examples'
                continue
            elif line.lower().startswith('todo:'):
                section = 'todo'
                continue
            
            # 基於當前部分處理
            if section == 'description':
                description_lines.append(line)
            elif section == 'params':
                param_match = re.match(r'(\w+)(?:\s+\(([^)]+)\))?\s*:\s*(.*)', line)
                if param_match:
                    param_name = param_match.group(1)
                    param_desc = param_match.group(3)
                    info.params[param_name] = param_desc
            elif section == 'returns':
                info.returns += line + " "
            elif section == 'raises':
                exception_match = re.match(r'(\w+)(?:\s+\(([^)]+)\))?\s*:\s*(.*)', line)
                if exception_match:
                    exception_name = exception_match.group(1)
                    exception_desc = exception_match.group(3)
                    info.raises[exception_name] = exception_desc
            elif section == 'examples':
                info.examples.append(line)
            elif section == 'todo':
                info.todo.append(line)
        
        info.description = '\n'.join(description_lines).strip()
        info.returns = info.returns.strip()
        
        return info
    
    def _document_class(self, node: ast.ClassDef, file_content: str) -> Dict[str, Any]:
        """
        提取class的文檔。
        
        Args:
            node: ClassDef 節點
            file_content: 文件內容
            
        Returns:
            包含class文檔的字典
        """
        class_info = {
            'name': node.name,
            'lineno': node.lineno,
            'bases': [self._get_name(base) for base in node.bases],
            'docstring': ast.get_docstring(node),
            'docstring_info': DocstringInfo(),
            'methods': []
        }
        
        # 解析文檔字符串
        if class_info['docstring']:
            class_info['docstring_info'] = self._parse_docstring(class_info['docstring'])
        
        # 提取方法
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_info = self._document_function(item, file_content)
                class_info['methods'].append(method_info)
        
        return class_info
    
    def _document_function(self, node: ast.FunctionDef, file_content: str) -> Dict[str, Any]:
        """
        提取函數或方法的文檔。
        
        Args:
            node: FunctionDef 節點
            file_content: 文件內容
            
        Returns:
            包含函數文檔的字典
        """
        func_info = {
            'name': node.name,
            'lineno': node.lineno,
            'args': [],
            'return_type': None,
            'docstring': ast.get_docstring(node),
            'docstring_info': DocstringInfo()
        }
        
        # 提取參數
        for arg in node.args.args:
            if arg.arg == 'self':
                continue
                
            arg_info = {
                'name': arg.arg,
                'type': None,
                'has_default': False,
                'default': None
            }
            
            # 提取class型註解
            if arg.annotation:
                arg_info['type'] = self._get_name(arg.annotation)
            
            func_info['args'].append(arg_info)
        
        # 提取默認值
        defaults_offset = len(node.args.args) - len(node.args.defaults)
        for i, default in enumerate(node.args.defaults):
            arg_idx = i + defaults_offset
            if arg_idx < len(func_info['args']):
                func_info['args'][arg_idx]['has_default'] = True
                func_info['args'][arg_idx]['default'] = ast.unparse(default)
        
        # 提取返回class型
        if node.returns:
            func_info['return_type'] = self._get_name(node.returns)
        
        # 解析文檔字符串
        if func_info['docstring']:
            func_info['docstring_info'] = self._parse_docstring(func_info['docstring'])
        
        return func_info
    
    def _get_name(self, node: ast.AST) -> str:
        """
        從 AST 節點獲取可讀名稱。
        
        Args:
            node: AST 節點
            
        Returns:
            節點的字符串表示
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        else:
            return ast.unparse(node)
    
    def _format_class_doc(self, cls: Dict[str, Any]) -> str:
        """
        將class文檔格式化為 Markdown。
        
        Args:
            cls: class信息字典
            
        Returns:
            Markdown 格式的文檔
        """
        doc = f"### `{cls['name']}`\n\n"
        
        # 添加繼承
        if cls['bases']:
            doc += f"**bases:** {', '.join(cls['bases'])}\n\n"
        
        # 添加class描述
        docstring_info = cls.get('docstring_info', DocstringInfo())
        if docstring_info.description:
            doc += f"{docstring_info.description}\n\n"
        elif cls.get('docstring'):
            doc += f"{cls['docstring']}\n\n"
        
        # 添加class方法
        if cls['methods']:
            doc += "#### methods\n\n"
            
            # 方法摘要表
            doc += "| methods | description |\n"
            doc += "|--------|-------------|\n"
            
            for method in cls['methods']:
                method_docstring_info = method.get('docstring_info', DocstringInfo())
                method_summary = method_docstring_info.summary or "no description"
                doc += f"| [`{method['name']}()`](#{cls['name'].lower()}.{method['name'].lower()}) | {method_summary} |\n"
            
            doc += "\n"
            
            # 詳細方法文檔
            for method in cls['methods']:
                doc += self._format_method_doc(method, cls['name'])
        
        return doc
    
    def _format_method_doc(self, method: Dict[str, Any], class_name: str) -> str:
        """
        將方法文檔格式化為 Markdown。
        
        Args:
            method: 方法信息字典
            class_name: 包含class的名稱
            
        Returns:
            Markdown 格式的文檔
        """
        doc = f"#### `{class_name}.{method['name']}()`\n\n"
        
        # 添加方法簽名
        signature = f"{method['name']}("
        
        for i, arg in enumerate(method['args']):
            if i > 0:
                signature += ", "
            
            signature += arg['name']
            
            if arg['type']:
                signature += f": {arg['type']}"
            
            if arg['has_default']:
                signature += f" = {arg['default']}"
        
        signature += ")"
        
        if method['return_type']:
            signature += f" -> {method['return_type']}"
        
        doc += f"```python\n{signature}\n```\n\n"
        
        # 添加方法描述
        docstring_info = method.get('docstring_info', DocstringInfo())
        if docstring_info.description:
            doc += f"{docstring_info.description}\n\n"
        elif method.get('docstring'):
            doc += f"{method['docstring']}\n\n"
        
        # 添加參數詳情
        if docstring_info.params:
            doc += "**參數:**\n\n"
            
            for param, desc in docstring_info.params.items():
                # 在 args 中尋找參數class型
                param_type = ""
                for arg in method['args']:
                    if arg['name'] == param and arg['type']:
                        param_type = f": {arg['type']}"
                        break
                
                doc += f"- `{param}{param_type}` - {desc}\n"
            
            doc += "\n"
        
        # 添加返回詳情
        if docstring_info.returns:
            doc += f"**返回:**\n\n{docstring_info.returns}\n\n"
        
        # 添加異常
        if docstring_info.raises:
            doc += "**拋出:**\n\n"
            
            for exc, desc in docstring_info.raises.items():
                doc += f"- `{exc}` - {desc}\n"
            
            doc += "\n"
        
        # 添加示例
        if docstring_info.examples:
            doc += "**示例:**\n\n"
            doc += "```python\n"
            for example in docstring_info.examples:
                doc += f"{example}\n"
            doc += "```\n\n"
        
        return doc
    
    def _format_function_doc(self, func: Dict[str, Any]) -> str:
        """
        將函數文檔格式化為 Markdown。
        
        Args:
            func: 函數信息字典
            
        Returns:
            Markdown 格式的文檔
        """
        doc = f"### `{func['name']}()`\n\n"
        
        # 添加函數簽名
        signature = f"{func['name']}("
        
        for i, arg in enumerate(func['args']):
            if i > 0:
                signature += ", "
            
            signature += arg['name']
            
            if arg['type']:
                signature += f": {arg['type']}"
            
            if arg['has_default']:
                signature += f" = {arg['default']}"
        
        signature += ")"
        
        if func['return_type']:
            signature += f" -> {func['return_type']}"
        
        doc += f"```python\n{signature}\n```\n\n"
        
        # 添加函數描述
        docstring_info = func.get('docstring_info', DocstringInfo())
        if docstring_info.description:
            doc += f"{docstring_info.description}\n\n"
        elif func.get('docstring'):
            doc += f"{func['docstring']}\n\n"
        
        # 添加參數詳情
        if docstring_info.params:
            doc += "**參數:**\n\n"
            
            for param, desc in docstring_info.params.items():
                # 在 args 中尋找參數class型
                param_type = ""
                for arg in func['args']:
                    if arg['name'] == param and arg['type']:
                        param_type = f": {arg['type']}"
                        break
                
                doc += f"- `{param}{param_type}` - {desc}\n"
            
            doc += "\n"
        
        # 添加返回詳情
        if docstring_info.returns:
            doc += f"**返回:**\n\n{docstring_info.returns}\n\n"
        
        # 添加異常
        if docstring_info.raises:
            doc += "**拋出:**\n\n"
            
            for exc, desc in docstring_info.raises.items():
                doc += f"- `{exc}` - {desc}\n"
            
            doc += "\n"
        
        # 添加示例
        if docstring_info.examples:
            doc += "**示例:**\n\n"
            doc += "```python\n"
            for example in docstring_info.examples:
                doc += f"{example}\n"
            doc += "```\n\n"
        
        return doc
    
    def _get_module_name(self, file_path: str) -> str:
        """
        從文件路徑獲取模組名稱。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            模組名稱
        """
        rel_path = os.path.relpath(file_path, self.project_path)
        module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
        return module_name
    
    def _get_python_files(self, directory: str) -> List[str]:
        """
        獲取目錄中的所有 Python 文件（遞歸）。
        
        Args:
            directory: 目錄路徑
            
        Returns:
            Python 文件路徑列表
        """
        python_files = []
        
        for root, _, files in os.walk(directory):
            # 跳過一些常見的要排除的目錄
            if any(excluded in root for excluded in ['venv', '.git', '__pycache__', 'build', 'dist']):
                continue
                
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def _generate_index(self, stats: Dict[str, Any]) -> None:
        """
        為文檔生成索引文件。
        
        Args:
            stats: 文檔生成統計信息
        """
        index_path = os.path.join(self.output_dir, 'index.md')
        
        content = "# API 文檔\n\n"
        
        # 添加統計信息
        content += "## 概覽\n\n"
        content += f"- **module:** {stats['modules_documented']}\n"
        content += f"- **class:** {stats['classes_documented']}\n"
        content += f"- **函數:** {stats['functions_documented']}\n\n"
        
        # 添加模組文檔的連結
        content += "## module\n\n"
        
        module_links = []
        for doc_file in sorted(stats['generated_files']):
            rel_path = os.path.relpath(doc_file, self.output_dir)
            module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
            module_links.append(f"- [{module_name}]({rel_path})")
        
        content += '\n'.join(module_links)
        
        # 添加有關缺失文檔字符串的部分
        if stats['missing_docstrings']:
            content += "\n\n## 缺失的文檔字符串\n\n"
            content += "以下項目缺少文檔字符串：\n\n"
            
            for item in sorted(stats['missing_docstrings']):
                content += f"- {item}\n"
        
        # 寫入索引文件
        write_file(index_path, content)

class ConsistencyChecker:
    """檢查代碼和文檔之間一致性的class。"""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.logger = logging.getLogger(__name__)
    
    def check_file(self, file_path: str) -> Dict[str, Any]:
        """
        檢查 Python 文件的一致性。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            包含一致性檢查結果的字典
        """
        results = {
            'file_path': file_path,
            'module_inconsistencies': [],
            'class_inconsistencies': {},
            'function_inconsistencies': {},
            'overall_consistency': 100.0
        }
        
        # 讀取文件
        file_content = read_file(file_path)
        if not file_content:
            return results
        
        # 解析代碼
        try:
            tree = ast.parse(file_content)
        except SyntaxError as e:
            results['module_inconsistencies'].append(f"語法錯誤: {str(e)}")
            results['overall_consistency'] = 0.0
            return results
        
        # 檢查模組文檔字符串
        module_name = self._get_module_name(file_path)
        module_docstring = ast.get_docstring(tree)
        module_docstring_info = None
        if module_docstring:
            module_docstring_info = self._parse_docstring(module_docstring)
            
            # 檢查任何明顯的模組級不一致
            self._check_module_consistency(tree, module_docstring_info, results)
        
        # 檢查class
        total_items = 0
        inconsistent_items = 0
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                results['class_inconsistencies'][class_name] = []
                
                class_docstring = ast.get_docstring(node)
                if class_docstring:
                    class_docstring_info = self._parse_docstring(class_docstring)
                    
                    # 檢查class一致性
                    inconsistencies = self._check_class_consistency(node, class_docstring_info)
                    results['class_inconsistencies'][class_name].extend(inconsistencies)
                    
                    total_items += 1
                    if inconsistencies:
                        inconsistent_items += 1
                
                # 檢查方法
                for method_node in node.body:
                    if isinstance(method_node, ast.FunctionDef):
                        method_name = f"{class_name}.{method_node.name}"
                        results['function_inconsistencies'][method_name] = []
                        
                        method_docstring = ast.get_docstring(method_node)
                        if method_docstring:
                            method_docstring_info = self._parse_docstring(method_docstring)
                            
                            # 檢查方法一致性
                            inconsistencies = self._check_function_consistency(method_node, method_docstring_info)
                            results['function_inconsistencies'][method_name].extend(inconsistencies)
                            
                            total_items += 1
                            if inconsistencies:
                                inconsistent_items += 1
        
        # 檢查函數
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                function_name = node.name
                results['function_inconsistencies'][function_name] = []
                
                function_docstring = ast.get_docstring(node)
                if function_docstring:
                    function_docstring_info = self._parse_docstring(function_docstring)
                    
                    # 檢查函數一致性
                    inconsistencies = self._check_function_consistency(node, function_docstring_info)
                    results['function_inconsistencies'][function_name].extend(inconsistencies)
                    
                    total_items += 1
                    if inconsistencies:
                        inconsistent_items += 1
        
        # 計算總體一致性
        if total_items > 0:
            consistency = ((total_items - inconsistent_items) / total_items) * 100
            results['overall_consistency'] = round(consistency, 2)
        
        return results
    
    def _check_module_consistency(self, tree: ast.AST, docstring_info: DocstringInfo, results: Dict[str, Any]) -> None:
        """
        檢查模組代碼和文檔字符串之間的一致性。
        
        Args:
            tree: AST 樹
            docstring_info: 解析的文檔字符串信息
            results: 要更新的結果字典
        """
        # 檢查提到但不存在的導入
        for line in docstring_info.description.splitlines():
            for word in re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', line):
                if len(word) > 3:  # 跳過小單詞
                    # 檢查單詞是否看起來像一個模組但未被導入
                    if word[0].isupper() and '_' not in word:
                        module_imported = False
                        for node in tree.body:
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                for name in node.names:
                                    if name.name == word or (name.asname and name.asname == word):
                                        module_imported = True
                                        break
                        
                        if not module_imported:
                            results['module_inconsistencies'].append(f"文檔字符串提到了 '{word}' 但它沒有被導入")
    
    def _check_class_consistency(self, node: ast.ClassDef, docstring_info: DocstringInfo) -> List[str]:
        """
        檢查class代碼和文檔字符串之間的一致性。
        
        Args:
            node: ClassDef 節點
            docstring_info: 解析的文檔字符串信息
            
        Returns:
            不一致列表
        """
        inconsistencies = []
        
        # 檢查繼承
        if node.bases:
            # 提取基class名稱
            base_names = [self._get_name(base) for base in node.bases]
            base_names = [re.sub(r'\..*', '', name) for name in base_names]  # 剔除模組前綴
            
            # 在文檔字符串中尋找基class
            for base_name in base_names:
                if base_name not in docstring_info.description and base_name != 'object':
                    inconsistencies.append(f"class繼承自 '{base_name}' 但在文檔字符串中沒有提到")
        
        # 檢查文檔字符串中提到的屬性與實際屬性
        actual_attributes = set()
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        actual_attributes.add(target.id)
                    elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                        actual_attributes.add(target.attr)
        
        # 檢查文檔字符串中提到的方法與實際方法
        actual_methods = set()
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                actual_methods.add(item.name)
        
        # 尋找提到但不存在的屬性或方法
        for line in docstring_info.description.splitlines():
            for word in re.findall(r'`([A-Za-z_][A-Za-z0-9_]*)`', line):
                if word not in actual_attributes and word not in actual_methods:
                    inconsistencies.append(f"文檔字符串提到了 '{word}' 但它不是class的屬性或方法")
        
        return inconsistencies
    
    def _check_function_consistency(self, node: ast.FunctionDef, docstring_info: DocstringInfo) -> List[str]:
        """
        檢查函數代碼和文檔字符串之間的一致性。
        
        Args:
            node: FunctionDef 節點
            docstring_info: 解析的文檔字符串信息
            
        Returns:
            不一致列表
        """
        inconsistencies = []
        
        # 獲取函數參數
        arg_names = [arg.arg for arg in node.args.args if arg.arg != 'self']
        
        # 檢查文檔記錄的參數是否不在函數簽名中
        for param_name in docstring_info.params:
            if param_name not in arg_names:
                inconsistencies.append(f"參數 '{param_name}' 已記錄在文檔中但不在函數簽名中")
        
        # 檢查函數參數是否未在文檔中記錄
        for arg_name in arg_names:
            if arg_name not in docstring_info.params:
                inconsistencies.append(f"參數 '{arg_name}' 在函數簽名中但未在文檔中記錄")
        
        # 檢查函數是否返回值但沒有返回描述
        has_return = False
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Return) and sub_node.value is not None:
                has_return = True
                break
        
        if has_return and not docstring_info.returns:
            inconsistencies.append("函數返回一個值但沒有記錄返回值")
        
        if not has_return and docstring_info.returns:
            inconsistencies.append("函數有返回值文檔但不返回值")
        
        # 檢查函數是否拋出異常但未在文檔中記錄
        documented_exceptions = set(docstring_info.raises.keys())
        raised_exceptions = set()
        
        for sub_node in ast.walk(node):
            if isinstance(sub_node, ast.Raise):
                if isinstance(sub_node.exc, ast.Name):
                    raised_exceptions.add(sub_node.exc.id)
                elif isinstance(sub_node.exc, ast.Call) and isinstance(sub_node.exc.func, ast.Name):
                    raised_exceptions.add(sub_node.exc.func.id)
        
        for exc in raised_exceptions:
            if exc not in documented_exceptions:
                inconsistencies.append(f"函數拋出 '{exc}' 但未在文檔中記錄")
        
        for exc in documented_exceptions:
            if exc not in raised_exceptions:
                inconsistencies.append(f"異常 '{exc}' 已在文檔中記錄但函數不拋出")
        
        return inconsistencies
    
    def _parse_docstring(self, docstring: str) -> DocstringInfo:
        """
        解析文檔字符串以提取組件。
        
        Args:
            docstring: 要解析的文檔字符串
            
        Returns:
            帶有解析組件的 DocstringInfo 對象
        """
        if not docstring:
            return DocstringInfo()
        
        info = DocstringInfo()
        
        # 將文檔字符串分割為行
        lines = docstring.splitlines()
        
        # 提取摘要（第一行）
        if lines and lines[0].strip():
            info.summary = lines[0].strip()
        
        # 提取描述
        description_lines = []
        section = 'description'
        
        for i, line in enumerate(lines[1:], 1):
            line = line.strip()
            
            if not line:
                continue
            
            # 檢查部分標題
            if line.lower().startswith(('args:', 'arguments:', 'parameters:')):
                section = 'params'
                continue
            elif line.lower().startswith('returns:'):
                section = 'returns'
                continue
            elif line.lower().startswith(('raises:', 'exceptions:', 'throws:')):
                section = 'raises'
                continue
            elif line.lower().startswith('examples:'):
                section = 'examples'
                continue
            elif line.lower().startswith('todo:'):
                section = 'todo'
                continue
            
            # 基於當前部分處理
            if section == 'description':
                description_lines.append(line)
            elif section == 'params':
                param_match = re.match(r'(\w+)(?:\s+\(([^)]+)\))?\s*:\s*(.*)', line)
                if param_match:
                    param_name = param_match.group(1)
                    param_desc = param_match.group(3)
                    info.params[param_name] = param_desc
            elif section == 'returns':
                info.returns += line + " "
            elif section == 'raises':
                exception_match = re.match(r'(\w+)(?:\s+\(([^)]+)\))?\s*:\s*(.*)', line)
                if exception_match:
                    exception_name = exception_match.group(1)
                    exception_desc = exception_match.group(3)
                    info.raises[exception_name] = exception_desc
            elif section == 'examples':
                info.examples.append(line)
            elif section == 'todo':
                info.todo.append(line)
        
        info.description = '\n'.join(description_lines).strip()
        info.returns = info.returns.strip()
        
        return info
    
    def _get_name(self, node: ast.AST) -> str:
        """
        從 AST 節點獲取可讀名稱。
        
        Args:
            node: AST 節點
            
        Returns:
            節點的字符串表示
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return ast.unparse(node)
    
    def _get_module_name(self, file_path: str) -> str:
        """
        從文件路徑獲取模組名稱。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            模組名稱
        """
        rel_path = os.path.relpath(file_path, self.project_path)
        module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, '.')
        return module_name