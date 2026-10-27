# Repo PR 模板範本（`.github/pull_request_template.md`）

目標路徑：`.github/pull_request_template.md`

用途：讓 GitHub 網頁開 PR 時自動帶入，並讓沒有載入本 skill 的 agent 也照同一份段落撰寫（例如 Claude Code 雲端 session 開 PR 前會檢查並沿用 repo 的 PR 模板）。

> - 內容與 `references/pr-template.md` 的完整版一致；GitHub 只支援一份預設模板，無法自動切換精簡版／完整版，因此以 HTML 註解標示小型 PR 可刪除的段落。HTML 註解在 PR 頁面不會顯示。
> - 若 repo 含 `migrations/`、`infra/`、`.env` 等部署相關路徑，可在「備註」前加入 `references/pr-template.md` 的 Deployment 段落，並同樣標示為選填。

## 既有模板偵測

GitHub 會讀取以下任一位置（檔名不分大小寫），建立前全部檢查：

- `.github/pull_request_template.md`
- `pull_request_template.md`（repo 根目錄）
- `docs/pull_request_template.md`
- `.github/PULL_REQUEST_TEMPLATE/` 目錄下的多份模板

## 繁體中文版（預設）

```markdown
<!--
標題請遵循 Conventional Commits：<type>(<scope>): <summary>
小型 PR（commits ≤ 2 且變更檔案 ≤ 10）只需填寫：摘要、修改內容、變更類型；標示「選填」的段落可整段刪除。
請勿填入客戶／組織名稱、email、support ticket 原文等個人資料。
-->

### 摘要
<!-- 一句話說明此 PR 的核心目的 -->

### 修改內容
<!-- 條列具體的修改內容 -->
-

### Why
<!-- 選填：變更動機不明顯時填寫。大型 PR 請分別說明商業背景與技術理由 -->

### Testing
<!-- 選填：小型 PR 可刪除 -->
- [ ] 單元測試通過且覆蓋新功能
- [ ] 使用者介面變更已完成手動測試
- [ ] 效能 / 安全性考量已確認

### ⚠️ 風險評估與破壞性變更
<!-- 選填：小型 PR 可刪除。沒有破壞性變更時寫「無破壞性變更」 -->

### 相關連結
<!-- 選填：Fixes #123（合併時關閉 issue）或 Refs #123（僅連結） -->

### 變更類型
- [ ] 新增功能 (feat)
- [ ] 修復錯誤 (fix)
- [ ] 重構 (refactor)
- [ ] 文件 (docs)
- [ ] 測試 (tests)
- [ ] 其他 (chore / ci / perf)

### 備註
<!-- 選填：部署提示、截圖等 -->
```

## English Version

```markdown
<!--
Title must follow Conventional Commits: <type>(<scope>): <summary>
Small PRs (≤ 2 commits and ≤ 10 changed files) only need Summary, Changes, and Type of Change; sections marked "Optional" can be removed.
Do not include customer or organization names, emails, or support ticket text.
-->

### Summary
<!-- One sentence on the purpose of this PR -->

### Changes
<!-- List the concrete changes -->
-

### Why
<!-- Optional: fill in when the motivation is not obvious. For large PRs, cover both business context and technical rationale -->

### Testing
<!-- Optional: remove for small PRs -->
- [ ] Unit tests pass and cover the new behavior
- [ ] UI changes were tested manually
- [ ] Performance / security considerations reviewed

### ⚠️ Risks and Breaking Changes
<!-- Optional: remove for small PRs. Write "No breaking changes" if none -->

### Related Links
<!-- Optional: Fixes #123 (closes the issue on merge) or Refs #123 (link only) -->

### Type of Change
- [ ] New feature (feat)
- [ ] Bug fix (fix)
- [ ] Refactor (refactor)
- [ ] Documentation (docs)
- [ ] Tests (tests)
- [ ] Other (chore / ci / perf)

### Notes
<!-- Optional: deployment notes, screenshots, etc. -->
```
