"""
框架分析器套件 - 為特定 Web 框架提供專門的分析功能。
支援 Django、Flask 和 FastAPI 框架。
"""

from typing import Dict, List, Optional, Any

# 導出主要類
from .django_analyzer import DjangoAnalyzer
from .flask_analyzer import FlaskAnalyzer
from .fastapi_analyzer import FastAPIAnalyzer
from .framework_migration import FrameworkMigrationHelper