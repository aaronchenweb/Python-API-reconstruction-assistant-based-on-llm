"""
基於大型語言模型 Python API 重構助手
整合 Python 重構、文檔生成和性能優化工具。
"""
import ast
import datetime
import json
import os
import re
import sys
import logging
from typing import Dict, List, Optional, Tuple, Any
from venv import logger

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.markdown import Markdown

from code_analyzer.ast_parser import analyze_python_file
from code_analyzer.code_metrics import get_code_metrics, calculate_metrics
from llm_integration.llm_client import LLMClient
from llm_integration.prompt_templates import init_template_manager, get_template, get_prompt_for_analysis
from utils.file_operations import read_file, write_file
from config import load_config

from design_patterns.pattern_detector import PatternDetector
from design_patterns.patterns_registry import PatternInfo, PatternsRegistry, get_pattern_applicability, show_pattern_details, show_patterns_comparison
from refactoring.refactoring_engine import RefactoringEngine
from refactoring.suggestion_generator import RefactoringSuggestion, SuggestionGenerator
from refactoring.code_change_manager import CodeChangeManager

from performance.perf_analyzer import PerformanceAnalyzer, PerformanceOptimizer
from documentation.doc_generator import DocGenerator, ConsistencyChecker

# 初始化 Typer 應用程序和控制台
app = typer.Typer(help="Python 重構助手")
console = Console()

# 全局狀態
project_path = ""
llm_client = None
refactoring_engine = None
suggestion_generator = None
code_change_manager = None
perf_analyzer = None
doc_generator = None
config = None


