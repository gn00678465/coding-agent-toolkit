# 工程任務模板範本 (`4-task.yml`)

目標路徑：`.github/ISSUE_TEMPLATE/4-task.yml`

> 頂層 `labels`：GitHub 預設 9 個標籤（`bug`、`documentation`、`duplicate`、`enhancement`、`good first issue`、`help wanted`、`invalid`、`question`、`wontfix`）不含 `chore`／`task`，依 Step 1 的 `gh label list` 結果處理：
>
> - 已存在 `chore` 或 `task` → 直接掛載既有標籤（下方範本以 `chore` 為例）。
> - 兩者皆不存在 → 詢問使用者是否建立。同意則先執行 `gh label create chore --color FEF2C0 --description "工程任務、重構與維護"`（或請使用者於 Issues → Labels 手動新增），確認建立後再寫入 `labels: ["chore"]`；不同意則省略 `labels` 鍵。
> - 未建立就寫入的標籤會被 GitHub 靜默忽略，表單仍可正常開單，但 Issue 不會帶上該標籤。

---

## 1. 工程任務與檢查清單範本（繁體中文預設）

```yaml
name: 🛠 工程任務與維護 (Task / Chore)
description: 追蹤內部重構、技術債清理、CI/CD 維護或版本發佈檢查清單
title: "[Task]: "
labels: ["chore"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：用於追蹤工程重構、基礎設施調整或分階段待辦清單（可使用 `- [ ]` 語法建立子任務）。

  - type: textarea
    id: goal
    attributes:
      label: 任務目標與背景 (Task Goal & Context)
      description: 請說明此工程任務欲達成的目標、重構範圍或背景動機。
      placeholder: "將舊版認證中介層遷移至新版 Session API，並移除過時的相容層..."
    validations:
      required: true

  - type: textarea
    id: acceptance-criteria
    attributes:
      label: 交付項目與驗收條件 (Deliverables & Acceptance Criteria)
      description: 請列出具體的執行步驟或完成判準（可使用 `- [ ]` 建立核取清單）。
      placeholder: |
        - [ ] 完成核心模組重構
        - [ ] 補齊整合測試並確認 CI 通過
        - [ ] 更新相關文件與遷移指南
    validations:
      required: true

  - type: textarea
    id: notes
    attributes:
      label: 技術備註與相依項目 (Technical Notes & Dependencies)
      description: 相關聯的 Issue / PR 編號、潛在風險或實作參考資料。
      placeholder: "前置依賴：#12；注意需維持設定檔向後相容..."
    validations:
      required: false
```

---

## 2. 中英雙語欄位對照（English Mode）

| 欄位 `id` / 項目 | 繁體中文 (預設) | English |
|---|---|---|
| `name` | `🛠 工程任務與維護 (Task / Chore)` | `🛠 Engineering Task / Chore` |
| `description` | `追蹤內部重構、技術債清理、CI/CD 維護或版本發佈檢查清單` | `Track internal refactoring, technical debt, CI/CD maintenance, or release checklists` |
| `goal` label | `任務目標與背景 (Task Goal & Context)` | `Task Goal & Context` |
| `acceptance-criteria` label | `交付項目與驗收條件 (Deliverables & Acceptance Criteria)` | `Deliverables & Acceptance Criteria` |
| `notes` label | `技術備註與相依項目 (Technical Notes & Dependencies)` | `Technical Notes & Dependencies` |
