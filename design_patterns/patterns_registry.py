"""
用於儲存設計模式資訊並提供重構建議的模組。
"""
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
console = Console()

class PatternInfo:
    """設計模式的相關資訊。"""
    
    def __init__(self, 
                 name: str, 
                 description: str, 
                 benefits: List[str], 
                 drawbacks: List[str], 
                 implementation_tips: List[str],
                 refactoring_tips: List[str],
                 example: str):
        self.name = name
        self.description = description
        self.benefits = benefits
        self.drawbacks = drawbacks
        self.implementation_tips = implementation_tips
        self.refactoring_tips = refactoring_tips
        self.example = example

class PatternsRegistry:
    """包含設計模式資訊和重構建議的註冊表。"""
    
    def __init__(self):
        self._patterns: Dict[str, PatternInfo] = {}
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """使用常見設計模式初始化註冊表。"""
        # 單例模式
        self._patterns["singleton"] = PatternInfo(
            name="Singleton",
            description="確保一個 class 只有一個 instance，並提供一個 global point。",
            benefits=[
                "對唯一實例的受控訪問",
                "減少命名空間污染",
                "允許優化操作和表示",
                "允許變量數量的 instances",
                "比 class 操作更靈活"
            ],
            drawbacks=[
                "使單元測試變得困難",
                "在應用程序中引入全局狀態",
                "如果未正確實現，可能導致線程安全問題"
            ],
            implementation_tips=[
                "考慮使用 class 方法來處理 instance creation",
                "使構造函數為私有或受保護",
                "在多線程應用程序中考慮線程安全",
                "考慮 lazy initialization 以提高資源效率"
            ],
            refactoring_tips=[
                "考慮 Singleton 是否真正必要 - 是否可以使用依賴注入代替？",
                "通過使用適當的同步機制確保線程安全",
                "Consider using a metaclass for more elegant implementation",
                "確保正確處理序列化和反序列化"
            ],
            example="""
class Singleton:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    # 使用 class 方法的替代實現
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
"""
        )
        
        # Factory Method
        self._patterns["factory_method"] = PatternInfo(
            name="Factory Method",
            description="定義一個用於建立對象的interface，但讓sub class 決定實例化哪個 class 。",
            benefits=[
                "消除將特定於應用程序的 class 綁定到程式碼中的需要",
                "通過繼承而非實例化建立對象",
                "連接平行 class 層次結構",
                "通過減少對具體 class 的依賴來促進鬆散耦合"
            ],
            drawbacks=[
                "可能導致許多小而相似的建立者 class ",
                "可能通過要求許多新sub class 來增加複雜性"
            ],
            implementation_tips=[
                "建立一個返回實現共同interface的對象的方法",
                "讓sub class 重寫Factory Method以更改生成的產品",
                "考慮提供Factory Method的默認實現",
                "使用Factory Method連接系統中需要一起工作的不同部分"
            ],
            refactoring_tips=[
                "將common factory code從具體建立者提取到base class 中",
                "考慮使用參數化Factory Method而不是多個專用方法",
                "使用配置文件或環境變量來確定要建立的產品",
                "考慮結合Abstract Factory pattern families of related objects"
            ],
            example="""
from abc import ABC, abstractmethod

class Product(ABC):
    @abstractmethod
    def operation(self):
        pass

class ConcreteProductA(Product):
    def operation(self):
        return "ConcreteProductA 的結果"

class ConcreteProductB(Product):
    def operation(self):
        return "ConcreteProductB 的結果"

class Creator(ABC):
    @abstractmethod
    def factory_method(self):
        pass
    
    def some_operation(self):
        product = self.factory_method()
        return f"建立者: {product.operation()}"

class ConcreteCreatorA(Creator):
    def factory_method(self):
        return ConcreteProductA()

class ConcreteCreatorB(Creator):
    def factory_method(self):
        return ConcreteProductB()
"""
        )
        
        # Observer
        self._patterns["observer"] = PatternInfo(
            name="Observer",
            description="定義對象之間的一對多依賴關係，使得當一個對象改變狀態時，所有依賴於它的對象都會得到通知並自動更新。",
            benefits=[
                "支持對象之間loose coupling的原則",
                "允許以便捷的方式向多個對象發送數據",
                "在運行時動態添加/移除對象之間的關係"
            ],
            drawbacks=[
                "訂閱者以隨機順序被通知",
                "如果不小心，可能會造成內存洩漏（如果主題保持對observers的強引用）",
                "擁有大量observers或頻繁更新時可能會導致性能問題"
            ],
            implementation_tips=[
                "為observers通知定義清晰的interface",
                "考慮使用對observers的弱引用以避免內存洩漏",
                "使用特定的更新方法來僅傳遞已更改的數據而不是整個狀態",
                "對於多線程應用程序考慮線程安全"
            ],
            refactoring_tips=[
                "將observers管理程式碼提取到可重用的base class 中",
                "對於簡單的情況，考慮使用事件或回調",
                "使用弱引用避免當observers可能被垃圾回收時的內存洩漏",
                "對於複雜的observers關係，考慮使用中介者模式"
            ],
            example="""
from abc import ABC, abstractmethod
from typing import List

class Observer(ABC):
    @abstractmethod
    def update(self, subject):
        pass

class Subject:
    def __init__(self):
        self._observers: List[Observer] = []
        self._state = None
    
    def attach(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach(self, observer: Observer):
        self._observers.remove(observer)
    
    def notify(self):
        for observer in self._observers:
            observer.update(self)
    
    @property
    def state(self):
        return self._state
    
    @state.setter
    def state(self, state):
        self._state = state
        self.notify()

class ConcreteObserver(Observer):
    def update(self, subject):
        print(f"observers: 對主題狀態變化為 {subject.state} 做出反應")
"""
        )
        
        # Strategy
        self._patterns["strategy"] = PatternInfo(
            name="Strategy",
            description="定義一系列算法，將每個算法封裝起來，並使它們可互換。",
            benefits=[
                "在單獨的 class 中封裝算法",
                "使在運行時輕鬆切換不同算法",
                "避免對不同算法變體使用條件語句",
                "遵循開閉原則：添加新策略無需更改現有程式碼"
            ],
            drawbacks=[
                "客戶端必須了解不同的策略",
                "增加應用程序中的對象數量",
                "對於簡單的算法變體可能過於複雜"
            ],
            implementation_tips=[
                "定義可互換使用的算法族",
                "將每個算法封裝在實現共同interface的單獨 class 中",
                "使上下文 class 在其構造函數或通過設置器接受策略",
                "對於簡單的策略，考慮使用lambda函數或簡單方法"
            ],
            refactoring_tips=[
                "用策略對象替換條件邏輯（if/else或switch）",
                "將策略實現之間的共同程式碼提取到基 class 中",
                "對於簡單的策略，考慮使用簡單的函數而不是 class ",
                "使用工廠來根據上下文實例化適當的策略"
            ],
            example="""
from abc import ABC, abstractmethod

class Strategy(ABC):
    @abstractmethod
    def execute(self, data):
        pass

class ConcreteStrategyA(Strategy):
    def execute(self, data):
        return sorted(data)  # 升序排序

class ConcreteStrategyB(Strategy):
    def execute(self, data):
        return sorted(data, reverse=True)  # 降序排序

class Context:
    def __init__(self, strategy: Strategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: Strategy):
        self._strategy = strategy
    
    def execute_strategy(self, data):
        return self._strategy.execute(data)

# 使用方式
context = Context(ConcreteStrategyA())
result = context.execute_strategy([3, 1, 4, 2])  # [1, 2, 3, 4]

context.set_strategy(ConcreteStrategyB())
result = context.execute_strategy([3, 1, 4, 2])  # [4, 3, 2, 1]
"""
        )
        
        # Decorator
        self._patterns["decorator"] = PatternInfo(
            name="Decorator",
            description="動態地給對象添加額外的職責，為擴展功能提供比sub class 化更靈活的選擇。",
            benefits=[
                "比繼承更靈活地擴展功能",
                "允許在運行時添加/移除職責",
                "避免在層次結構高處的功能豐富的 classes",
                "遵循單一職責原則，分離關注點"
            ],
            drawbacks=[
                "可能導致許多看起來相似的 small objects",
                "對不熟悉該模式的開發人員可能造成混淆",
                "從 class 型角度看，裝飾器及其組件並不相同"
            ],
            implementation_tips=[
                "確保組件和裝飾器共享一個公共interface",
                "裝飾器應該聚合組件並將操作委派給它",
                "保持裝飾器簡單，專注於單一職責",
                "考慮使用多個裝飾器組合不同功能"
            ],
            refactoring_tips=[
                "將通用裝飾器功能提取到基礎裝飾器 class 中",
                "對於函數裝飾，考慮使用Python的內置裝飾器語法",
                "當應用多個裝飾器時要注意順序",
                "考慮使用建造者模式構建裝飾對象"
            ],
            example="""
from abc import ABC, abstractmethod

class Component(ABC):
    @abstractmethod
    def operation(self):
        pass

class ConcreteComponent(Component):
    def operation(self):
        return "具體組件"

class Decorator(Component):
    def __init__(self, component: Component):
        self._component = component
    
    @abstractmethod
    def operation(self):
        pass

class ConcreteDecoratorA(Decorator):
    def operation(self):
        return f"具體裝飾器A({self._component.operation()})"

class ConcreteDecoratorB(Decorator):
    def operation(self):
        return f"具體裝飾器B({self._component.operation()})"

# 使用方式
component = ConcreteComponent()
decorator1 = ConcreteDecoratorA(component)
decorator2 = ConcreteDecoratorB(decorator1)
result = decorator2.operation()  # "具體裝飾器B(具體裝飾器A(具體組件))"
"""
        )
        
        # Adapter
        self._patterns["adapter"] = PatternInfo(
            name="Adapter",
            description="將一個 class 的interface轉換成客戶期望的另一個interface，使得原本由於interface不兼容而不能一起工作的 class 能夠共同工作。",
            benefits=[
                "允許interface不兼容的 class 一起工作",
                "促進現有程式碼的重用性",
                "將interface或數據轉換程式碼與核心業務邏輯分離",
                "引入一層間接性以促進靈活性"
            ],
            drawbacks=[
                "通過引入新 class 增加複雜性",
                "有時修改被適配者使其兼容更簡潔",
                "由於間接性可能引入性能開銷"
            ],
            implementation_tips=[
                "實現客戶端期望的目標interface",
                "在適配器中組合被適配者的實例",
                "將客戶端請求委派給被適配者，必要時進行轉換",
                "考慮在Python中使用多重繼承實現 class 適配器"
            ],
            refactoring_tips=[
                "在將現有系統與新程式碼集成時考慮適配器",
                "使用外部庫時建立可重用的適配器",
                "使用適配器統一不同實現間的interface",
                "對適配多個 class 考慮外觀模式"
            ],
example="""
class Target:
    # 客戶端使用的interface
    def request(self):
        return "目標: 默認行為。"

class Adaptee:
    # 具有不兼容interface的 class 
    def specific_request(self):
        return "被適配者: 特殊行為。"

class Adapter(Target):
    # 將被適配者轉換為目標interface
    def __init__(self, adaptee: Adaptee):
        self.adaptee = adaptee
    
    def request(self):
        return f"適配器: 已轉換 {self.adaptee.specific_request()}"

# 使用方式
adaptee = Adaptee()
adapter = Adapter(adaptee)
result = adapter.request()  # "適配器: 已轉換 被適配者: 特殊行為。"
"""
        )
    
    def get_pattern(self, pattern_name: str) -> Optional[PatternInfo]:
        """
        獲取設計模式的資訊。
        
        Args:
            pattern_name: 模式名稱
            
        Returns:
            PatternInfo 對象，如果未找到模式則返回 None
        """
        return self._patterns.get(pattern_name.lower())
    
    def get_all_patterns(self) -> List[str]:
        """
        獲取所有已註冊模式的名稱。
        
        Returns:
            模式名稱列表
        """
        return list(self._patterns.keys())
    
    def get_refactoring_suggestions(self, pattern_name: str) -> List[str]:
        """
        獲取設計模式的重構建議。
        
        Args:
            pattern_name: 模式名稱
            
        Returns:
            重構建議列表，如果未找到模式則返回空列表
        """
        pattern = self.get_pattern(pattern_name)
        if pattern:
            return pattern.refactoring_tips
        return []

