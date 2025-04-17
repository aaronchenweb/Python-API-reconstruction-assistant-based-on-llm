"""
用於文件操作的實用函數。
"""
import logging
import os
from typing import List, Optional


def read_file(file_path: str) -> Optional[str]:
    """
    讀取文件內容。
    
    Args:
        file_path: 文件路徑
        
    Returns:
        文件內容的字符串，如果文件不存在則返回 None
    
    Raises:
        FileNotFoundError: 文件不存在
        IOError: 讀取文件錯誤
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def write_file(file_path: str, content: str) -> bool:
    """
    將內容寫入文件。
    
    Args:
        file_path: 文件路徑
        content: 要寫入的內容
        
    Returns:
        如果成功寫入則返回 True，否則返回 False
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Check that we're not writing an empty file
        if not content or len(content) < 10:
            logging.error(f"Attempted to write very short content ({len(content)} chars) to {file_path}")
            return False
            
        # Write file with explicit encoding
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            # Force flush to ensure all content is written
            f.flush()
            os.fsync(f.fileno())
            
        # Verify content was written correctly
        if os.path.exists(file_path):
            written_size = os.path.getsize(file_path)
            expected_size = len(content.encode('utf-8'))
            if written_size < expected_size * 0.9:
                logging.warning(f"File size mismatch: expected ~{expected_size}, got {written_size}")
                
        return True
    except Exception as e:
        print(f"寫入文件時出錯: {e}")
        return False


def get_python_files(directory_path: str) -> List[str]:
    """
    獲取目錄中的 Python 文件列表（遞歸）。
    
    Args:
        directory_path: 要搜索的目錄路徑
        
    Returns:
        Python 文件路徑的列表
    """
    python_files = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def backup_file(file_path: str, backup_dir: str = ".backup") -> Optional[str]:
    """
    創建文件的備份。
    
    Args:
        file_path: 要備份的文件路徑
        backup_dir: 儲存備份的目錄
        
    Returns:
        備份文件的路徑，如果備份失敗則返回 None
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        # 如果目錄不存在則創建備份目錄
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # 從路徑獲取文件名
        filename = os.path.basename(file_path)
        
        # 獲取備份文件路徑
        backup_path = os.path.join(backup_dir, filename)
        
        # 如果文件已存在則添加後綴
        counter = 1
        while os.path.exists(backup_path):
            backup_path = os.path.join(backup_dir, f"{filename}.{counter}")
            counter += 1
        
        # 複製文件
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        return backup_path
    
    except Exception as e:
        print(f"創建備份時出錯: {e}")
        return None


def restore_file(backup_path: str, target_path: str) -> bool:
    """
    從備份恢復文件。
    
    Args:
        backup_path: 備份文件的路徑
        target_path: 恢復的目標路徑
        
    Returns:
        如果成功恢復則返回 True，否則返回 False
    """
    try:
        if not os.path.exists(backup_path):
            return False
        
        with open(backup_path, 'r', encoding='utf-8') as src:
            with open(target_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        return True
    
    except Exception as e:
        print(f"恢復文件時出錯: {e}")
        return False