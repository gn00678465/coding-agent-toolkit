# 功能提案模板範本 (`2-feature-request.yml`)

目標路徑：`.github/ISSUE_TEMPLATE/2-feature-request.yml`

---

## 1. 痛點導向功能提案範本（繁體中文預設）

```yaml
name: ✨ 功能與強化提案 (Feature Request)
description: 提出新功能構想、API 體驗改良或效能強化建議
title: "[Feat]: "
labels: ["enhancement"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：優秀的功能提案始於清楚的「使用痛點」。若已有類似提案，對該 Issue 按下 👍 (Upvote) 比重複開單更能加速排程！

  - type: textarea
    id: problem
    attributes:
      label: 使用情境與目前痛點 (Use Case & Current Friction)
      description: 請說明這項功能是為了解決什麼實際場景的問題？目前的限制或痛點為何？
      placeholder: "目前在處理批次檔案時，API 僅支援同步單檔讀取，導致必須自行維護外部佇列..."
    validations:
      required: true

  - type: textarea
    id: proposal
    attributes:
      label: 期望的解決方案或 API 設計 (Proposed Solution)
      description: 希望新增什麼樣的功能、設定選項或理想中的呼叫介面？
      placeholder: |
        希望能新增 `batchProcess(files, { concurrency: 4 })` 選項，或支援 AsyncIterable。
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: 替代方案與現有解法 (Alternatives & Workarounds)
      description: 目前是否有暫時的繞道解法（Workaround）？其他類似工具有無可參考的設計？
      placeholder: "目前暫時透過第三方套件封裝處理；可參考某專案的設計..."
    validations:
      required: false

  - type: dropdown
    id: contribution
    attributes:
      label: 貢獻意願 (Willingness to Contribute)
      description: 若維護團隊認可此提案方向，是否有意願協助提交 Pull Request 實作？
      options:
        - 需要維護團隊或社群協助實作
        - 願意在維護者指引下嘗試提交 PR
        - 已準備好實作並可立即提交 PR
      default: 0
    validations:
      required: false
```

---

## 2. 中英雙語欄位對照（English Mode）

| 欄位 `id` / 項目 | 繁體中文 (預設) | English |
|---|---|---|
| `name` | `✨ 功能與強化提案 (Feature Request)` | `✨ Feature Request` |
| `description` | `提出新功能構想、API 體驗改良或效能強化建議` | `Suggest a new feature, API ergonomic improvement, or performance enhancement` |
| `problem` label | `使用情境與目前痛點 (Use Case & Current Friction)` | `Use Case & Current Friction` |
| `proposal` label | `期望的解決方案或 API 設計 (Proposed Solution)` | `Proposed Solution` |
| `alternatives` label | `替代方案與現有解法 (Alternatives & Workarounds)` | `Alternatives & Workarounds` |
| `contribution` label | `貢獻意願 (Willingness to Contribute)` | `Willingness to Contribute` |
| `contribution` options[0] | `需要維護團隊或社群協助實作` | `Need maintainer or community help to implement` |
| `contribution` options[1] | `願意在維護者指引下嘗試提交 PR` | `Willing to submit a PR with guidance` |
| `contribution` options[2] | `已準備好實作並可立即提交 PR` | `Ready to submit a PR immediately` |
