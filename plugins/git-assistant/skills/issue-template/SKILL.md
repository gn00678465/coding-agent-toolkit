---
name: issue-template
description: 建立、重構與驗證 GitHub Issue 模板（.github/ISSUE_TEMPLATE/*.yml YAML Issue Forms 與 config.yml 入口分流）。觸發情境：(1) 為專案新增或重構 Bug Report、Feature Request、Documentation 等 Issue 表單；(2) 將舊版 ISSUE_TEMPLATE.md 遷移為結構化 YAML Issue Forms；(3) 配置 config.yml 關閉空白 Issue 並導流 Q&A／資安通報；(4) 優化既有表單以降低回報放棄率或檢核 GitHub Form Schema 陷阱。支援繁體中文與英文切換。不適用於開啟、編輯、查詢或關閉單一 GitHub Issue（如 gh issue create / view / edit）或撰寫 Pull Request 模板。
---

# GitHub Issue 模板與分流配置

為儲存庫建立兼顧**低填寫摩擦（60 秒原則）**與**結構化自動分流**的 `.github/ISSUE_TEMPLATE/` YAML Issue Forms 套件。

> - 各模板之標準 YAML 範本與中英雙語對照按需讀取：[`references/config.md`](references/config.md)、[`references/bug-report.md`](references/bug-report.md)、[`references/feature-request.md`](references/feature-request.md)、[`references/docs.md`](references/docs.md)、[`references/issue-triage.md`](references/issue-triage.md)。
> - 大型開源專案實證數據與五大專案（Vite、Next.js、Kubernetes、Astral、VS Code）架構分析見 [`references/issue-forms-guide.md`](references/issue-forms-guide.md)——使用者追問設計依據或需針對特殊專案架構裁切欄位時讀取。

## 貫穿全程的規則

- **語言切換**：使用者訊息含 `english`、`in English`、`用英文`、`英文`、`用英語`、`以英文` 任一字詞時，全程（含產出的 YAML `name`、`description`、`label`、`placeholder`、`options` 與對話回覆）使用英文；否則預設使用**繁體中文 (zh-TW)**。
- **2 必填預算制**：每張表單中 `validations.required: true` 的欄位數量**上限為 2 個**。Bug 表單必須將「實際現象」與「預期行為」合併為單一 `what-happened` 欄位，不得拆分為兩個獨立必填框。
- **敘述欄位禁設 `render`**：GitHub Issue Forms 的 `textarea` 一旦加上 `render`，前端會轉為純程式碼區塊並**停用圖片貼上與檔案拖放上傳**。`what-happened`、`repro`、`problem`、`proposal` 嚴禁設定 `render`；僅對純文字日誌（`logs`）或設定檔片段（`config-file`）啟用 `render`。
- **禁設儀式性核取方塊牆**：不得在表單底部放置「已搜尋重複 Issue」「已閱讀文件」等強制勾選的 `checkboxes`。填表提示一律放在表單頂部的單一 `type: markdown` 區塊（送出後不會渲染至 Issue 內文）。
- **分類選單必含逃生口**：所有子系統或模組 `dropdown` 的首項（`default: 0`）必須為 `不確定 / 通用 (Not sure)`（英文：`Not sure / General`），且 `options` **嚴禁包含保留字 `None`**。
- **禁止硬編 `projects` 與 `---` 分隔線**：公開模板頂層不得設定 `projects`（無 Project 寫入權限的開單者會靜默失敗）；YAML Issue Forms 不得使用 Markdown Frontmatter 的 `---` 文件分隔線。

---

## 執行流程

### Step 1 — 環境與儲存庫探測（Pre-flight）

1. **探測 GitHub 儲存庫狀態與現有標籤**：

   ```bash
   gh repo view --json nameWithOwner,hasDiscussionsEnabled,isPrivate,url
   gh label list --json name --jq '.[].name'
   ```

   - **降級處理（離線／非 GitHub 遠端／`gh` 未授權）**：若命令失敗，將儲存庫狀態標記為 `unverified`——後續 `config.yml` 不自動填入依賴儲存庫網址的 `contact_links`（或先詢問使用者 `OWNER/REPO`），模板頂層 `labels` 僅使用 GitHub 預設標籤（`bug`、`enhancement`、`documentation`）。

2. **盤點既有模板與專案形態**：
   - 檢查 `.github/ISSUE_TEMPLATE/`、`ISSUE_TEMPLATE.md`、`.github/ISSUE_TEMPLATE.md` 是否存在。
   - 依根目錄設定檔（`package.json`、`pyproject.toml`、`Cargo.toml`、`go.mod` 等）判定專案形態：

   | 專案形態 | 判定線索 | Bug 表單配置策略 |
   |---------|---------|----------------|
   | **CLI / 編譯器 / 靜態工具** | 含 CLI `bin` 入口、Linter/Formatter/建置工具，無 GUI | 採 **CLI 內嵌重現範本**：以 `code-snippet`（`render: text`）與選填 `config-file`（依專案設定檔設為 `render: toml`／`json`／`yaml`）直接貼入文字重現，不要求建立外部 Repo |
   | **Web / 前端 / UI 元件庫** | 含 React、Vue、Svelte、Next.js、Vite 等前端相依 | 採**通用範本**：`repro` 提示支援 StackBlitz / CodeSandbox 或最小 Repo，並依專案模組配置 `area` 下拉選單 |
   | **大型系統 / 多模組** | Monorepo（`workspaces`、`packages/*`）或基礎設施專案 | 採**通用範本（漸進式揭露）**：必填僅限 `what-happened` 與 `repro`，環境版本與周邊插件皆設為選填並標註「若適用才填寫」 |
   | **通用函式庫 / 其他** | 一般套件或無法歸入上列者 | 採**通用範本** |

### Step 2 — 配置入口分流 `.github/ISSUE_TEMPLATE/config.yml`

讀取 [`references/config.md`](references/config.md)，設定 `blank_issues_enabled: false` 強制走結構化表單，並依 Step 1 探測結果動態決定 `contact_links`：

- `hasDiscussionsEnabled: true` → 加入 Q&A Discussions 導流連結（`https://github.com/<OWNER>/<REPO>/discussions`）。
- `isPrivate: false` 或儲存庫存在 `SECURITY.md` → 加入資安漏洞私密通報連結（`https://github.com/<OWNER>/<REPO>/security/advisories/new`）。
- 使用者有指定外部社群（Discord、Slack、Stack Overflow）→ 加入對應連結。

> **Schema 防呆**：未啟用的管道（如 `hasDiscussionsEnabled: false` 時的 `/discussions`）**不得**寫入 `contact_links`，以免產生 404 死鏈；若無任何有效外部連結，**完全省略 `contact_links` 鍵**（GitHub Schema 不允許 `contact_links: []` 空陣列）。

### Step 3 — 產製 YAML Issue Forms

依使用者需求與目標專案形態，**僅讀取本次需要產出的模板參考檔**並寫入 `.github/ISSUE_TEMPLATE/`：

1. `1-bug-report.yml` → 讀取 [`references/bug-report.md`](references/bug-report.md)（通用版或 CLI 內嵌重現版）
2. `2-feature-request.yml` → 讀取 [`references/feature-request.md`](references/feature-request.md)
3. `3-docs.yml`（當使用者要求完整套件或專案包含文件網站時產出）→ 讀取 [`references/docs.md`](references/docs.md)
4. `.github/workflows/issue-triage.yml`（僅在使用者要求自動標籤分流工作流時產出）→ 讀取 [`references/issue-triage.md`](references/issue-triage.md)

**標籤與儲存庫權限處置**：

- **標籤存在性核對**：GitHub Issue Forms 頂層 `labels` 若引用儲存庫尚不存在的標籤（如 `pending-triage`、`needs-discussion`），開單時會被 GitHub **靜默忽略**。對照 Step 1 的 `gh label list`：
  - 若目標標籤已存在 → 寫入 `labels`。
  - 若目標標籤不存在 → 預設只寫入已存在的標籤（如 `["bug"]`、`["enhancement"]`），並提示使用者可選執行 `gh label create pending-triage --color FBCA04`、`gh label create needs-discussion --color D4C5F9` 後再掛上。
- **私有儲存庫注意**：若 `isPrivate: true`，主動告知使用者 GitHub 在 Private / Internal 儲存庫會將 `validations.required: true` 自動降級為選填，屬平台預期行為。
- **舊版 Markdown 模板清理**：若專案存在舊版 `ISSUE_TEMPLATE.md`，經使用者確認後移除或搬遷，避免新舊模板並存造成入口混亂。

### Step 4 — Schema 與防呆驗證（Gate）

寫入檔案後，執行以下腳本驗證 `.github/ISSUE_TEMPLATE/` 下所有 YAML 檔（優先用 `uv run --with pyyaml python`，無 `uv` 時改用已安裝 `pyyaml` 的 `python`）：

```bash
uv run --with pyyaml python -X utf8 -c "
import glob, os, re, yaml

files = glob.glob('.github/ISSUE_TEMPLATE/*.yml') + glob.glob('.github/ISSUE_TEMPLATE/*.yaml')
assert files, 'No YAML files found in .github/ISSUE_TEMPLATE/'

for path in files:
    raw = open(path, encoding='utf-8').read()
    assert not re.search(r'^---\s*$', raw, re.M), f'{path}: forbidden --- frontmatter delimiter'
    data = yaml.safe_load(raw)
    assert isinstance(data, dict), f'{path}: root must be a YAML mapping'

    if os.path.basename(path) in ('config.yml', 'config.yaml'):
        if 'contact_links' in data:
            assert isinstance(data['contact_links'], list) and len(data['contact_links']) > 0, f'{path}: contact_links must not be empty'
            for link in data['contact_links']:
                assert all(k in link for k in ('name', 'url', 'about')), f'{path}: contact_link missing required keys'
                assert link['url'].startswith(('https://', 'http://')), f'{path}: url must start with http(s)://'
        continue

    for req_key in ('name', 'description', 'body'):
        assert data.get(req_key), f'{path}: missing top-level {req_key}'
    assert 'projects' not in data, f'{path}: avoid top-level projects in issue forms'

    ids, labels, req_count = set(), set(), 0
    for item in data['body']:
        t = item.get('type')
        attrs = item.get('attributes', {})
        if t == 'markdown':
            assert 'validations' not in item, f'{path}: markdown item cannot have validations'
            assert attrs.get('value'), f'{path}: markdown item missing value'
            continue
        el_id = item.get('id')
        assert el_id and re.match(r'^[a-zA-Z0-9_-]+$', el_id), f'{path}: invalid or missing id {el_id}'
        assert el_id not in ids, f'{path}: duplicate id {el_id}'
        ids.add(el_id)
        lbl = attrs.get('label', '')
        assert lbl and lbl not in labels, f'{path}: duplicate or missing label {lbl}'
        labels.add(lbl)
        if el_id in ('what-happened', 'repro', 'problem', 'proposal'):
            assert 'render' not in attrs, f'{path}: {el_id} must not set render (blocks image/file upload)'
        if item.get('validations', {}).get('required') is True:
            req_count += 1
        if t == 'dropdown':
            opts = attrs.get('options', [])
            assert opts and len(opts) == len(set(opts)), f'{path}: dropdown {el_id} options must be non-empty and unique'
            assert all(str(o).strip().lower() != 'none' for o in opts), f'{path}: dropdown {el_id} contains reserved word None'
            if 'default' in attrs:
                assert isinstance(attrs['default'], int) and 0 <= attrs['default'] < len(opts), f'{path}: invalid default index in {el_id}'
    assert req_count <= 2, f'{path}: required fields ({req_count}) exceed budget of 2'

print(f'OK: validated {len(files)} file(s) successfully.')
"
```

任何斷言失敗時，必須修正對應 YAML 並重跑至印出 `OK` 為止，才算完成交付。
