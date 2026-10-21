# 錯誤回報模板範本 (`1-bug-report.yml`)

目標路徑：`.github/ISSUE_TEMPLATE/1-bug-report.yml`

---

## 1. 標準通用版（Web / 前端 / 函式庫 / 大型系統）

```yaml
name: 🐛 錯誤回報 (Bug Report)
description: 回報非預期的錯誤行為、崩潰或功能異常（僅需填寫 2 項核心資訊）
title: "[Bug]: "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：為節省寶貴時間，本表單僅要求填寫 **2 個必填欄位**。送出前請先透過上方搜尋欄確認是否已有相同回報。

  - type: textarea
    id: what-happened
    attributes:
      label: 問題現象與預期行為 (What happened & Expected behavior)
      description: 請簡述實際發生的錯誤現象，以及原本預期應該出現的正確行為（可直接貼上截圖）。
      placeholder: |
        實際現象：當傳入空陣列時，程式拋出 TypeError 崩潰。
        預期行為：應回傳預設的空物件 `{}` 而不應中斷執行。
    validations:
      required: true

  - type: textarea
    id: repro
    attributes:
      label: 最小重現方式 (Minimal Reproduction)
      description: 請提供以下任一方式協助重現：(1) 幾行可重現的程式碼片段/指令、(2) 簡要操作步驟 1-2-3、或 (3) 線上沙盒 / 最小 Repo 連結。
      placeholder: |
        1. 執行 `my-tool init --empty`
        2. 執行 `my-tool run`
        或直接貼上可重現的最小程式碼片段：
        import { run } from 'my-tool';
        run([]);
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: 錯誤輸出與堆疊日誌 (Error Output / Stack Trace)
      description: 若有終端機或 Console 錯誤訊息，請直接貼上（系統將自動包裹代碼區塊，無須手動加反引號）。
      placeholder: 請貼上錯誤訊息或 Stack Trace...
      render: text
    validations:
      required: false

  - type: input
    id: version
    attributes:
      label: 軟體與環境版本 (Version & Environment)
      description: 請填入套件版本、執行環境與作業系統（例如 `my-tool --version` 輸出）。
      placeholder: "例如：v1.2.0 / Node.js 22.12.0 / macOS 15.2 (或 Windows 11)"
    validations:
      required: false

  - type: dropdown
    id: area
    attributes:
      label: 受影響的模組區域 (Affected Area)
      description: 若知道問題所屬子系統請協助選擇以加速分流；若不確定請保留預設值。
      options:
        - 不確定 / 通用 (Not sure)
        - 核心引擎 (Core / Runtime)
        - 命令列工具 (CLI / Tooling)
        - 介面與元件 (UI / Components)
        - 建置與設定 (Build / Config)
        - 文件與型別 (Docs / Types)
      default: 0
    validations:
      required: false
```

---

## 2. CLI / 靜態工具極簡內嵌版（CLI / Linter / 編譯器）

適用於命令列工具、套件管理器、編譯器與靜態分析器（如 Ruff、uv、esbuild）：

```yaml
name: 🐛 錯誤回報 (CLI / Tooling Bug Report)
description: 回報命令列工具、解析器或編譯輸出的異常（極簡內嵌重現模式）
title: "[Bug]: "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：無須建立外部 Repo，請直接將觸發錯誤的指令、代碼片段與設定檔貼在下方文字框中。

  - type: textarea
    id: what-happened
    attributes:
      label: 錯誤現象與預期行為 (What happened & Expected behavior)
      description: 請簡述執行的命令、實際出現的非預期輸出，以及原本預期的輸出結果。
    validations:
      required: true

  - type: textarea
    id: repro
    attributes:
      label: 觸發錯誤的最小代碼或指令 (Minimal Reproduction Snippet / Command)
      description: 請貼上可直接重現問題的最簡短指令與輸入程式碼片段。
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: 終端機錯誤輸出 (Terminal Output / Backtrace)
      description: 請貼上完整的錯誤訊息或 stack backtrace（系統自動包裹代碼塊）。
      render: text
    validations:
      required: false

  - type: textarea
    id: config-file
    attributes:
      label: 相關設定檔段落 (Relevant Configuration)
      description: 若問題與設定檔相關，請貼上對應段落（系統自動包裹代碼塊）。
      render: toml
    validations:
      required: false

  - type: input
    id: version
    attributes:
      label: 工具與系統版本 (CLI & OS Version)
      description: 請貼上 `<tool> --version` 輸出與作業系統。
      placeholder: "例如：0.4.15 (Windows 11 x86_64)"
    validations:
      required: false
```

### 設定檔欄位 (`config-file`) 之 `render` 語法對照

| 專案主要設定檔 | `render` 值 |
|---|---|
| `pyproject.toml`, `Cargo.toml`, `mise.toml` | `toml` |
| `package.json`, `tsconfig.json`, `deno.json` | `json` |
| `*.yml`, `*.yaml` | `yaml` |
| 多格式並存或純文字設定 | `text` |

---

## 3. 中英雙語欄位對照（English Mode）

| 欄位 `id` / 項目 | 繁體中文 (預設) | English |
|---|---|---|
| `name` | `🐛 錯誤回報 (Bug Report)` | `🐛 Bug Report` |
| `description` | `回報非預期的錯誤行為、崩潰或功能異常（僅需填寫 2 項核心資訊）` | `Report unexpected behavior, crashes, or regressions (only 2 required fields)` |
| `what-happened` label | `問題現象與預期行為 (What happened & Expected behavior)` | `What happened & Expected behavior` |
| `repro` label (通用) | `最小重現方式 (Minimal Reproduction)` | `Minimal Reproduction` |
| `repro` label (CLI) | `觸發錯誤的最小代碼或指令 (Minimal Reproduction Snippet / Command)` | `Minimal Reproduction Snippet / Command` |
| `logs` label | `錯誤輸出與堆疊日誌 (Error Output / Stack Trace)` | `Error Output / Stack Trace` |
| `config-file` label | `相關設定檔段落 (Relevant Configuration)` | `Relevant Configuration` |
| `version` label | `軟體與環境版本 (Version & Environment)` | `Version & Environment` |
| `area` label | `受影響的模組區域 (Affected Area)` | `Affected Area` |
| `area` 首項預設值 | `不確定 / 通用 (Not sure)` | `Not sure / General` |