@app.callback()
def main(ctx: typer.Context, 
         project: str = typer.Option(".", help="項目目錄的路徑"),
         llm_api_key: str = typer.Option(None, help="LLM 服務的 API 密鑰", envvar="LLM_API_KEY"),
         llm_provider: str = typer.Option(None, help="LLM 提供商 (openai, anthropic, 或 gemini)"),
         config_path: str = typer.Option("config.json", help="配置文件的路徑"),
         verbose: bool = typer.Option(False, "--verbose", "-v", help="顯示詳細信息")):
    """
    Python 重構助手 - 幫助識別並應用重構機會。
    """
    global project_path, llm_client, refactoring_engine, suggestion_generator, code_change_manager
    global perf_analyzer, doc_generator, config
    
    # 設置項目路徑
    project_path = os.path.abspath(project)
    if not os.path.exists(project_path):
        console.print(f"[bold red]錯誤:[/] 項目路徑 {project_path} 不存在。")
        sys.exit(1)
    
    # 加載配置
    config = load_config(config_path)
    
    # 設置日誌記錄
    log_level = getattr(logging, config.get('log_level', 'INFO'))
    logging.basicConfig(
        level=log_level if not verbose else logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 如果提供命令行參數，則覆蓋配置
    if llm_api_key:
        config['llm_api_key'] = llm_api_key
    if llm_provider:
        config['llm_provider'] = llm_provider
    
    # 初始化 LLM 客戶端
    llm_client = LLMClient(
        api_key=config['llm_api_key'], 
        model=config['llm_model'], 
        provider=config['llm_provider']
    )
    
    # 初始化提示模板
    init_template_manager(os.path.join(project_path, "prompt_templates"))
    
    # 初始化其他組件
    refactoring_engine = RefactoringEngine(llm_client, project_path)
    suggestion_generator = SuggestionGenerator(os.path.join(project_path, "suggestions.json"))
    code_change_manager = CodeChangeManager(project_path)
    
    perf_analyzer = PerformanceAnalyzer(project_path)
    perf_optimizer = PerformanceOptimizer(llm_client)
    doc_generator = DocGenerator(project_path)
    
    # 顯示歡迎信息
    console.print(Panel.fit(
        "Python 重構助手",
        title="歡迎",
        border_style="blue"
    ))

@app.command("analyze-file")
def analyze_file(
    file_path: str = typer.Argument(..., help="要分析的 Python 文件路徑"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="分析結果的輸出文件路徑"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="顯示詳細信息")
):
    """
    分析單個 Python 文件並生成報告（第 1 階段功能）。
    """
    try:
        # 讀取文件
        if verbose:
            console.print(f"正在讀取文件: {file_path}")
        
        file_content = read_file(file_path)
        
        # 分析代碼
        if verbose:
            console.print("正在分析代碼結構...")
        
        analysis_result = analyze_python_file(file_content)
        
        # 獲取代碼指標
        if verbose:
            console.print("正在計算代碼指標...")
        
        metrics = get_code_metrics(file_content)
        analysis_result.update(metrics)
        
        # 準備 LLM 提示
        if verbose:
            console.print("正在生成 LLM 提示...")
        
        prompt = get_prompt_for_analysis(file_content, analysis_result)
        
        # 調用 LLM API
        console.print("正在從 LLM 獲取分析...")
        
        llm_response = llm_client.get_completion(prompt)
        
        # 確保回應不為空
        if llm_response is None:
            llm_response = "無法獲取分析結果。請檢查 API 設置和網絡連接。"
        
        # 準備完整報告
        full_report = f"""# Python 代碼分析報告
## 原始代碼
```python
{file_content}
```
## 分析結果
{llm_response}
"""
        
        # 如果未指定輸出路徑，生成默認輸出路徑
        if output is None:
            # 獲取文件名和目錄
            file_dir = os.path.dirname(os.path.abspath(file_path))
            file_name = os.path.basename(file_path)
            base_name, _ = os.path.splitext(file_name)
            
            # 創建默認輸出路徑: 相同目錄 + 原文件名 + "-analysis.md"
            output = os.path.join(file_dir, f"{base_name}-analysis.md")
        
        # 檢查輸出目錄是否存在，不存在則創建
        output_dir = os.path.dirname(os.path.abspath(output))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 輸出結果
        write_file(output, full_report)
        console.print(f"結果已保存到: {output}")
            
    except Exception as e:
        console.print(f"[bold red]錯誤:[/] {str(e)}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())

@app.command("analyze")
def analyze_code(
    path: str = typer.Argument(..., help="要分析的 Python 文件或目錄的路徑"),
    metrics: bool = typer.Option(True, help="計算代碼指標"),
    patterns: bool = typer.Option(True, help="檢測設計模式"),
    suggestions: bool = typer.Option(True, help="生成重構建議")
):
    """
    分析 Python 代碼以識別重構機會。
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        console.print(f"[bold red]錯誤:[/] 路徑 {path} 不存在。")
        return
    
    if os.path.isfile(path) and not path.endswith('.py'):
        console.print(f"[bold red]錯誤:[/] 文件 {path} 不是 Python 文件。")
        return
    
    # 處理文件
    files_to_analyze = []
    if os.path.isfile(path):
        files_to_analyze.append(path)
    else:
        # 遍歷目錄查找 Python 文件
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    files_to_analyze.append(os.path.join(root, file))
    
    if not files_to_analyze:
        console.print("[yellow]警告:[/] 未找到要分析的 Python 文件。")
        return
    
    console.print(f"正在分析 {len(files_to_analyze)} 個 Python 文件...")
    
    # 分析每個文件
    for file_path in files_to_analyze:
        console.print(f"\n[bold blue]正在分析:[/] {file_path}")
        
        # 計算指標
        if metrics:
            console.print("\n[bold]代碼指標:[/]")
            try:
                file_metrics = calculate_metrics(file_path)
                metrics_table = Table(title=f"{os.path.basename(file_path)} 的指標")
                metrics_table.add_column("指標", style="cyan")
                metrics_table.add_column("值", style="green")
                
                for metric, value in file_metrics.items():
                    if metric != 'function_complexities' and metric != 'error':
                        metrics_table.add_row(metric, str(value))
                
                console.print(metrics_table)
                
                # 顯示複雜函數（如果有）
                if 'function_complexities' in file_metrics and file_metrics['function_complexities']:
                    complex_table = Table(title="複雜函數")
                    complex_table.add_column("Function", style="cyan")
                    complex_table.add_column("Line", style="green")
                    complex_table.add_column("複雜度", style="yellow")
                    
                    for func in file_metrics['function_complexities']:
                        complex_table.add_row(func['name'], str(func['line']), str(func['complexity']))
                    
                    console.print(complex_table)
            except Exception as e:
                console.print(f"[red]計算指標時出錯:[/] {e}")
        
        # 檢測設計模式
        if patterns:
            console.print("\n[bold]設計模式:[/]")
            try:
                pattern_detector = PatternDetector()
                detected_patterns = pattern_detector.detect_patterns(file_path)
                
                if detected_patterns:
                    patterns_table = Table(title="檢測到的模式")
                    patterns_table.add_column("Pattern", style="cyan")
                    patterns_table.add_column("Class", style="green")
                    patterns_table.add_column("Line", style="yellow")
                    
                    for pattern_name, occurrences in detected_patterns.items():
                        for class_name, line_number in occurrences:
                            patterns_table.add_row(pattern_name.capitalize(), class_name, str(line_number))
                    
                    console.print(patterns_table)
                else:
                    console.print("[yellow]未檢測到設計模式。[/]")
            except Exception as e:
                console.print(f"[red]檢測模式時出錯:[/] {e}")
        
        # 生成重構建議
        if suggestions:
            console.print("\n[bold]重構建議:[/]")
            try:
                suggestion_ids = suggestion_generator.generate_suggestions_for_file(file_path)
                
                if suggestion_ids:
                    suggestions_table = Table(title="重構建議")
                    suggestions_table.add_column("ID", style="cyan")
                    suggestions_table.add_column("Type", style="green")
                    suggestions_table.add_column("Description", style="yellow")
                    suggestions_table.add_column("Location", style="blue")
                    
                    for suggestion_id in suggestion_ids:
                        suggestion = suggestion_generator.suggestion_store.get_suggestion(suggestion_id)
                        if suggestion:
                            location = f"行 {suggestion.location.get('start_line', 'N/A')}"
                            if suggestion.location.get('end_line', -1) > 0:
                                location += f"-{suggestion.location.get('end_line')}"
                            
                            suggestions_table.add_row(
                                str(suggestion.id),
                                suggestion.type,
                                suggestion.description,
                                location
                            )
                    
                    console.print(suggestions_table)
                else:
                    console.print("[yellow]未生成重構建議。[/]")
            except Exception as e:
                console.print(f"[red]生成建議時出錯:[/] {e}")

@app.command("patterns")
def list_design_patterns(
    detail: bool = typer.Option(False, "--detail", "-d", help="顯示模式的詳細資訊"),
    compare: bool = typer.Option(False, "--compare", "-c", help="比較不同模式的適用場景"),
    pattern_name: str = typer.Option(None, "--pattern", "-p", help="指定要詳細查看的模式名稱")
):
    """
    列出助手支持的所有設計模式，並提供何時應用每種模式的指南。
    """
    patterns_registry = PatternsRegistry()
    all_patterns = patterns_registry.get_all_patterns()
    
    if not all_patterns:
        console.print("[yellow]未註冊任何設計模式。[/]")
        return
    
    # 如果指定了特定模式名稱
    if pattern_name:
        show_pattern_details(patterns_registry, pattern_name)
        return
    
    # 顯示詳細資訊
    if detail:
        for pattern_name in all_patterns:
            show_pattern_details(patterns_registry, pattern_name)
            console.print("\n" + "=" * 80 + "\n")
        return
    
    # 比較不同模式
    if compare:
        show_patterns_comparison(patterns_registry, all_patterns)
        return
    
    # 默認顯示 - 使用更簡潔的列表格式而非表格
    console.print(Panel.fit("[bold]支持的設計模式[/]", border_style="blue"))
    
    # 按類型分組顯示
    categories = {
        "創建型模式": ["singleton", "factory_method"],
        "結構型模式": ["adapter", "decorator"],
        "行為型模式": ["observer", "strategy"]
    }
    
    # 處理所有已分類的模式
    for category, pattern_names in categories.items():
        # 過濾出實際存在的模式
        existing_patterns = [p.lower() for p in all_patterns if p.lower() in pattern_names]
        
        if existing_patterns:
            console.print(f"\n[bold cyan]{category}[/]")
            
            for pattern in existing_patterns:
                pattern_info = patterns_registry.get_pattern(pattern)
                if pattern_info:
                    # 創建簡潔的描述
                    console.print(f"[bold green]{pattern_info.name}[/]")
                    console.print(f"  說明: {pattern_info.description}")
                    
                    # 顯示前兩個優點作為核心優勢
                    if pattern_info.benefits:
                        console.print("  優點:")
                        for benefit in pattern_info.benefits[:2]:
                            console.print(f"   • {benefit}")
                    
                    # 顯示適用場景的簡短描述
                    applicability = get_pattern_applicability(pattern_info)
                    app_points = applicability.split("；")[:2]  # 只取前兩點
                    console.print("  適用場景:")
                    for point in app_points:
                        if point.strip():
                            console.print(f"   • {point.strip()}")
                    
                    console.print("")  # 添加空行分隔
    
    # 處理未分類的模式
    all_categorized = sum(categories.values(), [])
    uncategorized = [p for p in all_patterns if p.lower() not in all_categorized]
    
    if uncategorized:
        console.print("\n[bold cyan]其他模式[/]")
        
        for pattern in uncategorized:
            pattern_info = patterns_registry.get_pattern(pattern)
            if pattern_info:
                console.print(f"[bold green]{pattern_info.name}[/]")
                console.print(f"  說明: {pattern_info.description}")
                
                # 顯示前兩個優點作為核心優勢
                if pattern_info.benefits:
                    console.print("  優點:")
                    for benefit in pattern_info.benefits[:2]:
                        console.print(f"   • {benefit}")
                
                console.print("")  # 添加空行分隔
    
    # 顯示使用提示
    console.print("\n[bold yellow]查看更多資訊:[/]")
    console.print(f"• 查看特定模式詳情: [cyan]python3 main.py patterns -p <模式名稱>[/]")
    console.print(f"• 比較不同模式: [cyan]python3 main.py patterns -c[/]")
    console.print(f"• 顯示模式結構圖: [cyan]python3 main.py pattern-diagram <模式名稱>[/]")
    
@app.command("pattern-guide")
def pattern_guide():
    """
    提供設計模式選擇指南，幫助用戶決定何時使用哪種模式。
    """
    console.print(Panel.fit(
        "設計模式選擇指南",
        title="指南",
        border_style="blue"
    ))
    
    console.print("""
[bold]設計模式分類[/]

設計模式通常被分為三種主要類型：

1. [bold cyan]創建型模式[/]：提供創建對象的機制，增加靈活性並重用現有代碼。
   包括：Singleton、Factory Method、Abstract Factory、Builder、Prototype

2. [bold green]結構型模式[/]：解釋如何將對象和類組裝成更大的結構，同時保持結構的靈活性和高效性。
   包括：Adapter、Decorator、Proxy、Facade、Bridge、Composite、Flyweight

3. [bold yellow]行為型模式[/]：關注對象之間的責任分配和算法封裝。
   包括：Observer、Strategy、Command, Template Method, Iterator, State, Chain of Responsibility, Mediator, Memento, Visitor, Interpreter

[bold]何時選擇哪種模式？[/]

以下是一些常見問題及對應的設計模式解決方案：

1. [bold]問題：需要確保類只有一個實例[/]
   → 解決方案：[cyan]Singleton[/]

2. [bold]問題：需要創建對象但不確切知道要創建哪個具體類[/]
   → 解決方案：[cyan]Factory Method[/]或[cyan]Abstract Factory[/]

3. [bold]問題：需要在不修改已有代碼的情況下擴展其功能[/]
   → 解決方案：[green]Decorator[/]

4. [bold]問題：兩個不兼容的介面需要一起工作[/]
   → 解決方案：[green]Adapter[/]

5. [bold]問題：對象狀態變化時需要通知其他對象[/]
   → 解決方案：[yellow]Observer[/]

6. [bold]問題：想要能夠動態替換算法[/]
   → 解決方案：[yellow]Strategy[/]

7. [bold]問題：有複雜系統需要提供簡單介面[/]
   → 解決方案：[green]Facade[/]

8. [bold]問題：需要表示操作的歷史記錄或支持撤銷機制[/]
   → 解決方案：[yellow]Command[/]和[yellow]Memento[/]

9. [bold]問題：構建複雜對象的過程應獨立於部件的表示[/]
   → 解決方案：[cyan]Builder[/]

10. [bold]問題：對象的狀態會影響其行為[/]
    → 解決方案：[yellow]State[/]

使用 `patterns --compare` 命令可以查看更詳細的模式比較。
    """)
    
    console.print("\n[bold]模式選擇決策樹:[/]")
    
    # 使用Mermaid顯示決策樹會很棒，但這裡只能用文本表示
    decision_tree = """
創建對象？
├── 是 → 需要確保只有一個實例？
│      ├── 是 → [Singleton]
│      └── 否 → 是否需要創建一系列相關對象？
│             ├── 是 → [Abstract Factory]
│             └── 否 → 是否希望子類決定創建哪種類型的對象？
│                    ├── 是 → [Factory Method]
│                    └── 否 → 是否關注對象的創建過程？
│                           ├── 是 → [Builder]
│                           └── 否 → [Prototype]
└── 否 → 需要添加功能到對象？
       ├── 是 → 需要動態添加/移除功能？
       │      ├── 是 → [Decorator]
       │      └── 否 → 需要將不兼容的介面一起工作？
       │             ├── 是 → [Adapter]
       │             └── 否 → [Bridge]
       └── 否 → 涉及對象之間的通信？
              ├── 是 → 一對多依賴關係？
              │      ├── 是 → [Observer]
              │      └── 否 → 需要封裝算法？
              │             ├── 是 → [Strategy]
              │             └── 否 → [Mediator]
              └── 否 → 考慮其他模式...
"""
    console.print(decision_tree)

@app.command("pattern-diagram")
def pattern_diagram(
    pattern_name: str = typer.Argument(..., help="要顯示圖解的設計模式名稱")
):
    """
    顯示設計模式的結構圖解和流程。
    """
    patterns_registry = PatternsRegistry()
    pattern_info = patterns_registry.get_pattern(pattern_name)
    
    if not pattern_info:
        console.print(f"[bold red]錯誤:[/] 未找到名為 '{pattern_name}' 的模式。")
        available_patterns = patterns_registry.get_all_patterns()
        if available_patterns:
            console.print(f"可用的模式: {', '.join(available_patterns)}")
        return
    
    console.print(Panel(f"[bold]{pattern_info.name} 模式圖解[/]", border_style="blue"))
    
    # 使用 ASCII 藝術圖顯示模式結構
    if pattern_info.name == "Singleton":
        diagram = """
        ┌───────────────────────┐
        │      Singleton        │
        ├───────────────────────┤
        │ - instance: Singleton │
        ├───────────────────────┤
        │ + getInstance()       │◄───┐
        │ - Singleton()         │    │
        └───────────────────────┘    │
                 ▲                   │
                 │                   │
                 └───────────────────┘
                 returns single instance
        """
    elif pattern_info.name == "Factory Method":
        diagram = """
        ┌───────────────┐         ┌───────────┐
        │    Creator    │         │  Product  │
        ├───────────────┤         ├───────────┤
        │ + factoryMethod() │◄────►│ + operation() │
        │ + anOperation() │         └───────────┘
        └───────────────┘              ▲
               ▲                       │
               │                       │
        ┌──────┴────────┐      ┌──────┴────────┐
        │ ConcreteCreator│      │ConcreteProduct│
        ├───────────────┤      ├───────────────┤
        │ + factoryMethod() │──►│ + operation() │
        └───────────────┘      └───────────────┘
        """
    elif pattern_info.name == "Observer":
        diagram = """
        ┌───────────┐       ┌───────────┐
        │  Subject  │       │  Observer │
        ├───────────┤       ├───────────┤
        │ + attach()│◄──────►│ + update()│
        │ + detach()│       └───────────┘
        │ + notify()│             ▲
        └───────────┘             │
             ▲                    │
             │                    │
        ┌────┴──────┐      ┌─────┴──────┐
        │ConcreteSubject│   │ConcreteObserver│
        ├────────────┤      ├─────────────┤
        │ + getState()│      │ + update()    │
        │ + setState()│      └──────────────┘
        └────────────┘
        """
    elif pattern_info.name == "Strategy":
        diagram = """
        ┌────────────┐        ┌───────────┐
        │   Context  │        │  Strategy │
        ├────────────┤        ├───────────┤
        │ - strategy │◄───────►│ + execute()│
        ├────────────┤        └───────────┘
        │ + method() │              ▲
        └────────────┘              │
                                    │
              ┌────────────────────┬┴───────────────┐
              │                    │                │
        ┌─────┴─────┐      ┌──────┴─────┐    ┌─────┴──────┐
        │StrategyA  │      │StrategyB   │    │StrategyC   │
        ├───────────┤      ├────────────┤    ├────────────┤
        │ + execute()│      │ + execute() │    │ + execute() │
        └───────────┘      └────────────┘    └────────────┘
        """
    elif pattern_info.name == "Decorator":
        diagram = """
        ┌────────────┐
        │  Component │
        ├────────────┤
        │ + operation()│
        └────────────┘
             ▲
             │
      ┌──────┴─────────────────┐
      │                         │
┌─────┴─────┐          ┌───────┴────────┐
│ConcreteComponent│     │    Decorator     │
├─────────────┤     ├────────────────┤
│ + operation()│     │ - component     │
└─────────────┘     ├────────────────┤
                    │ + operation()    │
                    └────────────────┘
                          ▲
                          │
           ┌──────────────┴─────────────┐
           │                            │
    ┌──────┴───────┐           ┌───────┴──────┐
    │DecoratorA    │           │DecoratorB    │
    ├──────────────┤           ├──────────────┤
    │ + operation()│           │ + operation()│
    │ + addedBehavior()│       │ + addedState() │
    └──────────────┘           └──────────────┘
        """
    elif pattern_info.name == "Adapter":
        diagram = """
        ┌───────────┐     ┌───────────┐
        │   Client  │     │   Target  │
        ├───────────┤     ├───────────┤
        │           │────►│ + request()│
        └───────────┘     └───────────┘
                               ▲
                               │
                          ┌────┴─────┐
                          │  Adapter │
                          ├──────────┤
                          │ + request()│
                          └──────────┘
                               │
                               ▼
                          ┌────────────┐
                          │  Adaptee   │
                          ├────────────┤
                          │ + specificRequest()│
                          └────────────┘
        """
    else:
        diagram = """
        模式圖解暫時不可用。
        請使用 show-pattern-details 命令查看詳細說明。
        """
    
    console.print(Syntax(diagram, "text", theme="ansi_dark"))
    
    # 顯示流程說明
    console.print("\n[bold]模式流程:[/]")
    
    if pattern_info.name == "Singleton":
        console.print("""
1. 客戶端調用 Singleton.getInstance()
2. Singleton 檢查是否已有實例
3. 如果沒有實例，創建一個新實例
4. 返回唯一的實例給客戶端
        """)
    elif pattern_info.name == "Factory Method":
        console.print("""
1. 客戶端創建 ConcreteCreator 並調用其 anOperation() 方法
2. Creator.anOperation() 調用 factoryMethod()
3. ConcreteCreator.factoryMethod() 創建並返回 ConcreteProduct
4. Creator 使用返回的 Product 物件而不需要知道其具體類型
        """)
    elif pattern_info.name == "Observer":
        console.print("""
1. ConcreteSubject 的狀態發生變化
2. ConcreteSubject.notify() 通知所有已註冊的 Observer
3. 每個 ConcreteObserver.update() 被調用
4. 每個 Observer 從 Subject 獲取更新的狀態並做出相應處理
        """)
    elif pattern_info.name == "Strategy":
        console.print("""
1. 客戶端創建 ConcreteStrategy 並將其傳遞給 Context
2. 客戶端調用 Context.method()
3. Context.method() 內部調用 strategy.execute()
4. 在運行時可以更改 Context 的 strategy 來切換算法
        """)
    elif pattern_info.name == "Decorator":
        console.print("""
1. 客戶端創建 ConcreteComponent
2. 客戶端用各種 Decorator 包裝 Component
3. 客戶端調用 operation() 方法
4. 每個 Decorator 先調用其包裝的 Component 的 operation()，再添加自己的行為
5. 調用鏈從最外層裝飾器開始，逐層向內直到原始組件
        """)
    elif pattern_info.name == "Adapter":
        console.print("""
1. 客戶端請求 Target 接口
2. 調用傳到 Adapter 的 request() 方法
3. Adapter 將請求轉換成 Adaptee 能理解的形式
4. Adapter 調用 Adaptee 的 specificRequest() 方法
5. 結果被 Adapter 轉換成 Target 接口的形式並返回給客戶端
        """)
    
    # 顯示應用場景
    console.print("\n[bold]常見應用場景:[/]")
    console.print(get_pattern_applicability(pattern_info))
    
    # 顯示代碼示例
    console.print("\n[bold]查看完整代碼示例:[/]")
    console.print(f"運行 [cyan]python3 main.py patterns -p {pattern_name}[/] 查看完整代碼示例")

@app.command("refactor")
def refactor(
    file_path: str = typer.Argument(..., help="要分析的 Python 文件路徑"),
    llm: bool = typer.Option(True, help="使用 LLM 進行更深入的分析和建議"),
    backup: bool = typer.Option(True, help="在應用更改前創建備份"),
    preview: bool = typer.Option(True, help="在應用更改前預覽更改"),
    apply: bool = typer.Option(False, help="自動詢問是否要應用建議"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="顯示詳細錯誤信息")
):
    """
    分析 Python 文件並生成重構建議，並可選擇性地應用所選建議。
    """
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path) or not file_path.endswith('.py'):
        console.print(f"[bold red]錯誤:[/] 文件 {file_path} 不是有效的 Python 文件。")
        return
    
    # 第一階段：生成建議
    console.print(f"正在分析 {file_path} 以獲取重構建議...")
    
    # 使用基本規則生成建議
    suggestion_ids = []
    try:
        suggestion_ids = suggestion_generator.generate_suggestions_for_file(file_path)
        
        if suggestion_ids:
            console.print("\n[bold]基本重構建議:[/]")
            suggestions_table = Table(title="重構建議")
            suggestions_table.add_column("ID", style="cyan")
            suggestions_table.add_column("類型", style="green")
            suggestions_table.add_column("描述", style="yellow")
            suggestions_table.add_column("嚴重性", style="red")
            
            for suggestion_id in suggestion_ids:
                suggestion = suggestion_generator.suggestion_store.get_suggestion(suggestion_id)
                if suggestion:
                    suggestions_table.add_row(
                        str(suggestion.id),
                        suggestion.type,
                        suggestion.description,
                        suggestion.severity
                    )
            
            console.print(suggestions_table)
        else:
            console.print("[yellow]未生成基本重構建議。[/]")
    except Exception as e:
        console.print(f"[bold red]生成基本建議時出錯:[/] {str(e)}")
        if verbose:
            import traceback
            console.print(Panel(traceback.format_exc(), title="錯誤詳情", border_style="red"))
    
    # 使用 LLM 進行更深入的分析
    llm_suggestion_ids = []
    if llm:
        if llm_client and hasattr(llm_client, 'api_key') and llm_client.api_key:
            console.print("\n[bold]正在生成 AI 驅動的重構建議...[/]")
            try:
                suggestions = refactoring_engine.suggest_refactorings(file_path)
                
                if suggestions and suggestions.get('llm_suggestions') and len(suggestions['llm_suggestions']) > 0:
                    llm_suggestions_table = Table(title="AI 驅動的重構建議")
                    llm_suggestions_table.add_column("ID", style="cyan")
                    llm_suggestions_table.add_column("類型", style="green")
                    llm_suggestions_table.add_column("描述", style="yellow")
                    llm_suggestions_table.add_column("位置", style="blue")
                    
                    for i, suggestion in enumerate(suggestions['llm_suggestions']):
                        # 為 LLM 建議創建 RefactoringSuggestion 對象並存儲
                        llm_suggestion = RefactoringSuggestion(
                            suggestion_id=0,  # 將由儲存設置
                            suggestion_type=suggestion.get('type', '未知'),
                            description=suggestion.get('description', ''),
                            location={
                                "file_path": file_path,
                                "start_line": 1,  # 默認值
                                "end_line": -1
                            },
                            recommendation=suggestion.get('recommendation', ''),
                            code_example=suggestion.get('code_example', '')
                        )
                        
                        # 從位置字符串中提取行號（如果可能）
                        location_str = suggestion.get('location', '')
                        line_match = re.search(r'行\s*(\d+)', location_str)
                        if line_match:
                            llm_suggestion.location["start_line"] = int(line_match.group(1))
                            
                            # 檢查是否有結束行
                            end_line_match = re.search(r'行\s*\d+\s*-\s*(\d+)', location_str)
                            if end_line_match:
                                llm_suggestion.location["end_line"] = int(end_line_match.group(1))
                        
                        # 添加到儲存並獲取 ID
                        suggestion_id = suggestion_generator.suggestion_store.add_suggestion(llm_suggestion)
                        llm_suggestion_ids.append(suggestion_id)
                        
                        llm_suggestions_table.add_row(
                            str(suggestion_id),
                            suggestion.get('type', '未知'),
                            suggestion.get('description', ''),
                            suggestion.get('location', '')
                        )
                    
                    console.print(llm_suggestions_table)
                    
                    # 顯示第一個建議的詳情
                    if suggestions['llm_suggestions']:
                        first_suggestion = suggestions['llm_suggestions'][0]
                        first_id = llm_suggestion_ids[0] if llm_suggestion_ids else None
                        console.print("\n[bold]第一個建議的詳情:[/]")
                        console.print(Panel(
                            f"[bold]ID:[/] {first_id}\n"
                            f"[bold]類型:[/] {first_suggestion.get('type', '未知')}\n"
                            f"[bold]描述:[/] {first_suggestion.get('description', '')}\n"
                            f"[bold]位置:[/] {first_suggestion.get('location', '')}\n"
                            f"[bold]建議:[/] {first_suggestion.get('recommendation', '')}"
                        ))
                        
                        if first_suggestion.get('code_example'):
                            console.print("\n[bold]程式碼範例:[/]")
                            syntax = Syntax(
                                first_suggestion.get('code_example', ''),
                                "python",
                                theme="monokai",
                                line_numbers=True
                            )
                            console.print(syntax)
                else:
                    console.print("[yellow]未生成 AI 驅動的建議。[/]")
            except Exception as e:
                console.print(f"[bold red]生成 AI 驅動建議時出錯:[/] {str(e)}")
                if verbose:
                    import traceback
                    console.print(Panel(traceback.format_exc(), title="錯誤詳情", border_style="red"))
        else:
            console.print("[yellow]LLM 集成不可用。請檢查您的 API 密鑰。[/]")
    
    # 合併所有建議 ID
    all_suggestion_ids = suggestion_ids + llm_suggestion_ids
    
    # 第二階段：如果啟用了應用選項，詢問用戶是否要應用建議
    if apply and all_suggestion_ids:
        console.print("\n[bold]應用重構建議:[/]")
        
        # 詢問用戶是否要應用建議
        apply_suggestion = typer.confirm("是否要應用其中一個建議？")
        if not apply_suggestion:
            console.print("[yellow]用戶選擇不應用建議。[/]")
            return
        
        # 詢問用戶要應用哪個建議
        valid_ids = [str(id) for id in all_suggestion_ids]
        suggestion_id_str = typer.prompt(
            f"請輸入要應用的建議 ID [{'/'.join(valid_ids)}]",
            default=str(all_suggestion_ids[0]) if all_suggestion_ids else ""
        )
        
        # 驗證輸入的 ID
        try:
            suggestion_id = int(suggestion_id_str)
            if suggestion_id not in all_suggestion_ids:
                console.print(f"[bold red]錯誤:[/] 無效的建議 ID {suggestion_id}。")
                return
        except ValueError:
            console.print(f"[bold red]錯誤:[/] 無效的建議 ID '{suggestion_id_str}'。")
            return
        
        # 獲取建議
        suggestion = suggestion_generator.suggestion_store.get_suggestion(suggestion_id)
        if not suggestion:
            console.print(f"[bold red]錯誤:[/] 未找到 ID 為 {suggestion_id} 的建議。")
            return
        
        console.print(f"\n[bold]正在應用建議 #{suggestion_id}:[/] {suggestion.description}")
        
        # 讀取原始內容
        original_content = read_file(file_path)
        if original_content is None:
            console.print(f"[bold red]錯誤:[/] 無法讀取文件 {file_path}。")
            return
        
        # 生成重構代碼
        refactored_code = refactoring_engine.generate_refactored_code(file_path, suggestion_id)
        if not refactored_code:
            console.print("[bold red]錯誤:[/] 無法生成重構代碼。")
            return
        
        # 如果請求，則預覽更改
        if preview:
            console.print("\n[bold]更改預覽:[/]")
            import difflib
            diff = difflib.unified_diff(
                original_content.splitlines(keepends=True),
                refactored_code.splitlines(keepends=True),
                fromfile=f"a/{os.path.basename(file_path)}",
                tofile=f"b/{os.path.basename(file_path)}",
                n=3
            )
            diff_text = ''.join(diff)
            
            if diff_text:
                console.print(Syntax(diff_text, "diff", theme="monokai"))
            else:
                console.print("[yellow]未檢測到更改。[/]")
                return
            
            # 請求確認
            apply_changes = typer.confirm("應用這些更改？")
            if not apply_changes:
                console.print("[yellow]未應用更改。[/]")
                return
        
        # 生成時間戳
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 根據建議類型創建新文件名
        suggestion_type = suggestion.type
        file_name, file_ext = os.path.splitext(file_path)
        new_file_path = f"{file_name}_{suggestion_type}_{timestamp}{file_ext}"
        
        # 如果請求了備份，則創建原始文件的備份
        if backup:
            backup_file_path = f"{file_name}_backup_{timestamp}{file_ext}"
            success = write_file(backup_file_path, original_content)
            if success:
                console.print(f"[green]已創建備份文件:[/] {backup_file_path}")
            else:
                console.print("[bold red]無法創建備份。[/]")
                return
        
        # 寫入新文件
        success = write_file(new_file_path, refactored_code)
        
        if success:
            console.print(f"[bold green]更改已應用到新文件:[/] {new_file_path}")
            suggestion_generator.suggestion_store.mark_suggestion_applied(suggestion_id)
        else:
            console.print("[bold red]無法將更改應用到新文件。[/]")
            
@app.command("analyze-performance")
def analyze_performance(
    file_path: str = typer.Argument(..., help="要分析性能問題的 Python 文件路徑"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="分析結果的輸出文件路徑"),
    optimize: bool = typer.Option(False, "--optimize", help="生成代碼的優化版本")
):
    """
    分析 Python 代碼的性能問題並建議優化方案。
    """
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path) or not file_path.endswith('.py'):
        console.print(f"[bold red]錯誤:[/] 文件 {file_path} 不是有效的 Python 文件。")
        return
    
    console.print(f"正在分析 {file_path} 的性能...")
    
    # 分析性能
    analysis_result = perf_analyzer.analyze_file(file_path)
    
    # 顯示結果
    if analysis_result.get('issues'):
        console.print("\n[bold]性能問題:[/]")
        issues_table = Table(title="檢測到的問題")
        issues_table.add_column("類型", style="cyan")
        issues_table.add_column("描述", style="yellow")
        issues_table.add_column("行號", style="blue")
        issues_table.add_column("嚴重性", style="red")
        
        for issue in analysis_result['issues']:
            issues_table.add_row(
                issue['issue_type'],
                issue['description'],
                str(issue['line_number']) if issue['line_number'] else "N/A",
                issue['severity']
            )
        
        console.print(issues_table)
    else:
        console.print("[green]未檢測到性能問題。[/]")
    
    # 顯示指標
    if analysis_result.get('metrics'):
        console.print("\n[bold]性能指標:[/]")
        metrics_table = Table(title="性能指標")
        metrics_table.add_column("指標", style="cyan")
        metrics_table.add_column("值", style="green")
        
        for metric, value in analysis_result['metrics'].items():
            if metric not in ('profile_output', 'function_stats'):
                metrics_table.add_row(metric, str(value))
        
        console.print(metrics_table)
        
        # 如果可用，顯示函數統計信息
        if 'function_stats' in analysis_result['metrics']:
            console.print("\n[bold]函數性能統計:[/]")
            stats_table = Table(title="按執行時間排序的頂部函數")
            stats_table.add_column("函數", style="cyan")
            stats_table.add_column("調用次數", style="blue")
            stats_table.add_column("總時間", style="yellow")
            stats_table.add_column("每次調用時間", style="green")
            
            for stat in analysis_result['metrics']['function_stats'][:5]:  # 顯示前 5 個
                stats_table.add_row(
                    stat.get('function', ''),
                    stat.get('ncalls', ''),
                    stat.get('tottime', ''),
                    stat.get('percall', '')
                )
            
            console.print(stats_table)
    
    # 生成優化建議
    suggestions = perf_analyzer.suggest_improvements(file_path, analysis_result)
    
    if suggestions:
        console.print("\n[bold]優化建議:[/]")
        suggestions_table = Table(title="優化建議")
        suggestions_table.add_column("類型", style="cyan")
        suggestions_table.add_column("描述", style="yellow")
        suggestions_table.add_column("建議", style="green")
        
        for suggestion in suggestions:
            suggestions_table.add_row(
                suggestion['type'],
                suggestion['description'],
                suggestion['recommendation']
            )
        
        console.print(suggestions_table)
    
    # 如果請求，生成優化代碼
    if optimize and llm_client and llm_client.api_key:
        console.print("\n[bold]正在生成優化代碼...[/]")
        
        # 創建帶有 LLM 客戶端的性能優化器
        from performance.perf_analyzer import PerformanceOptimizer
        optimizer = PerformanceOptimizer(llm_client)
        
        # 生成優化代碼
        optimized_code = optimizer.optimize_code(file_path, analysis_result.get('issues', []))
        
        if optimized_code:
            # 顯示預覽
            console.print("\n[bold]優化代碼預覽:[/]")
            
            # 差異視圖
            import difflib
            original_content = read_file(file_path)
            diff = difflib.unified_diff(
                original_content.splitlines(keepends=True),
                optimized_code.splitlines(keepends=True),
                fromfile=f"a/{os.path.basename(file_path)}",
                tofile=f"b/{os.path.basename(file_path)}",
                n=3
            )
            diff_text = ''.join(diff)
            
            if diff_text:
                console.print(Syntax(diff_text, "diff", theme="monokai"))
            else:
                console.print("[yellow]優化代碼中沒有變化。[/]")
            
            # 如果指定了輸出或用戶確認，則保存優化代碼
            if output:
                write_file(output, optimized_code)
                console.print(f"[green]優化代碼已保存到: {output}[/]")
            else:
                save_optimized = typer.confirm("保存優化代碼？")
                if save_optimized:
                    optimized_path = f"{os.path.splitext(file_path)[0]}_optimized.py"
                    write_file(optimized_path, optimized_code)
                    console.print(f"[green]優化代碼已保存到: {optimized_path}[/]")
        else:
            console.print("[yellow]無法生成優化代碼。[/]")
    
    # 如果請求，將完整分析保存到文件
    if output and not optimize:
        import json
        
        # 將分析轉換為可讀格式
        output_content = "# 性能分析報告\n\n"
        
        # 添加問題
        if analysis_result.get('issues'):
            output_content += "## 性能問題\n\n"
            for issue in analysis_result['issues']:
                output_content += f"### {issue['issue_type']}\n"
                output_content += f"- **描述:** {issue['description']}\n"
                output_content += f"- **嚴重性:** {issue['severity']}\n"
                if issue['line_number']:
                    output_content += f"- **行號:** {issue['line_number']}\n"
                if issue['suggestion']:
                    output_content += f"- **建議:** {issue['suggestion']}\n"
                output_content += "\n"
        
        # 添加指標
        if analysis_result.get('metrics'):
            output_content += "## 性能指標\n\n"
            for metric, value in analysis_result['metrics'].items():
                if metric not in ('profile_output', 'function_stats'):
                    output_content += f"- **{metric}:** {value}\n"
            
            # 添加函數統計
            if 'function_stats' in analysis_result['metrics']:
                output_content += "\n### 函數性能統計\n\n"
                output_content += "| 函數 | 調用次數 | 總時間 | 每次調用時間 |\n"
                output_content += "|----------|-------|------------|---------------|\n"
                
                for stat in analysis_result['metrics']['function_stats'][:10]:  # 顯示前 10 個
                    output_content += f"| {stat.get('function', '')} | {stat.get('ncalls', '')} | {stat.get('tottime', '')} | {stat.get('percall', '')} |\n"
        
        # 添加優化建議
        if suggestions:
            output_content += "\n## 優化建議\n\n"
            for suggestion in suggestions:
                output_content += f"### {suggestion['type']}\n"
                output_content += f"- **描述:** {suggestion['description']}\n"
                output_content += f"- **建議:** {suggestion['recommendation']}\n"
                if suggestion.get('code_example'):
                    output_content += f"\n```python\n{suggestion['code_example']}\n```\n"
                output_content += "\n"
        
        # 寫入文件
        write_file(output, output_content)
        console.print(f"[green]性能分析報告已保存到: {output}[/]")

@app.command("generate-docs")
def generate_docs(
    path: str = typer.Argument(..., help="要生成文檔的 Python 文件或目錄的路徑"),
    output_dir: str = typer.Option("docs", help="文檔的輸出目錄"),
    check_consistency: bool = typer.Option(True, help="檢查代碼和文檔之間的一致性")
):
    """
    為 Python 代碼生成 API 文檔。
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        console.print(f"[bold red]錯誤:[/] 路徑 {path} 不存在。")
        return
    
    # 創建文檔生成器
    doc_gen = DocGenerator(project_path, output_dir)
    
    if os.path.isfile(path):
        if not path.endswith('.py'):
            console.print(f"[bold red]錯誤:[/] 文件 {path} 不是 Python 文件。")
            return
        
        console.print(f"正在為文件生成文檔: {path}")
        result = doc_gen.generate_docs_for_file(path)
        
        if result:
            console.print(f"[green]文檔生成成功![/]")
            console.print(f"輸出文件: {result['output_file']}")
            
            # 打印統計信息
            console.print("\n[bold]文檔統計:[/]")
            stats_table = Table()
            stats_table.add_column("指標", style="cyan")
            stats_table.add_column("數量", style="green")
            
            stats_table.add_row("已文檔化的類", str(result['classes_documented']))
            stats_table.add_row("已文檔化的函數", str(result['functions_documented']))
            
            console.print(stats_table)
            
            # 如果請求，檢查文檔一致性
            if check_consistency:
                console.print("\n[bold]檢查文檔一致性:[/]")
                consistency_checker = ConsistencyChecker(project_path)
                consistency_result = consistency_checker.check_file(path)
                
                # 顯示一致性結果
                console.print(f"整體一致性: {consistency_result['overall_consistency']}%")
                
                # 如果有，顯示不一致之處
                all_inconsistencies = []
                
                if consistency_result['module_inconsistencies']:
                    console.print("\n[yellow]模塊不一致:[/]")
                    for issue in consistency_result['module_inconsistencies']:
                        console.print(f"- {issue}")
                        all_inconsistencies.append(issue)
                
                for class_name, issues in consistency_result['class_inconsistencies'].items():
                    if issues:
                        console.print(f"\n[yellow]類 '{class_name}' 不一致:[/]")
                        for issue in issues:
                            console.print(f"- {issue}")
                            all_inconsistencies.append(f"{class_name}: {issue}")
                
                for func_name, issues in consistency_result['function_inconsistencies'].items():
                    if issues:
                        console.print(f"\n[yellow]函數 '{func_name}' 不一致:[/]")
                        for issue in issues:
                            console.print(f"- {issue}")
                            all_inconsistencies.append(f"{func_name}: {issue}")
                
                if not all_inconsistencies:
                    console.print("[green]未發現不一致。[/]")
        else:
            console.print("[yellow]無法生成文檔。[/]")
    else:
        # 處理目錄
        console.print(f"正在為目錄生成文檔: {path}")
        result = doc_gen.generate_docs_for_project()
        
        if result:
            console.print(f"[green]文檔生成成功![/]")
            
            # 打印統計信息
            console.print("\n[bold]文檔統計:[/]")
            stats_table = Table()
            stats_table.add_column("指標", style="cyan")
            stats_table.add_column("數量", style="green")
            
            stats_table.add_row("處理的文件", str(result['files_processed']))
            stats_table.add_row("已文檔化的模塊", str(result['modules_documented']))
            stats_table.add_row("已文檔化的類", str(result['classes_documented']))
            stats_table.add_row("已文檔化的函數", str(result['functions_documented']))
            
            console.print(stats_table)
            
            # 顯示生成的文件
            if result['generated_files']:
                console.print("\n[bold]已生成的文檔文件:[/]")
                for file_path in result['generated_files'][:5]:  # 顯示前 5 個
                    console.print(f"- {os.path.relpath(file_path, project_path)}")
                
                if len(result['generated_files']) > 5:
                    console.print(f"... 還有 {len(result['generated_files']) - 5} 個文件")
            
            # 顯示缺失的文檔字符串
            if result['missing_docstrings']:
                console.print("\n[yellow]缺失的文檔字符串:[/]")
                missing_table = Table()
                missing_table.add_column("元素", style="cyan")
                
                for element in result['missing_docstrings'][:10]:  # 顯示前 10 個
                    missing_table.add_row(element)
                
                console.print(missing_table)
                
                if len(result['missing_docstrings']) > 10:
                    console.print(f"... 還有 {len(result['missing_docstrings']) - 10} 個缺失的文檔字符串")
        else:
            console.print("[yellow]無法生成文檔。[/]")

@app.command("analyze-api")
def analyze_api(
    path: str = typer.Argument(..., help="Path to the API project"),
    framework: str = typer.Option(None, help="Specify framework (django, flask, fastapi)"),
    endpoints_only: bool = typer.Option(False, help="Analyze only API endpoints"),
    security_focus: bool = typer.Option(False, help="Focus on security analysis"),
    generate_tests: bool = typer.Option(False, help="Generate API tests")
):
    """
    分析 Python Web API 代碼以識別重構機會。
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        console.print(f"[bold red]錯誤:[/] 路徑 {path} 不存在。")
        return
    
    console.print(f"正在分析 API 專案 {path}...")
    
    # 使用 API 分析器
    from api_analyzer.endpoint_analyzer import EndpointAnalyzer
    from api_analyzer.schema_extractor import SchemaExtractor
    schema_extractor = SchemaExtractor(path, framework)
    analyzer = EndpointAnalyzer(path)
    
    # 如果未指定框架，則嘗試檢測
    if not framework:
        detected_framework = analyzer.detect_framework()
        if detected_framework:
            framework = detected_framework
            console.print(f"檢測到 [bold green]{framework}[/] 框架")
        else:
            console.print("[yellow]警告:[/] 無法檢測 API 框架，使用通用分析")
    
    # 分析端點
    console.print("\n[bold]正在分析 API 端點...[/]")
    endpoints = analyzer.analyze_endpoints()
    
    if not endpoints:
        console.print("[yellow]未找到 API 端點。請確認專案使用了支援的 Web 框架 (Django, Flask, FastAPI)[/]")
        return
    
    # 顯示端點
    endpoints_table = Table(title="API 端點")
    endpoints_table.add_column("路由", style="cyan")
    endpoints_table.add_column("方法", style="green")
    endpoints_table.add_column("位置", style="yellow")
    
    for endpoint in endpoints[:20]:  # 限制顯示 20 個端點
        methods = ", ".join(endpoint.get("methods", []))
        file_path = endpoint.get("file", "")
        line = str(endpoint.get("line", ""))
        location = f"{os.path.basename(file_path)}:{line}" if file_path else ""
        endpoints_table.add_row(endpoint.get("route", ""), methods, location)
    
    console.print(endpoints_table)
    
    if len(endpoints) > 20:
        console.print(f"... 及 {len(endpoints) - 20} 個其他端點")
    
    # 如果只分析端點，則到此為止
    if endpoints_only:
        return
    
    # In main.py, replace around line 1270
    console.print("\n[bold]正在分析 API 模式...[/]")
    schema_metrics = schema_extractor.get_schema_metrics()

    # Show summary information
    console.print(f"檢測到 {schema_metrics['total_models']} 個資料模型")

    # Get actual models/schemas
    models = schema_extractor.extract_models()
        
    if models:
        schemas_table = Table(title="API 資料模型")
        schemas_table.add_column("模型", style="cyan")
        schemas_table.add_column("欄位數量", style="green")
        schemas_table.add_column("檔案", style="yellow")
        
        for model in models:
            name = model.get('name', 'Unknown')
            fields_count = len(model.get('fields', []))
            file_path = model.get('file', '')
            schemas_table.add_row(name, str(fields_count), os.path.basename(file_path))
        
        console.print(schemas_table)
    else:
        console.print("[yellow]未找到 API 資料模型。[/]")
    
    # 安全性分析
    if security_focus:
        console.print("\n[bold]正在進行 API 安全性分析...[/]")
        from api_refactoring.security_enhancer import APISecurityEnhancer
        
        security_enhancer = APISecurityEnhancer(path, framework)
        security_analysis = security_enhancer.analyze_security_issues()
        
        # 顯示安全問題
        if security_analysis['auth_issues'] or security_analysis['input_validation_issues'] or security_analysis['data_exposure_issues']:
            issues_table = Table(title="API 安全問題")
            issues_table.add_column("類型", style="cyan")
            issues_table.add_column("嚴重性", style="red")
            issues_table.add_column("描述", style="yellow")
            issues_table.add_column("位置", style="blue")
            
            for issue in (security_analysis['auth_issues'] + 
                        security_analysis['input_validation_issues'] + 
                        security_analysis['data_exposure_issues']):
                
                issue_type = issue.get("type", "unknown")
                severity = issue.get("severity", "medium")
                description = issue.get("description", "")
                file_path = issue.get("file", "")
                line = str(issue.get("line", ""))
                location = f"{os.path.basename(file_path)}:{line}" if file_path and line else file_path
                
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                issues_table.add_row(issue_type, f"[{severity_style}]{severity}[/]", description, location)
            
            console.print(issues_table)
            console.print(f"\n總安全評分: [bold {'green' if security_analysis['overall_score'] >= 80 else 'yellow' if security_analysis['overall_score'] >= 60 else 'red'}]{security_analysis['overall_score']}/100[/]")
        else:
            console.print("[green]未發現明顯的安全問題。[/]")
    
    # RESTful API 分析
    console.print("\n[bold]正在分析 RESTful API 設計...[/]")
    from api_refactoring.restful_design import RESTfulDesignAnalyzer
    
    restful_analyzer = RESTfulDesignAnalyzer(path, framework)
    restful_analysis = restful_analyzer.analyze_restful_design()
    
    if restful_analysis['restful_issues']:
        issues_table = Table(title="RESTful 設計問題")
        issues_table.add_column("類型", style="cyan")
        issues_table.add_column("嚴重性", style="red")
        issues_table.add_column("端點", style="blue")
        issues_table.add_column("描述", style="yellow")
        
        for issue in restful_analysis['restful_issues']:
            issue_type = issue.get("type", "unknown")
            severity = issue.get("severity", "medium")
            endpoint = issue.get("endpoint", "")
            description = issue.get("description", "")
            
            severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
            issues_table.add_row(issue_type, f"[{severity_style}]{severity}[/]", endpoint, description)
        
        console.print(issues_table)
        console.print(f"\nRESTful 設計評分: [bold {'green' if restful_analysis['restful_score'] >= 80 else 'yellow' if restful_analysis['restful_score'] >= 60 else 'red'}]{restful_analysis['restful_score']}/100[/]")
    else:
        console.print("[green]API 符合 RESTful 設計原則。[/]")
    
@app.command("api-patterns")
def api_patterns(
    pattern_name: str = typer.Option(None, help="API pattern to examine")
):
    """
    列出常見的 API 設計模式和最佳實踐。
    """
    # API 設計模式
    patterns = {
        "crud": {
            "name": "CRUD 操作",
            "description": "使用 HTTP 方法表示 Create, Read, Update, Delete 操作",
            "example": """
GET /api/users            # 取得所有使用者
GET /api/users/{id}       # 取得特定使用者
POST /api/users           # 創建新使用者
PUT /api/users/{id}       # 更新使用者 (完整替換)
PATCH /api/users/{id}     # 部分更新使用者
DELETE /api/users/{id}    # 刪除使用者
            """
        },
        "nesting": {
            "name": "資源嵌套",
            "description": "表示相關資源之間的階層關係",
            "example": """
GET /api/users/{id}/orders            # 取得使用者的訂單
POST /api/users/{id}/orders           # 為使用者創建訂單
GET /api/users/{id}/orders/{order_id} # 取得使用者的特定訂單
            """
        },
        "filtering": {
            "name": "篩選、排序與分頁",
            "description": "使用查詢參數進行資料過濾、排序和分頁",
            "example": """
GET /api/users?role=admin              # 篩選
GET /api/users?sort=name&order=desc    # 排序
GET /api/users?page=2&per_page=20      # 分頁
GET /api/users?fields=id,name,email    # 欄位篩選
            """
        },
        "versioning": {
            "name": "API 版本控制",
            "description": "管理 API 的變更和向後相容性",
            "example": """
# URL 路徑版本控制
GET /api/v1/users
GET /api/v2/users

# 查詢參數版本控制
GET /api/users?version=1.0

# 標頭版本控制
GET /api/users
Accept: application/vnd.myapp.v1+json
            """
        },
        "status-codes": {
            "name": "HTTP 狀態碼使用",
            "description": "正確使用 HTTP 狀態碼表示操作結果",
            "example": """
200 OK              # 成功的 GET, PUT, PATCH 請求
201 Created         # 成功的 POST 請求
204 No Content      # 成功的 DELETE 請求
400 Bad Request     # 客戶端錯誤 (無效參數等)
401 Unauthorized    # 身份驗證錯誤
403 Forbidden       # 無權限訪問
404 Not Found       # 資源不存在
429 Too Many Requests # 超過速率限制
500 Internal Server Error # 伺服器錯誤
            """
        },
        "hypermedia": {
            "name": "HATEOAS (Hypermedia as the Engine of Application State)",
            "description": "在回應中包含相關資源的連結，增強 API 的可發現性",
            "example": """
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "_links": {
    "self": { "href": "/api/users/123" },
    "orders": { "href": "/api/users/123/orders" },
    "invoices": { "href": "/api/users/123/invoices" }
  }
}
            """
        },
        "error-handling": {
            "name": "錯誤處理",
            "description": "統一且詳細的錯誤回應格式",
            "example": """
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "無效的 'email' 參數",
    "details": "提供的電子郵件地址格式不正確",
    "status": 400,
    "timestamp": "2023-12-15T12:34:56Z",
    "path": "/api/users"
  }
}
            """
        },
        "rate-limiting": {
            "name": "速率限制",
            "description": "防止 API 被濫用的機制",
            "example": """