def show_pattern_details(patterns_registry: PatternsRegistry, pattern_name: str):
    """顯示模式的詳細資訊，改進格式以更好地顯示"""
    pattern_info = patterns_registry.get_pattern(pattern_name)
    if not pattern_info:
        console.print(f"[bold red]錯誤:[/] 未找到名為 '{pattern_name}' 的模式。")
        return
    
    # 使用面板顯示基本信息
    console.print(Panel.fit(
        f"[bold]{pattern_info.name}[/]\n\n{pattern_info.description}",
        title="模式概述",
        border_style="cyan",
        width=80
    ))
    
    # 創建格式良好的部分
    sections = [
        ("優點", pattern_info.benefits, "green", "✓"),
        ("缺點", pattern_info.drawbacks, "red", "⚠"),
        ("實現提示", pattern_info.implementation_tips, "blue", "→"),
        ("重構提示", pattern_info.refactoring_tips, "magenta", "↻")
    ]
    
    # 顯示適用場景
    console.print("\n[bold yellow]適用場景:[/]")
    applicability = get_pattern_applicability(pattern_info)
    # 分點顯示適用場景
    for point in applicability.split("；"):
        if point.strip():
            console.print(f"• {point.strip()}")
    
    # 顯示各部分信息
    for title, items, color, bullet in sections:
        console.print(f"\n[bold {color}]{title}:[/]")
        for item in items:
            console.print(f"{bullet} {item}")
    
    # 使用語法高亮顯示代碼範例
    console.print("\n[bold cyan]程式碼範例:[/]")
    example_code = pattern_info.example.strip()
    console.print(Syntax(example_code, "python", theme="monokai", line_numbers=True))
    
    # 添加相關模式信息（如果有的話）
    related_patterns = get_related_patterns(pattern_info.name)
    if related_patterns:
        console.print("\n[bold yellow]相關模式:[/]")
        for related, relation in related_patterns.items():
            console.print(f"• [bold]{related}[/] - {relation}")

