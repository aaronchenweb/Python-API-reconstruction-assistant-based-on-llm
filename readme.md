# 基於大型語言模型 Python API 重構助手使用手冊

## 概述

基於大型語言模型 Python API 重構助手是一個強大的命令行工具，它與大型語言模型集成，幫助您分析、重構和優化您的 Python 代碼。該工具提供了多種功能，包括：

- 代碼分析和指標計算
- 設計模式檢測和實施指導
- AI 驅動的重構建議
- 性能分析和優化
- 文檔生成
- API 分析和安全評估

## 目錄

- [安裝](#安裝)
- [入門](#入門)
- [基本命令](#基本命令)
  - [analyze-file](#analyze-file)
  - [analyze](#analyze)
  - [refactor](#refactor)
- [設計模式命令](#設計模式命令)
  - [patterns](#patterns)
  - [pattern-guide](#pattern-guide)
  - [pattern-diagram](#pattern-diagram)
- [性能命令](#性能命令)
  - [analyze-performance](#analyze-performance)
- [文檔命令](#文檔命令)
  - [generate-docs](#generate-docs)
- [API 分析命令](#api-分析命令)
  - [analyze-api](#analyze-api)
  - [api-patterns](#api-patterns)
  - [generate-openapi](#generate-openapi)
  - [api-security](#api-security)

## 安裝

```bash
# 克隆倉庫
git clone https://github.com/your-username/Python-API-reconstruction-assistant-based-on-llm.git

# 進入項目目錄
cd Python-API-reconstruction-assistant-based-on-llm

# 安裝依賴
pip install -r requirements.txt
```

## 入門

Python 重構助手需要 API 密鑰才能訪問語言模型服務。您可以通過幾種方式設置 API 密鑰：

1. 環境變量：

```bash
export LLM_API_KEY=your_api_key_here
```

2. 命令行選項：

```bash
python3 main.py --llm-api-key your_api_key_here
```

3. 配置文件：
   在項目目錄中創建一個 `config.json` 文件，結構如下：

```json
{
  "llm_api_key": "your_api_key_here",
  "llm_provider": "openai",
  "llm_model": "gpt-4"
}
```

## 基本命令

### analyze-file

分析單個 Python 文件並生成帶有建議的報告。

```bash
python3 main.py analyze-file path/to/your/file.py [選項]
```

**選項：**

- `--output`, `-o`：指定分析報告的輸出文件路徑
- `--verbose`, `-v`：在分析過程中顯示詳細信息

**示例：**

```bash
python3 main.py analyze-file myproject/main.py -o analysis_report.md
```

此命令將：

1. 讀取指定的 Python 文件
2. 分析代碼結構
3. 計算代碼指標
4. 使用語言模型提供建議
5. 生成包含原始代碼和分析結果的綜合報告

### analyze

分析一個或多個 Python 文件以識別重構機會。

```bash
python3 main.py analyze path/to/analyze [選項]
```

**選項：**

- `--metrics`：計算代碼指標（默認：True）
- `--patterns`：檢測設計模式（默認：True）
- `--suggestions`：生成重構建議（默認：True）

**示例：**

```bash
python3 main.py analyze myproject/
```

此命令將：

1. 掃描指定目錄中的 Python 文件
2. 對每個文件計算複雜度、代碼行數等指標
3. 檢測已實現的設計模式
4. 根據最佳實踐生成重構建議

### refactor

分析 Python 文件並生成重構建議，可選擇應用這些建議。

```bash
python3 main.py refactor path/to/file.py [選項]
```

**選項：**

- `--llm`：使用 LLM 進行更深入的分析和建議（默認：True）
- `--backup`：在應用更改前創建備份（默認：True）
- `--preview`：在應用更改前預覽更改（默認：True）
- `--apply`：自動提示應用建議（默認：False）
- `--verbose`, `-v`：顯示詳細錯誤信息

**示例：**

```bash
python3 main.py refactor myproject/complex_file.py --apply
```

此命令將：

1. 分析文件尋找重構機會
2. 生成基於規則和 AI 驅動的建議
3. 顯示所有建議的列表
4. 如果指定了 `--apply`，提示您選擇並應用建議
5. 在應用更改前創建備份並預覽更改

## 設計模式命令

### patterns

列出所有支持的設計模式，並提供何時應用每種模式的指導。

```bash
python3 main.py patterns [選項]
```

**選項：**

- `--detail`, `-d`：顯示每種模式的詳細信息
- `--compare`, `-c`：比較不同模式的適用場景
- `--pattern`, `-p`：指定要詳細查看的特定模式

**示例：**

```bash
python3 main.py patterns --pattern singleton
```

此命令將顯示設計模式的信息，包括描述、優點和何時使用。

### pattern-guide

提供選擇適當設計模式的綜合指南。

```bash
python3 main.py pattern-guide
```

此命令顯示：

1. 模式分類（創建型、結構型、行為型）
2. 常見問題及其匹配的設計模式解決方案
3. 幫助選擇正確模式的決策樹

### pattern-diagram

顯示特定設計模式的結構圖和流程解釋。

```bash
python3 main.py pattern-diagram 模式名稱
```

**示例：**

```bash
python3 main.py pattern-diagram observer
```

此命令將顯示：

1. 模式結構的 ASCII 藝術圖
2. 逐步流程解釋
3. 常見應用場景

## 性能命令

### analyze-performance

分析 Python 文件的性能問題並建議優化。

```bash
python3 main.py analyze-performance path/to/file.py [選項]
```

**選項：**

- `--output`, `-o`：指定分析結果的輸出文件路徑
- `--optimize`：生成代碼的優化版本

**示例：**

```bash
python3 main.py analyze-performance myproject/slow_module.py --optimize
```

此命令將：

1. 分析文件中的性能瓶頸
2. 顯示性能指標和問題
3. 如果指定了 `--optimize`，生成代碼的優化版本

## 文檔命令

### generate-docs

為 Python 代碼生成 API 文檔。

```bash
python3 main.py generate-docs path/to/code [選項]
```

**選項：**

- `--output-dir`：指定文檔的輸出目錄（默認："docs"）
- `--check-consistency`：檢查代碼和文檔之間的一致性（默認：True）

**示例：**

```bash
python3 main.py generate-docs myproject/ --output-dir documentation
```

此命令將：

1. 分析代碼結構
2. 生成 Markdown 文檔
3. 如果請求，檢查代碼和文檔之間的一致性

## API 分析命令

### analyze-api

分析 Python Web API 項目以識別重構機會。

```bash
python3 main.py analyze-api path/to/api_project [選項]
```

**選項：**

- `--framework`：指定框架（django, flask, fastapi）
- `--endpoints-only`：僅分析 API 端點
- `--security-focus`：專注於安全分析
- `--generate-tests`：生成 API 測試

**示例：**

```bash
python3 main.py analyze-api my_api_project/ --framework flask --security-focus
```

此命令將：

1. 如果未指定，檢測 API 框架
2. 分析 API 端點和數據模型
3. 如果請求，執行安全分析
4. 評估 RESTful 設計合規性

### api-patterns

列出常見的 API 設計模式和最佳實踐。

```bash
python3 main.py api-patterns [選項]
```

### generate-openapi

從您的 API 代碼生成或更新 OpenAPI 規範。

```bash
python3 main.py generate-openapi path/to/api_project [選項]
```

**選項：**

- `--output`：OpenAPI 規範的輸出文件（默認："openapi.json"）
- `--title`：API 標題（默認："API Documentation"）
- `--version`：API 版本（默認："1.0.0"）
- `--description`：API 描述

**示例：**

```bash
python3 main.py generate-openapi my_api_project/ --output api_spec.json --title "My Amazing API"
```

此命令將：

1. 分析您的 API 項目
2. 提取端點和數據模型
3. 生成完整的 OpenAPI 規範

### api-security

分析 API 安全問題並生成修復建議。

```bash
python3 main.py api-security path/to/api_project [選項]
```

**選項：**

- `--output`：安全報告的輸出文件
- `--compact`, `-c`：使用緊湊顯示模式
- `--verbose`, `-v`：顯示包括文件路徑在內的完整詳情

**示例：**

```bash
python3 main.py api-security my_api_project/ --output security_report.md --generate-tests
```

此命令將：

1. 分析您的 API 的安全漏洞
2. 按類型分類問題（身份驗證、輸入驗證、數據洩露等）
3. 提供修復建議
4. 如果請求，生成安全測試腳本

## 高級用法

### 使用項目配置

您可以使用配置文件自定義工具的行為：

```bash
python3 main.py --config-path custom_config.json analyze myproject/
```

### LLM 提供商選擇

您可以選擇不同的 LLM 提供商：

```bash
python3 main.py --llm-provider anthropic analyze-file myproject/main.py
```

支持的提供商包括：

- openai
- anthropic
- gemini

## 故障排除

如果遇到問題，嘗試使用 `--verbose` 標誌獲取更詳細的錯誤信息：

```bash
python3 main.py --verbose analyze myproject/
```

對於 API 相關命令，確保您的 API 密鑰正確設置並具有必要的權限。

## 後續步驟

- 探索 [patterns](#patterns) 命令以了解設計模式
- 在小文件上嘗試 [refactor](#refactor) 以查看 AI 驅動的建議
- 使用 [analyze-performance](#analyze-performance) 來識別代碼中的瓶頸