# 標頭
X-Rate-Limit-Limit: 100      # 總請求限制
X-Rate-Limit-Remaining: 87   # 剩餘請求次數
X-Rate-Limit-Reset: 1628567219  # 重置時間 (Unix 時間戳)

# 回應 (超過限制時)
HTTP/1.1 429 Too Many Requests
X-Rate-Limit-Limit: 100
X-Rate-Limit-Remaining: 0
X-Rate-Limit-Reset: 1628567219

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "已超過 API 速率限制"
  }
}
            """
        }
    }
    
    # 如果指定了特定模式，顯示詳細資訊
    if pattern_name:
        pattern = patterns.get(pattern_name.lower())
        if pattern:
            console.print(Panel(f"[bold]{pattern['name']}[/]", border_style="blue"))
            console.print(f"\n[bold cyan]描述:[/]\n{pattern['description']}")
            console.print("\n[bold cyan]範例:[/]")
            console.print(Syntax(pattern['example'], "text", theme="monokai"))
        else:
            console.print(f"[bold red]未找到名為 '{pattern_name}' 的 API 設計模式。[/]")
            console.print("可用的模式: " + ", ".join(patterns.keys()))
        return
    
    # 顯示所有模式摘要
    console.print(Panel("API 設計模式和最佳實踐", border_style="blue"))
    
    for key, pattern in patterns.items():
        console.print(f"\n[bold green]{pattern['name']}[/] [cyan]({key})[/]")
        console.print(f"{pattern['description']}")
    
    console.print("\n[bold yellow]查看特定模式的詳細資訊:[/]")
    console.print("python main.py api-patterns --pattern <模式名稱>")
    
    console.print("\n[bold]其他 API 最佳實踐:[/]")
    console.print("• 一致性: 在整個 API 中使用一致的命名和格式")
    console.print("• 文檔: 提供完整的 API 文檔，如使用 OpenAPI (Swagger)")
    console.print("• 安全性: 實施適當的身份驗證、授權和資料驗證")
    console.print("• 速率限制: 防止 API 被濫用")
    console.print("• 快取控制: 使用適當的快取標頭優化效能")
    console.print("• HTTPS: 始終使用 HTTPS 加密所有 API 流量")

@app.command("generate-openapi")
def generate_openapi(
    path: str = typer.Argument(..., help="Path to the API project"),
    output: str = typer.Option("openapi.json", help="Output file for OpenAPI spec"),
    title: str = typer.Option("API Documentation", help="API title"),
    version: str = typer.Option("1.0.0", help="API version"),
    description: str = typer.Option(None, help="API description")
):
    """
    從代碼生成或更新 OpenAPI 規範。
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        console.print(f"[bold red]錯誤:[/] 路徑 {path} 不存在。")
        return
    
    console.print(f"正在分析 API 專案 {path}...")
    
    # 使用 API 分析器
    from api_analyzer.endpoint_analyzer import EndpointAnalyzer
    from api_analyzer.schema_extractor import SchemaExtractor
    
    analyzer = EndpointAnalyzer(path)
    
    # 檢測框架
    framework = analyzer.detect_framework()
    if framework:
        console.print(f"檢測到 [bold green]{framework}[/] 框架")
    else:
        console.print("[yellow]警告:[/] 無法檢測 API 框架，使用通用分析")
    
    # 分析端點
    console.print("\n[bold]正在分析 API 端點...[/]")
    endpoints = analyzer.analyze_endpoints()
    
    if not endpoints:
        console.print("[yellow]未找到 API 端點。請確認專案使用了支援的 Web 框架 (Django, Flask, FastAPI)[/]")
        return
    
    console.print(f"發現 {len(endpoints)} 個端點")
    
    # 提取 API 模式 - 使用 extract_models() 而非 get_schema_metrics()
    console.print("\n[bold]正在分析 API 資料模型...[/]")
    schema_extractor = SchemaExtractor(path, framework)
    models = schema_extractor.extract_models()
    
    if models:
        console.print(f"發現 {len(models)} 個資料模型")
    else:
        console.print("[yellow]未找到 API 資料模型。[/]")
    
    # 生成 OpenAPI 規範
    console.print("\n[bold]正在生成 OpenAPI 規範...[/]")
    import json
    import datetime
    
    # 基本資訊
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description or f"API Documentation generated on {datetime.datetime.now().strftime('%Y-%m-%d')}",
        },
        "servers": [
            {
                "url": "/api",
                "description": "API Server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        }
    }
    
    # 處理端點
    for endpoint in endpoints:
        route = endpoint.get("route", "")
        # 兼容性檢查 - 接受 path 或 route
        if not route:
            route = endpoint.get("path", "")
            
        methods = endpoint.get("methods", [])
        # 兼容性檢查 - 接受單個 method 或 methods 列表
        if not methods and "method" in endpoint:
            methods = [endpoint.get("method")]
        
        if not route.startswith("/"):
            route = "/" + route
        
        # 確保路徑存在於 spec 中
        if route not in openapi_spec["paths"]:
            openapi_spec["paths"][route] = {}
        
        # 為每個 HTTP 方法添加定義
        for method in methods:
            method_lower = method.lower()
            
            # 跳過不支援的方法
            if method_lower not in ["get", "post", "put", "patch", "delete"]:
                continue
            
            # 根據方法建立操作對象
            operation = {
                "summary": f"{method} {route}",
                "description": f"{method} operation on {route}",
                "responses": {
                    "200": {
                        "description": "Successful operation"
                    },
                    "400": {
                        "description": "Bad request"
                    },
                    "401": {
                        "description": "Unauthorized"
                    }
                }
            }
            
            # 添加參數 (如果是 URL 中的參數)
            parameters = []
            if "{" in route:
                import re
                # 尋找路徑中的參數，如 {id}
                path_params = re.findall(r'\{([^}]+)\}', route)
                for param in path_params:
                    parameters.append({
                        "name": param,
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string"
                        }
                    })
            
            if parameters:
                operation["parameters"] = parameters
            
            # 如果是 POST 或 PUT 或 PATCH 方法，添加請求體
            if method_lower in ["post", "put", "patch"]:
                operation["requestBody"] = {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object"
                            }
                        }
                    }
                }
            
            # 添加操作到路徑下
            openapi_spec["paths"][route][method_lower] = operation
    
    # 處理模型 - 使用新的資料結構
    for model in models:
        model_name = model.get('name')
        properties = {}
        required = []
        
        # 處理每個字段
        for field in model.get('fields', []):
            field_name = field.get('name')
            field_type = field.get('type')
            
            # 跳過空字段名
            if not field_name:
                continue
                
            # 將 Python/框架 類型映射到 OpenAPI 類型
            openapi_type = "string"
            if field_type:
                field_type_lower = field_type.lower()
                if 'int' in field_type_lower or 'integer' in field_type_lower:
                    openapi_type = "integer"
                elif 'float' in field_type_lower or 'double' in field_type_lower or 'decimal' in field_type_lower:
                    openapi_type = "number"
                elif 'bool' in field_type_lower:
                    openapi_type = "boolean"
                elif 'dict' in field_type_lower or 'json' in field_type_lower:
                    openapi_type = "object"
                elif 'list' in field_type_lower or 'array' in field_type_lower:
                    openapi_type = "array"
                elif 'date' in field_type_lower:
                    openapi_type = "string"
                    properties[field_name] = {
                        "type": openapi_type,
                        "format": "date"
                    }
                    continue
                elif 'time' in field_type_lower and 'date' in field_type_lower:
                    openapi_type = "string"
                    properties[field_name] = {
                        "type": openapi_type,
                        "format": "date-time"
                    }
                    continue
            
            # 設置屬性
            properties[field_name] = {
                "type": openapi_type
            }
            
            # 檢查是否必需
            # 在 Django 模型中，檢查 null=False 或 blank=False
            is_required = False
            for arg in field.get('args', []):
                if isinstance(arg, dict):
                    if arg.get('name') == 'null' and arg.get('value') is False:
                        is_required = True
                    if arg.get('name') == 'blank' and arg.get('value') is False:
                        is_required = True
            
            if is_required:
                required.append(field_name)
        
        if properties:  # 只有有屬性時才添加模型
            schema_def = {
                "type": "object",
                "properties": properties
            }
            
            if required:
                schema_def["required"] = required
                
            openapi_spec["components"]["schemas"][model_name] = schema_def
    
    # 寫入 OpenAPI 規範
    with open(output, 'w') as f:
        json.dump(openapi_spec, f, indent=2)
    
    console.print(f"[bold green]OpenAPI 規範已生成至 {output}[/]")
    
    # 顯示下一步建議
    console.print("\n[bold]您可以使用以下工具查看生成的規範:[/]")
    console.print("• Swagger UI: https://swagger.io/tools/swagger-ui/")
    console.print("• Redoc: https://redocly.github.io/redoc/")
    console.print("• Stoplight Studio: https://stoplight.io/studio")