def get_pattern_applicability(pattern_info: PatternInfo) -> str:
    """從模式資訊中提取適用場景描述，更詳細的版本"""
    applicability = ""
    
    # 根據模式名稱提供特定的適用場景描述
    if pattern_info.name == "Singleton":
        applicability = "需要確保整個應用程序中只有一個共享實例時；需要懶加載資源密集型對象時；需要集中管理狀態或配置時；需要協調共享資源的訪問時；當全局變量需要更多控制時。"
    elif pattern_info.name == "Factory Method":
        applicability = "當不知道創建的對象的具體類型時；當類的創建邏輯應該與使用邏輯分離時；當擴展產品類型時不希望修改現有代碼；當您需要重用現有對象而不是創建新對象時；當創建過程涉及複雜的步驟時。"
    elif pattern_info.name == "Observer":
        applicability = "當對象狀態改變需要通知多個其他對象時；當一個對象的變化要觸發一系列其他對象的變化時；實現發布/訂閱模型時；當需要在運行時動態地建立對象間的關係時；圖形用戶界面中的事件處理時。"
    elif pattern_info.name == "Strategy":
        applicability = "當需要使用不同算法的變體時；避免大量條件語句時；當算法的細節應該對客戶端隱藏時；運行時動態選擇算法時；當類具有大量行為導致條件語句複雜時；當基於上下文需要切換行為時。"
    elif pattern_info.name == "Decorator":
        applicability = "動態添加功能到對象而不改變其結構時；需要在運行時添加和移除對象職責時；使用繼承會導致類爆炸時；需要擴展封閉類的功能時；當需要靈活地擴展功能而不影響其他對象時。"
    elif pattern_info.name == "Adapter":
        applicability = "使用具有不兼容接口的現有類時；需要在不修改原始代碼的情況下適配現有類時；集成第三方庫或遺留系統時；需要重用現有類但接口不符合需求時；當您正在創建可重用的類，該類可能與未知或將來的類協作時。"
    else:
        # 通用適用場景，基於優點提取
        applicability = "；".join(pattern_info.benefits[:3])
    
    return applicability

