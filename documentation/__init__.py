"""
Python 重構助理的文檔產生套件。
提供產生API文件和檢查一致性的功能。
"""

# 首先導入相容層以確保 ast.unparse 可用
from documentation.ast_compat import ast_unparse
from documentation.doc_generator import DocGenerator, ConsistencyChecker, DocstringInfo