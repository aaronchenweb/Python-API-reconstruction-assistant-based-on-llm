"""
用於管理代碼變更和重構的模塊。
提供應用和跟踪代碼變更的功能。
"""
import difflib
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import git

from utils.file_operations import read_file, write_file


class CodeChange:
    """表示代碼變更的類。"""
    
    def __init__(self, 
                 file_path: str, 
                 original_content: str, 
                 new_content: str, 
                 description: str = "", 
                 change_type: str = "refactoring"):
        self.file_path = file_path
        self.original_content = original_content
        self.new_content = new_content
        self.description = description
        self.change_type = change_type  # "refactoring", "pattern_implementation" 等
        self.timestamp = datetime.now().isoformat()
        self.diff = self._generate_diff()
    
    def _generate_diff(self) -> str:
        """生成變更的統一差異格式。"""
        diff = difflib.unified_diff(
            self.original_content.splitlines(keepends=True),
            self.new_content.splitlines(keepends=True),
            fromfile=f"a/{os.path.basename(self.file_path)}",
            tofile=f"b/{os.path.basename(self.file_path)}",
            n=3
        )
        return ''.join(diff)
    
    def to_dict(self) -> Dict:
        """將變更轉換為字典。"""
        return {
            "file_path": self.file_path,
            "description": self.description,
            "change_type": self.change_type,
            "timestamp": self.timestamp,
            "diff": self.diff
        }


class CodeChangeManager:
    """用於跟踪和應用代碼變更的管理器。"""
    
    def __init__(self, project_root: str, backup_dir: str = ".refactoring_backups"):
        self.project_root = project_root
        self.backup_dir = os.path.join(project_root, backup_dir)
        self.changes: List[CodeChange] = []
        
        # 如果備份目錄不存在則創建
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 檢查項目是否為 git 倉庫
        self.is_git_repo = self._is_git_repo()
        if self.is_git_repo:
            self.repo = git.Repo(project_root)
    
    def _is_git_repo(self) -> bool:
        """檢查項目是否為 git 倉庫。"""
        try:
            git.Repo(self.project_root)
            return True
        except git.InvalidGitRepositoryError:
            return False
    
    def _create_backup(self, file_path: str) -> str:
        """
        創建文件的備份。
        
        Args:
            file_path: 要備份的文件路徑
            
        Returns:
            備份文件的路徑
        """
        if not os.path.exists(file_path):
            return ""
        
        # 創建基於時間戳的備份目錄
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = os.path.join(self.backup_dir, timestamp)
        os.makedirs(backup_subdir, exist_ok=True)
        
        # 複製文件到備份目錄
        rel_path = os.path.relpath(file_path, self.project_root)
        backup_path = os.path.join(backup_subdir, rel_path)
        
        # 如果父目錄不存在則創建
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def apply_change(self, change: CodeChange) -> bool:
        """
        應用代碼變更。
        
        Args:
            change: 要應用的 CodeChange 對象
            
        Returns:
            如果成功應用則返回 True，否則返回 False
        """
        if not os.path.exists(change.file_path):
            return False
        
        # 在應用變更前創建備份
        backup_path = self._create_backup(change.file_path)
        if not backup_path:
            return False
        
        # 應用變更
        if write_file(change.file_path, change.new_content):
            self.changes.append(change)
            return True
        else:
            return False
    
    def get_changes(self) -> List[CodeChange]:
        """
        獲取所有變更。
        
        Returns:
            CodeChange 對象列表
        """
        return self.changes
    
    def commit_changes_to_git(self, message: str) -> bool:
        """
        將變更提交到 git 倉庫。
        
        Args:
            message: 提交信息
            
        Returns:
            如果成功提交則返回 True，否則返回 False
        """
        if not self.is_git_repo:
            return False
        
        try:
            # 獲取已更改文件的列表
            changed_files = list(set(change.file_path for change in self.changes))
            
            # 將文件添加到 git
            for file_path in changed_files:
                rel_path = os.path.relpath(file_path, self.project_root)
                self.repo.git.add(rel_path)
            
            # 提交變更
            self.repo.git.commit('-m', message)
            return True
        except git.GitCommandError:
            return False
    
    def create_branch_for_changes(self, branch_name: str) -> bool:
        """
        為變更創建新的 git 分支。
        
        Args:
            branch_name: 分支名稱
            
        Returns:
            如果成功創建分支則返回 True，否則返回 False
        """
        if not self.is_git_repo:
            return False
        
        try:
            # 檢查分支是否已存在
            existing_branches = [str(branch) for branch in self.repo.branches]
            if branch_name in existing_branches:
                return False
            
            # 創建新分支
            self.repo.git.checkout('-b', branch_name)
            return True
        except git.GitCommandError:
            return False
    
    def restore_backup(self, backup_dir: str) -> bool:
        """
        從備份目錄恢復文件。
        
        Args:
            backup_dir: 備份目錄的路徑
            
        Returns:
            如果成功恢復則返回 True，否則返回 False
        """
        if not os.path.exists(backup_dir):
            return False
        
        try:
            # 遍歷備份目錄
            for root, _, files in os.walk(backup_dir):
                for file in files:
                    # 獲取相對路徑
                    backup_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(backup_file_path, backup_dir)
                    
                    # 獲取原始文件路徑
                    original_file_path = os.path.join(self.project_root, rel_path)
                    
                    # 如果父目錄不存在則創建
                    os.makedirs(os.path.dirname(original_file_path), exist_ok=True)
                    
                    # 從備份複製文件到原始位置
                    shutil.copy2(backup_file_path, original_file_path)
            
            return True
        except Exception:
            return False
    
    def list_backups(self) -> List[Tuple[str, str]]:
        """
        列出所有備份。
        
        Returns:
            包含元組 (備份目錄, 時間戳) 的列表
        """
        if not os.path.exists(self.backup_dir):
            return []
        
        backups = []
        for item in os.listdir(self.backup_dir):
            backup_path = os.path.join(self.backup_dir, item)
            if os.path.isdir(backup_path):
                try:
                    # 從目錄名稱解析時間戳
                    timestamp = datetime.strptime(item, "%Y%m%d_%H%M%S")
                    backups.append((backup_path, timestamp.isoformat()))
                except ValueError:
                    # 如果目錄名稱不是時間戳，則使用目錄名稱
                    backups.append((backup_path, item))
        
        return sorted(backups, key=lambda x: x[1], reverse=True)