def get_related_patterns(pattern_name: str) -> Dict[str, str]:
    """獲取與特定模式相關的其他模式"""
    relations = {
        "Singleton": {
            "Factory Method": "工廠可以使用單例來管理創建的對象",
            "Builder": "建造者可以使用單例來管理建造過程"
        },
        "Factory Method": {
            "Abstract Factory": "抽象工廠經常使用工廠方法來實現",
            "Template Method": "工廠方法是模板方法的一種特殊形式",
            "Prototype": "工廠方法可以使用原型來創建對象"
        },
        "Observer": {
            "Mediator": "中介者經常作為觀察者模式的替代方案",
            "Strategy": "當策略需要了解上下文變化時可使用觀察者"
        },
        "Strategy": {
            "Command": "命令模式可視為策略模式的一種特殊形式",
            "State": "狀態模式和策略模式在結構上相似但目的不同"
        },
        "Decorator": {
            "Composite": "裝飾器可視為僅有一個組件的複合模式",
            "Strategy": "裝飾器可以使用不同的策略改變行為",
            "Chain of Responsibility": "兩者都通過組合對象工作"
        },
        "Adapter": {
            "Bridge": "橋接模式是預先設計的，而適配器是事後解決方案",
            "Decorator": "裝飾器增加功能，適配器改變接口",
            "Proxy": "代理使用相同接口，適配器改變接口"
        }
    }
    
    return relations.get(pattern_name, {})