@app.command("api-security")
def api_security(
    path: str = typer.Argument(..., help="Path to the API project"),
    output: str = typer.Option(None, help="Output file for security report"),
    generate_tests: bool = typer.Option(False, help="Generate security test scripts"),
    compact: bool = typer.Option(False, "--compact", "-c", help="Use compact display mode"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full details including file paths")
):
    """
    分析 API 安全性問題並生成修復建議。
    """
    path = os.path.abspath(path)
    if not os.path.exists(path):
        console.print(f"[bold red]錯誤:[/] 路徑 {path} 不存在。")
        return
    
    console.print(f"正在分析 API 專案 {path} 的安全性...")
    
    # 使用 EndpointAnalyzer 檢測框架
    from api_analyzer.endpoint_analyzer import EndpointAnalyzer
    analyzer = EndpointAnalyzer(path)
    framework = analyzer.detect_framework()
    
    if framework:
        console.print(f"檢測到 [bold green]{framework}[/] 框架")
    else:
        console.print("[yellow]警告:[/] 無法檢測 API 框架，使用通用分析")
    
    # 使用 APISecurityEnhancer 進行安全分析
    from api_refactoring.security_enhancer import APISecurityEnhancer
    security_enhancer = APISecurityEnhancer(path, framework)
    security_analysis = security_enhancer.analyze_security_issues()
    
    # 顯示分析結果
    console.print("\n[bold]API 安全分析結果[/]")
    
    # 使用顏色顯示總分
    score = security_analysis['overall_score']
    score_color = 'green' if score >= 80 else 'yellow' if score >= 60 else 'red'
    console.print(f"總安全評分: [bold {score_color}]{score}/100[/]")
    
    critical_count = security_analysis['critical_issues_count']
    critical_color = 'green' if critical_count == 0 else 'yellow' if critical_count < 3 else 'red'
    console.print(f"關鍵問題數量: [bold {critical_color}]{critical_count}[/]")
    
    # 幫助函數：縮短文件路徑
    def shorten_path(file_path, max_length=40):
        if not verbose and file_path and len(file_path) > max_length:
            parts = file_path.split(os.sep)
            # 保留最後 2-3 個路徑部分
            if len(parts) > 3:
                return os.path.join("...", *parts[-3:])
            return file_path
        return file_path
    
    # 幫助函數：縮短描述
    def format_description(desc, max_length=50):
        if not verbose and desc and len(desc) > max_length:
            return desc[:max_length] + "..."
        return desc
    
    # 顯示身份驗證問題
    if security_analysis['auth_issues']:
        console.print("\n[bold]身份驗證問題:[/]")
        
        if compact:
            # 使用簡潔的列表格式而非表格
            for i, issue in enumerate(security_analysis['auth_issues'], 1):
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                console.print(f"[{severity_style}]{i}. {issue.get('type')}[/]: {format_description(issue.get('description', ''))}")
                console.print(f"   文件: {shorten_path(issue.get('file', ''))}")
                if 'line' in issue and issue['line']:
                    console.print(f"   行號: {issue['line']}")
                console.print("")
        else:
            auth_table = Table(show_header=True, header_style="bold", expand=True)
            auth_table.add_column("嚴重性", style="red", width=8)
            auth_table.add_column("問題類型", style="cyan", width=20)
            auth_table.add_column("描述", style="yellow", width=30)
            auth_table.add_column("檔案", style="blue", width=30, overflow="fold")
            
            for issue in security_analysis['auth_issues']:
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                auth_table.add_row(
                    f"[{severity_style}]{severity}[/]",
                    issue.get("type", ""),
                    format_description(issue.get("description", "")),
                    shorten_path(issue.get("file", ""))
                )
            
            console.print(auth_table)
    
    # 顯示輸入驗證問題
    if security_analysis['input_validation_issues']:
        console.print("\n[bold]輸入驗證問題:[/]")
        
        if compact:
            # 使用簡潔的列表格式
            for i, issue in enumerate(security_analysis['input_validation_issues'], 1):
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                console.print(f"[{severity_style}]{i}. {issue.get('type')}[/]: {format_description(issue.get('description', ''))}")
                console.print(f"   文件: {shorten_path(issue.get('file', ''))}")
                if 'line' in issue and issue['line']:
                    console.print(f"   行號: {issue['line']}")
                console.print("")
        else:
            validation_table = Table(show_header=True, header_style="bold", expand=True)
            validation_table.add_column("嚴重性", style="red", width=8)
            validation_table.add_column("問題類型", style="cyan", width=20)
            validation_table.add_column("描述", style="yellow", width=30)
            validation_table.add_column("檔案", style="blue", width=30, overflow="fold")
            
            for issue in security_analysis['input_validation_issues']:
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                validation_table.add_row(
                    f"[{severity_style}]{severity}[/]",
                    issue.get("type", ""),
                    format_description(issue.get("description", "")),
                    shorten_path(issue.get("file", ""))
                )
            
            console.print(validation_table)
    
    # 顯示數據洩露問題
    if security_analysis['data_exposure_issues']:
        console.print("\n[bold]數據洩露問題:[/]")
        
        if compact:
            # 使用簡潔的列表格式
            for i, issue in enumerate(security_analysis['data_exposure_issues'], 1):
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                console.print(f"[{severity_style}]{i}. {issue.get('type')}[/]: {format_description(issue.get('description', ''))}")
                console.print(f"   文件: {shorten_path(issue.get('file', ''))}")
                if 'line' in issue and issue['line']:
                    console.print(f"   行號: {issue['line']}")
                console.print("")
        else:
            exposure_table = Table(show_header=True, header_style="bold", expand=True)
            exposure_table.add_column("嚴重性", style="red", width=8)
            exposure_table.add_column("問題類型", style="cyan", width=20)
            exposure_table.add_column("描述", style="yellow", width=30)
            exposure_table.add_column("檔案", style="blue", width=30, overflow="fold")
            
            for issue in security_analysis['data_exposure_issues']:
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                exposure_table.add_row(
                    f"[{severity_style}]{severity}[/]",
                    issue.get("type", ""),
                    format_description(issue.get("description", "")),
                    shorten_path(issue.get("file", ""))
                )
            
            console.print(exposure_table)
    
    # 顯示基礎設施問題
    if security_analysis['infrastructure_issues']:
        console.print("\n[bold]基礎設施問題:[/]")
        
        if compact:
            # 使用簡潔的列表格式
            for i, issue in enumerate(security_analysis['infrastructure_issues'], 1):
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                console.print(f"[{severity_style}]{i}. {issue.get('type')}[/]: {format_description(issue.get('description', ''))}")
                if 'file' in issue and issue['file']:
                    console.print(f"   文件: {shorten_path(issue.get('file', ''))}")
                console.print("")
        else:
            infra_table = Table(show_header=True, header_style="bold", expand=True)
            infra_table.add_column("嚴重性", style="red", width=8)
            infra_table.add_column("問題類型", style="cyan", width=25)
            infra_table.add_column("描述", style="yellow", width=50, overflow="fold")
            
            for issue in security_analysis['infrastructure_issues']:
                severity = issue.get("severity", "medium")
                severity_style = "red" if severity == "high" else "yellow" if severity == "medium" else "green"
                
                infra_table.add_row(
                    f"[{severity_style}]{severity}[/]",
                    issue.get("type", ""),
                    issue.get("description", "")
                )
            
            console.print(infra_table)
    
    # 如果沒有任何問題，顯示祝賀訊息
    if (not security_analysis['auth_issues'] and 
        not security_analysis['input_validation_issues'] and 
        not security_analysis['data_exposure_issues'] and 
        not security_analysis['infrastructure_issues']):
        console.print("\n[bold green]恭喜！未發現安全問題。[/]")
    
    # 顯示修復建議
    if any([security_analysis['auth_issues'], 
            security_analysis['input_validation_issues'],
            security_analysis['data_exposure_issues'],
            security_analysis['infrastructure_issues']]):
        
        console.print("\n[bold]修復建議:[/]")
        
        # 根據問題類型顯示修復建議
        suggestions = []
        
        if any(issue.get('type') == 'hardcoded_secret' for issue in security_analysis['auth_issues']):
            suggestions.append(("高優先級", "避免在代碼中硬編碼機密信息", "使用環境變量或專用的配置管理系統來儲存機密信息"))
            
        if any(issue.get('type') == 'insecure_setting' for issue in security_analysis['auth_issues']):
            suggestions.append(("高優先級", "不安全的設定", "在生產環境中禁用調試模式、啟用HTTPS強制等安全設置"))
            
        if any('missing_security_headers' in issue.get('type', '') for issue in security_analysis['data_exposure_issues']):
            suggestions.append(("中優先級", "缺少安全標頭", "添加關鍵的HTTP安全標頭，如X-Content-Type-Options、X-Frame-Options等"))
            
        if any('missing_rate_limiting' in issue.get('type', '') for issue in security_analysis['infrastructure_issues']):
            suggestions.append(("中優先級", "缺少速率限制", "實施API速率限制以防止濫用和拒絕服務攻擊"))
        
        # 顯示修復建議
        suggestions_table = Table(show_header=True, header_style="bold", expand=True)
        suggestions_table.add_column("優先級", style="red", width=12)
        suggestions_table.add_column("問題", style="yellow", width=25)
        suggestions_table.add_column("建議解決方案", style="green", width=50, overflow="fold")
        
        for priority, issue, suggestion in suggestions:
            suggestions_table.add_row(priority, issue, suggestion)
        
        console.print(suggestions_table)
    
    # 如果請求生成安全測試
    if generate_tests:
        console.print("\n[bold]正在生成安全測試腳本...[/]")
        from api_testing.security_test_generator import SecurityTestGenerator
        
        security_test_generator = SecurityTestGenerator(path, framework)
        test_results = security_test_generator.generate_security_tests()
        
        if test_results:
            console.print(f"[green]安全測試腳本已生成至 {os.path.relpath(os.path.dirname(test_results['auth_tests']), path)}[/]")
            console.print("生成的測試腳本包括:")
            console.print(f"• 身份驗證測試: {os.path.basename(test_results['auth_tests'])}")
            console.print(f"• 注入攻擊測試: {os.path.basename(test_results['injection_tests'])}")
            console.print(f"• 訪問控制測試: {os.path.basename(test_results['access_control_tests'])}")
            console.print(f"• 配置測試: {os.path.basename(test_results['config_tests'])}")
        else:
            console.print("[yellow]無法生成安全測試腳本。[/]")
    
    # 輸出報告到文件
    if output:
        console.print(f"\n[bold]正在生成安全報告至 {output}...[/]")
        
        # 生成詳細報告
        report = security_enhancer.generate_security_report(security_analysis)
        
        # 寫入報告
        with open(output, 'w', encoding='utf-8') as f:
            f.write(report)
        
        console.print(f"[green]安全報告已保存至 {output}[/]")
    
    # 提示用戶可以使用輸出選項獲取完整報告
    if not output:
        console.print("\n提示: 要查看完整的安全報告，請使用 --output 選項，例如:")
        console.print(f"[cyan]python3 main.py api-security {path} --output security-report.md[/]")
    
    # 提示用戶更詳細的查看選項
    if not verbose:
        console.print("\n提示: 要查看更詳細的問題信息，請使用 --verbose 選項")
    if not compact:
        console.print("\n提示: 要使用更緊湊的列表視圖而非表格，請使用 --compact 選項")
            
if __name__ == "__main__":
    app()