"""
用於管理 LLM 互動提示範本的模組。
"""
from typing import Dict, List, Any, Optional
import os
import json
import re

# Global template manager instance
_template_manager = None

class PromptTemplate:
    """A simple class for managing prompt templates."""
    
    def __init__(self, template_id: str, template_text: str, description: str = "", variables=None):
        self.id = template_id
        self.template_text = template_text
        self.description = description
        self.variables = variables or []
        
        # Extract variables from template if not provided
        if not self.variables:
            self.variables = re.findall(r'\{([^}]+)\}', template_text)
    
    def format(self, **kwargs) -> str:
        """Format the template with provided values."""
        return self.template_text.format(**kwargs)


class TemplateManager:
    """Simple template manager for storing and retrieving prompt templates."""
    
    def __init__(self, templates_dir: str = "prompt_templates"):
        self.templates_dir = templates_dir
        self.templates = {}
        self._load_templates()
        self._create_default_templates()
    
    def _load_templates(self):
        """Load templates from the directory if it exists."""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir, exist_ok=True)
            return
        
        # Try to load JSON template files
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(self.templates_dir, filename), 'r') as f:
                        data = json.load(f)
                        if 'id' in data and 'template_text' in data:
                            template = PromptTemplate(
                                data['id'], 
                                data['template_text'],
                                data.get('description', '')
                            )
                            self.templates[template.id] = template
                except Exception as e:
                    print(f"Error loading template from {filename}: {e}")
    
    def _create_default_templates(self):
        """Create default templates if they don't exist."""
        # Code analysis template
        if "code_analysis" not in self.templates:
            self.templates["code_analysis"] = PromptTemplate(
                "code_analysis",
                """作為一個Python代碼分析導師，我需要你分析以下Python代碼：

```python
{code}
```

代碼結構信息:
- 函數數量: {num_functions}
- 類數量: {num_classes}
- 導入庫: {imports}

請提供以下分析:
1. 代碼結構評估和可能的改進建議
2. 潛在的代碼質量問題或優化機會
3. 是否有明顯的設計模式，或者可以應用哪些設計模式來改進
4. 代碼風格和Python最佳實踐的遵循程度

請直接分析代碼本身，無需解釋代碼的功能。重點關注可以改進的地方，以及具體的重構建議。
""",
                "Template for Python code analysis"
            )
        
        # Error analysis template
        if "code_analysis_error" not in self.templates:
            self.templates["code_analysis_error"] = PromptTemplate(
                "code_analysis_error",
                """請分析這段有問題的Python代碼:

```python
{code}
```

在分析代碼時遇到了錯誤: {error}

請嘗試指出這個問題的可能原因，並建議如何修復。
""",
                "Template for analyzing code with errors"
            )
        
        # Add refactoring suggestions template
        if "refactoring_suggestions" not in self.templates:
            self.templates["refactoring_suggestions"] = PromptTemplate(
                "refactoring_suggestions",
                """Analyze the following Python code and provide refactoring suggestions based on the quality metrics and detected patterns.

Code:
```python
{code}
```

Quality Metrics:
{quality_metrics}

Quality Issues:
{quality_issues}

Detected Design Patterns:
{detected_patterns}

Please suggest specific refactorings to improve the code quality. For each suggestion, include:
1. The type of refactoring (e.g., Extract Method, Rename Variable, etc.)
2. The location in the code where it should be applied
3. A detailed description of the proposed change
4. Code example of how it might look after refactoring

Format your response as follows:

## Suggestion 1
### Type
(Type of refactoring)

### Description
(Description of the issue)

### Location
(Where to apply the refactoring)

### Recommendation
(Detailed explanation of the proposed change)

```python
# Example code after refactoring
```

Repeat for each suggestion.""",
                "Template for generating refactoring suggestions"
            )
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)


# Initialize global template manager
def init_template_manager(templates_dir: str = "prompt_templates"):
    """Initialize the global template manager."""
    global _template_manager
    _template_manager = TemplateManager(templates_dir)


# Get a template from the global manager
def get_template(template_id: str) -> Optional[PromptTemplate]:
    """Get a template by ID using the global template manager."""
    global _template_manager
    
    # Initialize if not already initialized
    if _template_manager is None:
        init_template_manager()
    
    return _template_manager.get_template(template_id)


# Get all templates from the global manager
def get_all_templates() -> Dict[str, PromptTemplate]:
    """Get all templates."""
    global _template_manager
    
    if _template_manager is None:
        init_template_manager()
    
    return _template_manager.templates.copy()


# Add a template to the global manager
def add_template(template: PromptTemplate) -> bool:
    """Add a template to the manager."""
    global _template_manager
    
    if _template_manager is None:
        init_template_manager()
    
    _template_manager.templates[template.id] = template
    return True


# Update a template in the global manager
def update_template(template: PromptTemplate) -> bool:
    """Update a template in the manager."""
    return add_template(template)


# Delete a template from the global manager
def delete_template(template_id: str) -> bool:
    """Delete a template from the manager."""
    global _template_manager
    
    if _template_manager is None:
        init_template_manager()
    
    if template_id in _template_manager.templates:
        del _template_manager.templates[template_id]
        return True
    return False


# Original function from Phase 1 (updated to use template manager)
def get_prompt_for_analysis(code: str, analysis_result: Dict[str, Any]) -> str:
    """
    生成代碼分析的提示
    
    Args:
        code: 原始代碼
        analysis_result: 代碼分析結果
        
    Returns:
        格式化的提示字符串
    """
    # 初始化模板管理器（如果尚未初始化）
    global _template_manager
    if _template_manager is None:
        init_template_manager()
    
    # 提取重要信息用於提示
    num_functions = analysis_result.get('num_functions', 0)
    num_classes = analysis_result.get('num_classes', 0)
    imports = analysis_result.get('imports', [])
    import_names = [imp.get('name') for imp in imports]
    
    # 檢查是否有錯誤
    if 'error' in analysis_result:
        # Use the error template if available, otherwise use the hardcoded template
        error_template = get_template("code_analysis_error")
        if error_template:
            return error_template.format(
                code=code,
                error=analysis_result['error']
            )
        
        return f"""
請分析這段有問題的Python代碼:

```python
{code}
```

在分析代碼時遇到了錯誤: {analysis_result['error']}

請嘗試指出這個問題的可能原因，並建議如何修復。
"""

    # Use the code analysis template if available, otherwise use the hardcoded template
    analysis_template = get_template("code_analysis")
    if analysis_template:
        return analysis_template.format(
            code=code,
            num_functions=num_functions,
            num_classes=num_classes,
            imports=', '.join(import_names) if import_names else '無'
        )
    
    # 構建正常代碼分析提示
    prompt = f"""
作為一個Python代碼分析導師，我需要你分析以下Python代碼：

```python
{code}
```

代碼結構信息:
- 函數數量: {num_functions}
- 類數量: {num_classes}
- 導入庫: {', '.join(import_names) if import_names else '無'}

請提供以下分析:
1. 代碼結構評估和可能的改進建議
2. 潛在的代碼質量問題或優化機會
3. 是否有明顯的設計模式，或者可以應用哪些設計模式來改進
4. 代碼風格和Python最佳實踐的遵循程度

請直接分析代碼本身，無需解釋代碼的功能。重點關注可以改進的地方，以及具體的重構建議。
"""
    return prompt