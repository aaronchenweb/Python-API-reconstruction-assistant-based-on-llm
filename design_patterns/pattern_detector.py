"""
用於識別 Python 程式碼中的設計模式的模組。
使用 AST 分析和啟發式方法來檢測常見模式。
"""
import ast
import os
from typing import Dict, List, Optional, Set, Tuple

import astroid
from astroid import nodes

from code_analyzer.ast_parser import analyze_python_file
from utils.file_operations import read_file

def get_python_files(directory_path):
    """
    取得目錄中的所有 Python 檔案（遞歸）。
    
    Args:
        directory_path: 目錄的路徑
        
    Returns:
        Python 檔案的路徑列表
    """
    import os
    python_files = []
    
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
                
    return python_files


class PatternDetector:
    """檢測 Python 程式碼中的常見設計模式。"""

    def __init__(self):
        self.patterns_found = {}

    def detect_patterns(self, file_path: str) -> Dict[str, List[Tuple[str, int]]]:
        """
        分析 Python 檔案以識別設計模式。
        
        Args:
            file_path: Python 檔案的路徑
            
        Returns:
            以模式名稱為鍵，(元素名稱, 行號) 元組列表為值的字典
        """
        patterns = {
            "singleton": [],
            "factory_method": [],
            "observer": [],
            "strategy": [],
            "decorator": [],
            "adapter": [],
        }
        
        # 使用 ast 和 astroid 分析檔案，以應用不同的分析技術
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # 標準 AST 解析
        try:
            tree = ast.parse(content)
            # 使用 astroid 進行更詳細的分析
            astroid_tree = astroid.parse(content)
            
            # 檢測模式
            patterns["singleton"].extend(self._detect_singleton(tree, astroid_tree))
            patterns["factory_method"].extend(self._detect_factory_method(tree, astroid_tree))
            patterns["observer"].extend(self._detect_observer(tree, astroid_tree))
            patterns["strategy"].extend(self._detect_strategy(tree, astroid_tree))
            patterns["decorator"].extend(self._detect_decorator(tree, astroid_tree))
            patterns["adapter"].extend(self._detect_adapter(tree, astroid_tree))
            
            # 移除空模式
            patterns = {k: v for k, v in patterns.items() if v}
            
        except SyntaxError:
            return {}
            
        return patterns
        
    def detect_patterns_in_directory(self, directory_path: str) -> Dict[str, Dict[str, List[Tuple[str, int]]]]:
        """
        分析目錄中的所有 Python 檔案以識別設計模式。
        
        Args:
            directory_path: 包含 Python 檔案的目錄路徑
            
        Returns:
            以檔案路徑為鍵，模式字典為值的字典
        """
        result = {}
        python_files = get_python_files(directory_path)
        
        for file_path in python_files:
            patterns = self.detect_patterns(file_path)
            if patterns:
                result[file_path] = patterns
                
        return result
    
    def _detect_singleton(self, tree: ast.Module, astroid_tree: nodes.Module) -> List[Tuple[str, int]]:
        """
        檢測單例模式實現。
        
        一個類如果符合以下條件，可能是單例模式：
        - 具有私有實例變數（通常為 _instance）
        - 有一個返回此實例的靜態方法（通常為 __new__ 或 getInstance）
        - 該實例僅在不存在時才被創建
        """
        singletons = []
        
        # 檢查類
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 檢查類變數，名稱如 _instance, __instance
                has_instance_var = False
                has_getInstance_method = False
                
                for item in node.body:
                    # 尋找實例變數
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and (
                                target.id.startswith('_instance') or 
                                target.id.startswith('__instance')
                            ):
                                has_instance_var = True
                    
                    # 尋找 __new__ 方法或 getInstance 方法
                    if isinstance(item, ast.FunctionDef) and (
                        item.name == '__new__' or 
                        'get_instance' in item.name.lower() or
                        'getinstance' in item.name.lower()
                    ):
                        has_getInstance_method = True
                
                if has_instance_var and has_getInstance_method:
                    singletons.append((node.name, node.lineno))
        
        return singletons
    
    def _detect_factory_method(self, tree: ast.Module, astroid_tree: nodes.Module) -> List[Tuple[str, int]]:
        """
        檢測工廠方法模式實現。
        
        如果一個類符合以下條件，可能使用了工廠方法模式：
        - 具有返回不同類實例的方法
        - 這些方法名稱中通常含有 'create'、'get'、'build' 等
        """
        factories = []
        
        # 檢查類是否使用工廠方法模式
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                factory_methods = []
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        # 檢查方法名稱是否包含工廠相關術語
                        if any(term in item.name.lower() for term in ['create', 'build', 'make', 'generate', 'factory']):
                            # 尋找創建對象的返回語句
                            returns_new_instance = False
                            
                            for subnode in ast.walk(item):
                                if isinstance(subnode, ast.Return) and isinstance(subnode.value, ast.Call):
                                    returns_new_instance = True
                                    break
                            
                            if returns_new_instance:
                                factory_methods.append(item.name)
                
                if factory_methods:
                    factories.append((node.name, node.lineno))
        
        return factories
    
    def _detect_observer(self, tree: ast.Module, astroid_tree: nodes.Module) -> List[Tuple[str, int]]:
        """
        檢測觀察者模式實現。
        
        如果一個類符合以下條件，可能使用了觀察者模式：
        - 具有如 add_observer、remove_observer、notify 等方法
        - 維護一個觀察者集合
        """
        observers = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                observer_methods = set()
                has_observers_collection = False
                
                # 檢查與觀察者相關的方法名稱
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = item.name.lower()
                        if any(term in method_name for term in ['add_observer', 'remove_observer', 'notify', 'subscribe', 'unsubscribe']):
                            observer_methods.add(method_name)
                
                # 檢查觀察者集合（列表、集合等）
                for item in astroid_tree.body:
                    if isinstance(item, nodes.ClassDef) and item.name == node.name:
                        for attr in item.instance_attrs:
                            if any(term in attr.lower() for term in ['observer', 'listener', 'subscriber']):
                                has_observers_collection = True
                
                if len(observer_methods) >= 2 or has_observers_collection:
                    observers.append((node.name, node.lineno))
        
        return observers
    
    def _detect_strategy(self, tree: ast.Module, astroid_tree: nodes.Module) -> List[Tuple[str, int]]:
        """
        檢測策略模式實現。
        
        策略模式的指標：
        - 在 __init__ 中接收策略對象的類
        - 實現共同介面/方法的多個類
        """
        strategies = []
        
        # 首先獲取可能是策略的所有類（具有相同的方法名稱）
        potential_strategies = {}
        
        # 識別具有相似介面方法的類
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = set()
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith('__'):
                        methods.add(item.name)
                
                # 按方法簽名分組
                method_signature = frozenset(methods)
                if method_signature and len(method_signature) > 0:
                    if method_signature not in potential_strategies:
                        potential_strategies[method_signature] = []
                    potential_strategies[method_signature].append(node.name)
        
        # 尋找可能使用這些策略的類
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 檢查 __init__ 是否接收可能是策略的參數
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        # 尋找將參數賦值給 self 屬性的情況
                        has_strategy_param = False
                        for param in item.args.args[1:]:  # 跳過 self
                            param_name = param.arg
                            # 檢查是否有類似 self.strategy = strategy 的賦值
                            for subnode in ast.walk(item):
                                if (isinstance(subnode, ast.Assign) and 
                                    isinstance(subnode.targets[0], ast.Attribute) and
                                    isinstance(subnode.targets[0].value, ast.Name) and
                                    subnode.targets[0].value.id == 'self' and
                                    isinstance(subnode.value, ast.Name) and
                                    subnode.value.id == param_name):
                                    has_strategy_param = True
                                    strategies.append((node.name, node.lineno))
                                    break
                        
                        if has_strategy_param:
                            break
        
        return strategies
    
    def _detect_decorator(self, tree: ast.Module, astroid_tree: nodes.Module) -> List[Tuple[str, int]]:
        """
        檢測裝飾器模式實現。
        
        裝飾器模式的指標：
        - 在 __init__ 中接收相同介面的對象的類
        - 在被包裝對象上調用相同方法的方法
        """
        decorators = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                has_component = False
                wraps_methods = False
                
                # 檢查 __init__ 是否接收組件參數
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        if len(item.args.args) > 1:  # 除 self 外還有其他參數
                            # 尋找類似 self.component = component 的賦值
                            for subnode in ast.walk(item):
                                if (isinstance(subnode, ast.Assign) and
                                    isinstance(subnode.targets[0], ast.Attribute) and
                                    isinstance(subnode.targets[0].value, ast.Name) and
                                    subnode.targets[0].value.id == 'self'):
                                    has_component = True
                                    break
                    
                    # 檢查方法是否在組件上調用相同方法
                    elif isinstance(item, ast.FunctionDef) and not item.name.startswith('__'):
                        for subnode in ast.walk(item):
                            if (isinstance(subnode, ast.Call) and
                                isinstance(subnode.func, ast.Attribute) and
                                isinstance(subnode.func.value, ast.Attribute) and
                                isinstance(subnode.func.value.value, ast.Name) and
                                subnode.func.value.value.id == 'self' and
                                subnode.func.attr == item.name):
                                wraps_methods = True
                                break
                
                if has_component and wraps_methods:
                    decorators.append((node.name, node.lineno))
        
        return decorators
    
    def _detect_adapter(self, tree: ast.Module, astroid_tree: nodes.Module) -> List[Tuple[str, int]]:
        """
        檢測轉接器模式實現。
        
        轉接器模式的指標：
        - 包裝具有不同介面的另一個類的類
        - 將調用轉換為被適配者上不同方法的方法
        """
        adapters = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                has_adaptee = False
                
                # 檢查類是否有可能是被適配者的實例變數
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                        for subnode in ast.walk(item):
                            if (isinstance(subnode, ast.Assign) and
                                isinstance(subnode.targets[0], ast.Attribute) and
                                isinstance(subnode.targets[0].value, ast.Name) and
                                subnode.targets[0].value.id == 'self'):
                                has_adaptee = True
                
                # 檢查方法是否在被適配者上調用方法
                calls_adaptee = False
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith('__'):
                        for subnode in ast.walk(item):
                            if (isinstance(subnode, ast.Call) and
                                isinstance(subnode.func, ast.Attribute) and
                                isinstance(subnode.func.value, ast.Attribute) and
                                isinstance(subnode.func.value.value, ast.Name) and
                                subnode.func.value.value.id == 'self'):
                                calls_adaptee = True
                                break
                
                if has_adaptee and calls_adaptee:
                    adapters.append((node.name, node.lineno))
        
        return adapters