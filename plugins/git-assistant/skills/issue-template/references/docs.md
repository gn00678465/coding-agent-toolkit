# 文件修正模板範本 (`3-docs.yml`)

目標路徑：`.github/ISSUE_TEMPLATE/3-docs.yml`

---

## 1. 極簡文件修正範本（繁體中文預設）

```yaml
name: 📖 文件缺漏與修正 (Documentation)
description: 回報官方文件、教學範例或型別註解的錯誤或不清楚之處
title: "[Docs]: "
labels: ["documentation"]
body:
  - type: markdown
    attributes:
      value: |
        > 💡 **快速提示**：若為單純的錯別字或小段範例更新，非常歡迎直接提交 Pull Request！

  - type: textarea
    id: doc-issue
    attributes:
      label: 文件問題描述 (Issue Description)
      description: 請說明哪一篇文件、哪個章節有錯誤、缺漏或容易造成誤導之處（請附上文件 URL 或檔案路徑）。
    validations:
      required: true

  - type: textarea
    id: suggestion
    attributes:
      label: 建議修正內容 (Suggested Improvement)
      description: 請提供您認為更正確、更清楚的說明或範例代碼。
    validations:
      required: false
```

---

## 2. 中英雙語欄位對照（English Mode）

| 欄位 `id` / 項目 | 繁體中文 (預設) | English |
|---|---|---|
| `name` | `📖 文件缺漏與修正 (Documentation)` | `📖 Documentation Issue` |
| `description` | `回報官方文件、教學範例或型別註解的錯誤或不清楚之處` | `Report inaccuracies, missing sections, or unclear examples in the documentation` |
| `doc-issue` label | `文件問題描述 (Issue Description)` | `Documentation Issue Description` |
| `suggestion` label | `建議修正內容 (Suggested Improvement)` | `Suggested Improvement` |