def show_patterns_comparison(patterns_registry: PatternsRegistry, all_patterns: List[str]):
    """比較不同模式的適用場景和優缺點，使用更友好的格式顯示"""
    console.print(Panel.fit(
        "設計模式比較：幫助您選擇最適合的模式",
        title="比較",
        border_style="green"
    ))
    
    # 定義模式的替代方案
    alternatives = {
        "singleton": "依賴注入、靜態類、全局變量",
        "factory_method": "抽象工廠、建造者模式、原型模式",
        "observer": "事件系統、回調函數、中介者模式",
        "strategy": "命令模式、模板方法、函數作為參數",
        "decorator": "複合模式、子類化、代理模式",
        "adapter": "橋接模式、外觀模式、直接修改不兼容類"
    }
    
    # 使用分類顯示模式比較
    categories = {
        "創建型模式": ["singleton", "factory_method"],
        "結構型模式": ["adapter", "decorator"],
        "行為型模式": ["observer", "strategy"]
    }
    
    # 依次顯示每個分類的模式
    for category, patterns in categories.items():
        console.print(f"\n[bold]{category}[/]")
        
        # 只顯示在註冊表中的模式
        available_patterns = [p for p in patterns if p in [p.lower() for p in all_patterns]]
        
        for pattern_name in available_patterns:
            pattern_info = patterns_registry.get_pattern(pattern_name)
            if not pattern_info:
                continue
                
            # 創建包含所有信息的面板
            pattern_panel = Panel(
                f"[bold cyan]主要用途:[/]\n{get_pattern_applicability(pattern_info)}\n\n"
                f"[bold green]優點:[/]\n" + "\n".join([f"• {benefit}" for benefit in pattern_info.benefits[:3]]) + "\n\n"
                f"[bold red]缺點:[/]\n" + "\n".join([f"• {drawback}" for drawback in pattern_info.drawbacks[:3]]) + "\n\n"
                f"[bold magenta]替代方案:[/]\n{alternatives.get(pattern_name.lower(), '無特定替代方案')}",
                title=f"[bold]{pattern_info.name}[/]",
                border_style="blue",
                width=80,
                padding=(1, 2)
            )
            console.print(pattern_panel)
    
    # 添加一個選擇提示
    console.print("\n[bold]提示:[/] 使用 [cyan]patterns -p <pattern_name>[/] 查看特定模式的完整詳情")
    
    # 設計模式選擇指南
    console.print("\n[bold]設計模式選擇指南:[/]")
    console.print("""
[bold]設計模式應該基於您的具體問題選擇:[/]

1. [bold cyan]創建型模式[/] - 當您關注對象的創建方式時
   • Singleton: 整個系統需要一個全局訪問點
   • Factory Method: 創建對象的類型應該由子類決定

2. [bold blue]結構型模式[/] - 當您關注類和對象的組合時
   • Adapter: 使不兼容的接口能夠一起工作
   • Decorator: 動態地向對象添加責任

3. [bold green]行為型模式[/] - 當您關注對象間的通信方式時
   • Observer: 當一個對象變化時需要自動通知其他對象
   • Strategy: 定義一系列算法並使其可互換
    """)
