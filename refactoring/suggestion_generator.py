"""
用於生成和管理重構建議的模塊。
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from code_analyzer import code_metrics
from design_patterns.pattern_detector import PatternDetector
from design_patterns.patterns_registry import PatternsRegistry
from utils.file_operations import read_file, write_file


class RefactoringSuggestion:
    """表示重構建議的Class。"""
    
    def __init__(self, 
                 suggestion_id: int,
                 suggestion_type: str,
                 description: str,
                 location: Dict,
                 recommendation: str,
                 severity: str = "medium",
                 code_example: Optional[str] = None):
        self.id = suggestion_id
        self.type = suggestion_type
        self.description = description
        self.location = location  # 包含 file_path、start_line、end_line 的字典
        self.recommendation = recommendation
        self.severity = severity  # "low", "medium", "high"
        self.code_example = code_example
        self.created_at = datetime.now().isoformat()
        self.applied = False
        self.applied_at = None
    
    def to_dict(self) -> Dict:
        """將建議轉換為字典。"""
        return {
            "id": self.id,
            "type": self.type,
            "description": self.description,
            "location": self.location,
            "recommendation": self.recommendation,
            "severity": self.severity,
            "code_example": self.code_example,
            "created_at": self.created_at,
            "applied": self.applied,
            "applied_at": self.applied_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RefactoringSuggestion':
        """從字典創建建議。"""
        suggestion = cls(
            suggestion_id=data["id"],
            suggestion_type=data["type"],
            description=data["description"],
            location=data["location"],
            recommendation=data["recommendation"],
            severity=data.get("severity", "medium"),
            code_example=data.get("code_example")
        )
        suggestion.created_at = data.get("created_at", suggestion.created_at)
        suggestion.applied = data.get("applied", False)
        suggestion.applied_at = data.get("applied_at")
        return suggestion
    
    def mark_as_applied(self):
        """將建議標記為已應用。"""
        self.applied = True
        self.applied_at = datetime.now().isoformat()


class SuggestionStore:
    """用於管理重構建議的儲存器。"""
    
    def __init__(self, store_path: str):
        self.store_path = store_path
        self.suggestions: Dict[int, RefactoringSuggestion] = {}
        self._next_id = 1
        self._load_suggestions()
    
    def _load_suggestions(self):
        """從儲存中加載建議。"""
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                    for suggestion_data in data:
                        suggestion = RefactoringSuggestion.from_dict(suggestion_data)
                        self.suggestions[suggestion.id] = suggestion
                        if suggestion.id >= self._next_id:
                            self._next_id = suggestion.id + 1
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_suggestions(self):
        """將建議保存到儲存中。"""
        data = [suggestion.to_dict() for suggestion in self.suggestions.values()]
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        with open(self.store_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_suggestion(self, suggestion: RefactoringSuggestion) -> int:
        """
        向儲存中添加建議。
        
        Args:
            suggestion: 要添加的建議
            
        Returns:
            添加的建議的 ID
        """
        suggestion.id = self._next_id
        self.suggestions[suggestion.id] = suggestion
        self._next_id += 1
        self._save_suggestions()
        return suggestion.id
    
    def get_suggestion(self, suggestion_id: int) -> Optional[RefactoringSuggestion]:
        """
        通過 ID 獲取建議。
        
        Args:
            suggestion_id: 建議的 ID
            
        Returns:
            建議對象，如果未找到則返回 None
        """
        return self.suggestions.get(suggestion_id)
    
    def get_all_suggestions(self) -> List[RefactoringSuggestion]:
        """
        獲取所有建議。
        
        Returns:
            所有建議的列表
        """
        return list(self.suggestions.values())
    
    def get_suggestions_for_file(self, file_path: str) -> List[RefactoringSuggestion]:
        """
        獲取特定文件的所有建議。
        
        Args:
            file_path: 文件路徑
            
        Returns:
            該文件的建議列表
        """
        return [
            suggestion for suggestion in self.suggestions.values()
            if suggestion.location.get("file_path") == file_path
        ]
    
    def get_pending_suggestions(self) -> List[RefactoringSuggestion]:
        """
        獲取所有待處理（未應用）的建議。
        
        Returns:
            待處理建議的列表
        """
        return [
            suggestion for suggestion in self.suggestions.values()
            if not suggestion.applied
        ]
    
    def mark_suggestion_applied(self, suggestion_id: int) -> bool:
        """
        將建議標記為已應用。
        
        Args:
            suggestion_id: 建議的 ID
            
        Returns:
            如果建議被標記則返回 True，否則返回 False
        """
        suggestion = self.get_suggestion(suggestion_id)
        if suggestion:
            suggestion.mark_as_applied()
            self._save_suggestions()
            return True
        return False
    
    def remove_suggestion(self, suggestion_id: int) -> bool:
        """
        從儲存中移除建議。
        
        Args:
            suggestion_id: 建議的 ID
            
        Returns:
            如果建議被移除則返回 True，否則返回 False
        """
        if suggestion_id in self.suggestions:
            del self.suggestions[suggestion_id]
            self._save_suggestions()
            return True
        return False


class SuggestionGenerator:
    """基於代碼分析生成重構建議的生成器。"""
    
    def __init__(self, store_path: str = "suggestions.json"):
        self.suggestion_store = SuggestionStore(store_path)
        self.pattern_detector = PatternDetector()
        self.patterns_registry = PatternsRegistry()
    
    def generate_suggestions_for_file(self, file_path: str) -> List[int]:
        """
        為文件生成重構建議。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            生成的建議 ID 列表
        """
        suggestion_ids = []
        
        # 生成質量指標建議
        quality_suggestions = self._generate_quality_suggestions(file_path)
        for suggestion in quality_suggestions:
            suggestion_id = self.suggestion_store.add_suggestion(suggestion)
            suggestion_ids.append(suggestion_id)
        
        # 生成設計模式建議
        pattern_suggestions = self._generate_pattern_suggestions(file_path)
        for suggestion in pattern_suggestions:
            suggestion_id = self.suggestion_store.add_suggestion(suggestion)
            suggestion_ids.append(suggestion_id)
        
        return suggestion_ids
    
    def _generate_quality_suggestions(self, file_path: str) -> List[RefactoringSuggestion]:
        """
        基於代碼質量指標生成建議，使用更合理的閾值。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            重構建議列表
        """
        suggestions = []
        
        try:
            # 獲取代碼指標
            metrics = code_metrics.calculate_metrics(file_path)
            
            # 檢查高複雜度 - 使用更高的閾值
            complexity = metrics.get('cyclomatic_complexity', metrics.get('total_complexity', 0))
            if complexity > 20:  
                # 安全獲取第一個複雜函數
                complex_functions = metrics.get('function_complexities', metrics.get('complex_functions', []))
                start_line = 1
                if complex_functions and len(complex_functions) > 0:
                    # 找出最複雜的函數
                    most_complex = max(complex_functions, key=lambda f: f.get('complexity', 0), default=None)
                    if most_complex:
                        # 處理不同的字段名
                        if 'line' in most_complex:
                            start_line = most_complex.get('line', 1)
                        elif 'lineno' in most_complex:
                            start_line = most_complex.get('lineno', 1)
                    
                    # 只有當存在高複雜度函數時才添加建議
                    if most_complex and most_complex.get('complexity', 0) > 10:
                        suggestion = RefactoringSuggestion(
                            suggestion_id=0,  # 將由儲存設置
                            suggestion_type="complexity",
                            description="檢測到高循環複雜度",
                            location={
                                "file_path": file_path,
                                "start_line": start_line,
                                "end_line": -1  # 未知結束行
                            },
                            recommendation="考慮將複雜函數分解為更小、更易於管理的部分。",
                            severity="high" if most_complex.get('complexity', 0) > 15 else "medium"
                        )
                        suggestions.append(suggestion)
            
            # 檢查低可維護性指數 - 使用更低的閾值
            maintainability = metrics.get('maintainability_index', metrics.get('maintainability', 0))
            if maintainability < 40:  
                suggestion = RefactoringSuggestion(
                    suggestion_id=0,  # 將由儲存設置
                    suggestion_type="maintainability",
                    description="可維護性指數低",
                    location={
                        "file_path": file_path,
                        "start_line": 1,
                        "end_line": -1  # 適用於整個文件
                    },
                    recommendation="改進代碼結構，降低複雜度，並添加適當的文檔。",
                    severity="high" if maintainability < 30 else "medium"
                )
                suggestions.append(suggestion)
            
            # 檢查高函數數量 - 使用更高的閾值
            if metrics.get('function_count', 0) > 25: 
                suggestion = RefactoringSuggestion(
                    suggestion_id=0,  # 將由儲存設置
                    suggestion_type="organization",
                    description="單個文件中函數數量過多",
                    location={
                        "file_path": file_path,
                        "start_line": 1,
                        "end_line": -1  # 適用於整個文件
                    },
                    recommendation="考慮根據功能將文件拆分為多個模塊。",
                    severity="medium"
                )
                suggestions.append(suggestion)
            
            # 檢查高行數 - 使用更高的閾值
            if metrics.get('loc', metrics.get('total_lines', 0)) > 500:
                suggestion = RefactoringSuggestion(
                    suggestion_id=0,  # 將由儲存設置
                    suggestion_type="organization",
                    description="文件過長",
                    location={
                        "file_path": file_path,
                        "start_line": 1,
                        "end_line": -1  # 適用於整個文件
                    },
                    recommendation="考慮根據功能將文件拆分為多個模塊。",
                    severity="medium"
                )
                suggestions.append(suggestion)
            
            # 檢查低註釋比率 - 使用更低的閾值並考慮新的計算方法
            comment_ratio = metrics.get('comment_ratio', 0)
            if comment_ratio < 0.05:  
                suggestion = RefactoringSuggestion(
                    suggestion_id=0,  # 將由儲存設置
                    suggestion_type="documentation",
                    description="註釋比率低",
                    location={
                        "file_path": file_path,
                        "start_line": 1,
                        "end_line": -1  # 適用於整個文件
                    },
                    recommendation="添加更多註釋來解釋複雜邏輯並提高代碼可讀性。",
                    severity="low"
                )
                suggestions.append(suggestion)
            
        except Exception as e:
            print(f"生成質量建議時出錯: {e}")
            import traceback
            print(traceback.format_exc())
        
        return suggestions
    
    def _generate_pattern_suggestions(self, file_path: str) -> List[RefactoringSuggestion]:
        """
        基於設計模式檢測生成建議。
        
        Args:
            file_path: Python 文件的路徑
            
        Returns:
            重構建議列表
        """
        suggestions = []
        
        try:
            # 檢測設計模式
            patterns = self.pattern_detector.detect_patterns(file_path)
            
            # 為每個模式生成建議
            for pattern_name, occurrences in patterns.items():
                pattern_info = self.patterns_registry.get_pattern(pattern_name)
                
                if not pattern_info:
                    continue
                
                for class_name, line_number in occurrences:
                    # 創建建議
                    suggestion = RefactoringSuggestion(
                        suggestion_id=0,  # 將由儲存設置
                        suggestion_type=f"pattern_{pattern_name}",
                        description=f"在Class {class_name} 中檢測到 {pattern_info.name} 模式",
                        location={
                            "file_path": file_path,
                            "start_line": line_number,
                            "end_line": -1,  # 未知結束行
                            "class_name": class_name
                        },
                        recommendation=f"考慮重構: {'; '.join(pattern_info.refactoring_tips[:2])}",
                        severity="medium",
                        code_example=pattern_info.example
                    )
                    suggestions.append(suggestion)
            
        except Exception as e:
            print(f"生成模式建議時出錯: {e}")
        
        return suggestions