# 研究筆記：檢查 apm.yml 外部套件的上游更新

- **主要來源**：
  - APM 官方文件 [`microsoft.github.io/apm`](https://microsoft.github.io/apm/)：[Manage dependencies](https://microsoft.github.io/apm/consumer/manage-dependencies/)、[Private and org packages](https://microsoft.github.io/apm/consumer/private-and-org-packages/)、[Install packages](https://microsoft.github.io/apm/consumer/install-packages/)、[Publish to a marketplace](https://microsoft.github.io/apm/producer/publish-to-a-marketplace/)、[Manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/)、[Lockfile spec](https://microsoft.github.io/apm/reference/lockfile-spec/)、[apm marketplace CLI reference](https://microsoft.github.io/apm/reference/cli/marketplace/)
  - [`microsoft/apm`](https://github.com/microsoft/apm) repo（`apm.lock.yaml` 範例檔）
  - `docs.github.com`：[REST API rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)、[Best practices for using the REST API](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)（conditional requests）、[Commits](https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28)（list commits、compare two commits）、[GraphQL rate limits](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api)
  - `git-scm.com`：[`git-ls-remote`](https://git-scm.com/docs/git-ls-remote)
  - `github.blog` changelog：[Updated rate limits for unauthenticated requests](https://github.blog/changelog/2025-05-08-updated-rate-limits-for-unauthenticated-requests/)
  - 本機指令輸出：`apm-go --version`（0.3.0-rc.1）、`apm-go marketplace outdated -v`、`apm-go marketplace check -v`、`apm --version`（0.27.0）、`apm --help` 與各子指令 `--help`、`gh --version`（2.83.0）、`gh api`、`git ls-remote`（皆為唯讀查詢，輸出摘要見各節）
  - 本 repo 檔案：`apm.yml`、`.claude-plugin/marketplace.json`、`.agents/plugins/marketplace.json`、`README.md`、`git log -- apm.yml`
- **檢索備註**：
  - `apm.yml`、兩份 `marketplace.json` 為工作樹中未提交的修改，本研究只讀取，未修改、未 `git add`、未 commit。
  - `apm marketplace outdated -v` 已在本 repo 實際執行（exit 0，執行前後 `git status --short` 相同），結果見 3.1。`apm-go marketplace outdated -v` 與 `apm-go marketplace check -v` 也已執行，結果見 3.3。`apm marketplace check`（非 `apm-go`）的行為說明只來自官方文件，未執行。本機 `apm --version` 為 0.27.0，落後官方文件所述最新版 0.30.0（執行 `apm outdated --help` 時 CLI 自動印出「A new version of APM is available: 0.30.0」），但本研究引用的所有子指令名稱與其 `--help` 輸出，皆是在本機 0.27.0 上實際執行得到，非僅來自文件推測。
  - `git ls-remote`、`gh api`（含一次 GraphQL 查詢）已實際對 `apm.yml` 中真實存在的外部套件 repo（`tt-a1i/archify`、`pbakaus/impeccable`）執行唯讀查詢，作為第 5、6 節的實測依據。
  - apm.yml 中所有外部套件的 `source` 皆為 `github.com`，未出現 GitLab、Azure DevOps 來源，故第 5 節不研究非 GitHub 來源。
- **檔案位置說明**：延續 `docs/research/agents-md-refactoring.md`、`docs/research/skill-router.md` 建立的 `docs/research/` 慣例，本檔案為第三篇研究筆記，格式（無 YAML front matter、開頭來源列表、`---`、後接 `## N.` 編號章節）沿用前兩篇。

---

## 1. 本 repo 的實際資料

### 1.1 三份設定檔的角色分工

`apm.yml` 是唯一的人工編輯來源。它有一個 `marketplace:` 區塊，`packages:` 清單同時放**自行開發**與**外部**兩種套件（來源：`apm.yml` 全文）。

`.claude-plugin/marketplace.json` 與 `.agents/plugins/marketplace.json` 是 `apm pack` 從 `apm.yml` 產生的**輸出物件**，不是人工維護的第二份宣告（證據：兩份 JSON 的套件清單、`ref`/`sha`/`tag_pattern` 欄位值與 `apm.yml` 逐一對應；`apm.yml` 註解自帶指令 `apm-go pack --marketplace=claude,codex --json | jq ...`，來源：`apm.yml` 第 20-22 行附近註解）。兩份 JSON 差異只在欄位命名慣例：`.claude-plugin/marketplace.json` 用扁平陣列 `plugins[]` 加 `source` 物件；`.agents/plugins/marketplace.json` 額外包了 `policy: {installation, authentication}` 區塊。

### 1.2 外部依賴的記錄格式

目前工作樹（含未提交的 `open-steps` 新增）`apm.yml` 的 `marketplace.packages` 共 **12 筆**：**4 筆自行開發**（`git-assistant`、`advisor`、`code-review`、`slim-agents-md`）、**8 筆外部**（`web-quality-skills`、`impeccable`、`taste-skill`、`beautify-github-readme`、`show-me`、`reviewable-html-workbench`、`archify`、`open-steps`）。已提交的 HEAD 版本是 11 筆（4 自製 + 7 外部，不含 `open-steps`）。

外部套件的欄位範例（`impeccable`，來源：`apm.yml`）：

```yaml
- name: impeccable
  source: https://github.com/pbakaus/impeccable.git
  ref: 63b04e2530f5c7b41ea83c133daab24f34912456
  version: 4.1.2
  tag_pattern: skill-v{version}
  category: design
```

- `source`：遠端 git URL（`https://github.com/<owner>/<repo>.git`）。
- `ref`：**一律是完整 40 字元 commit SHA**，8 筆外部套件無一例外。
- `version`：人類可讀版本號（多數對應上游的 git tag）。4 筆有填（`impeccable`、`reviewable-html-workbench`、`archify`、`open-steps`），4 筆未填（`web-quality-skills`、`taste-skill`、`beautify-github-readme`、`show-me`）。
- `tag_pattern`：`version` 換算成上游 tag 名稱的樣板，例如 `skill-v{version}` → tag `skill-v4.1.2`；未填則用 `marketplace.build.tagPattern` 全域預設 `v{version}`。
- `subdir`：monorepo 子目錄，`show-me`（`plugins/show-me`）與 `archify`（`archify`）兩筆使用。

### 1.3 是否釘選 ref/tag/commit

**只釘選 commit，不信任 tag 或 branch。** `ref` 欄位全部是完整 SHA，`version`/`tag_pattern` 只作為人類可讀標籤與（若之後要跑 `apm pack`/`apm marketplace outdated`）比對上游最新 tag 用，**不是**實際安裝依據——依 APM 官方 schema，「`ref` 欄位……會覆蓋同時存在的 `version` range」（來源：[Manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/)）。

### 1.4 lockfile

**本 repo 沒有 `apm.lock.yaml` / `apm.lock` / `apm.lock.yml`**（`Glob` 搜尋 `**/apm.lock*` 全 repo 無結果）。這與 1.3 的發現一致：因為 `apm.yml` 本身已把每個外部套件釘死在一顆 commit 上，宣告值與「已解析值」是同一件事，不需要另一份鎖定檔案記錄「解析後的結果」。此外，本 repo 的 `apm.yml` 只有 `marketplace:` 發布端（producer/authoring）區塊，沒有 `dependencies:`（consumer）區塊——鎖定檔案是 `apm install` 針對 `dependencies:` 區塊產生的產物（見第 2、4 節），本 repo 從未以自身身分執行過會產生 lockfile 的安裝流程。

### 1.5 scripts 與 CI

**都不存在。** `Glob scripts/**` 與 `Glob .github/workflows/**` 均回傳「No files found」。目前更新外部套件版本，是手動編輯 `apm.yml` 後（可能）手動跑 `apm pack` 重新產生兩份 `marketplace.json`（見 1.1 的證據鏈），沒有任何自動化腳本或排程。這正是使用者想用腳本取代的手動流程本身。

### 1.6 apm.yml 的演進（`git log --oneline -- apm.yml`）

`apm.yml` 至今共 **10 個提交**：

```
0e27a70 revert(marketplace): 將 taste-skill 改回單一入口
8236e14 feat(marketplace): 將 taste-skill 拆為五個子目錄入口
624f686 fix(marketplace): 將 archify 改以 commit sha 鎖定版本
df092fc style(apm): 修正 marketplace 範例註解縮排
2a2832a fix(marketplace): 補上 archify 的 ref 版本鎖定
3e5f23d feat(marketplace): 新增 archify 套件
9044c8a feat(marketplace): 新增 reviewable-html-workbench 套件
ca60a50 feat(marketplace): 新增 show-me 套件並調整 impeccable 分類
806359e feat(marketplace): 新增四個外部 skill 套件至 marketplace
531170b refactor(slim-agents-md)!: 將 trim-instruction-bloat 更名為 slim-agents-md（首次新增 apm.yml）
```

關鍵演進（`git show <sha> -- apm.yml` 逐一核對）：`archify` 加入時（`3e5f23d`）只有 `version: 2.16.0`，18 分鐘後補 `ref: v2.16.0`（`2a2832a`），26 分鐘後再改成 `ref: c826e6c3a7abad19c0f3cd1ca57207d54b1ad8de`（`624f686`，commit message 明講「將 archify 改以 commit sha 鎖定版本」）。這條軌跡就是本 repo「不信任 tag、只信任 commit SHA」這條慣例的成文證據——防的是上游維護者事後移動或重新打 tag。另外 `8236e14`/`0e27a70` 是一次把 `taste-skill` 拆成 5 個子目錄入口又撤回的實驗，與更新檢查無直接關係。

### 1.7 自行開發 vs 外部套件的判定依據

依 `apm.yml`／兩份 `marketplace.json` 的 `source` 欄位型態判定，二擇一，無需猜測：

| | 自行開發 | 外部套件 |
|---|---|---|
| `apm.yml` 的 `source` | `./plugins/<name>`（相對路徑，指向本 repo 內） | `https://github.com/<owner>/<repo>.git`（遠端 URL） |
| 是否有 `ref` | 無 | 有，且必為 40 字元 commit SHA |
| `.claude-plugin/marketplace.json` 的 `source` | `"./plugins/<name>"`（字串） | `{"source": "url"｜"git-subdir", "url", "ref", "sha", "tag_pattern"}`（物件） |
| `.agents/plugins/marketplace.json` 的 `source` | `{"source": "local", "path": "./plugins/<name>"}` | `{"source": "url"｜"git-subdir", "url", "ref", "sha", "tag_pattern"}` |

README.md 對此也有一句明文佐證：「以下為透過 marketplace 轉發的第三方 skill 套件，皆以 commit sha 鎖定版本」「本專案不散布這些套件的程式碼，marketplace 僅保存 URL 與 commit sha 指標」（來源：`README.md` 第 14-16、32 行附近）。

---

## 2. APM 官方 apm.yml 依賴語法

APM 的 apm.yml 有兩種互不相同、但外觀相似的依賴宣告區塊：**`dependencies:`**（consumer，安裝到自己專案）與**`marketplace:`**（producer/authoring，本 repo 實際使用的那種）。兩者的 `ref`／`source` 語法概念相通，但欄位集合不同。

### 2.1 `dependencies:` 區塊（consumer 語法）

來源：[Manage dependencies](https://microsoft.github.io/apm/consumer/manage-dependencies/)。

```yaml
dependencies:
  apm:
    - microsoft/apm-sample-package#v1.0.0
    - github/awesome-copilot/skills/review-and-refactor
devDependencies:
  apm:
    - my-org/internal-test-skills
```

必須用「頂層對映（`apm:`/`devDependencies.apm:`）」，不接受頂層平面陣列。支援的來源寫法（文件列出 10 種）：

| 形式 | 範例 | 用途 |
|---|---|---|
| GitHub 簡寫 | `owner/repo` | 公開 GitHub repo，預設分支 |
| 釘選參考 | `owner/repo#v1.0.0` | 釘到 tag／branch／完整 commit SHA |
| 指定 host 簡寫 | `gitlab.com/acme/repo#v2.0` | 任意 git host |
| 虛擬子目錄 | `owner/repo/skills/review` | monorepo 內特定資料夾 |
| 虛擬檔案 | `owner/repo/prompts/review.prompt.md` | 單一原始檔 |
| HTTPS URL | `https://gitlab.com/acme/repo.git` | 明確 URL |
| SSH SCP 形式 | `git@gitlab.com:acme/repo.git` | 預設埠 |
| SSH URL | `ssh://git@gitlab.com/acme/repo.git` | 明確 scheme／埠 |
| 本地路徑 | `./packages/shared`、`/abs/path` | 本機同級套件 |
| 物件形式 | `{ git: <url>, path: <subpath>, ref, alias, ... }` | 別名、巢狀群組、monorepo 子路徑 |

`#ref` 可以是：

- **Tag**：`owner/repo#v1.0.0`（不可變）
- **Branch**：`owner/repo#main`（會移動）
- **完整 commit SHA**（不可變）
- **semver range**：`owner/repo#^1.2.0`、`#~1.4`、`#>=2.0 <3`、`#1.5.x`——文件明講「分支會移動；標籤和 SHA 不會。為了可重現性，傾向於使用標籤或 SHA」，且對於 semver range 或可移動 ref，「APM 將範圍與標籤進行匹配……選擇滿足該範圍的最高標籤。原始約束條件保存在鎖定檔案中，供後續 `apm install` 進行確定性重放」（來源同上）。

物件形式僅接受 `git`、`path`、`ref`、`alias`、`type`、`allow_insecure`、`skills`、`targets` 幾個鍵（來源同上）。

### 2.2 `marketplace:` 區塊（producer/authoring 語法，本 repo 實際使用）

來源：[Publish to a marketplace](https://microsoft.github.io/apm/producer/publish-to-a-marketplace/)、[Manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/)。

```yaml
marketplace:
  sourceBase: https://gitlab.corp.example.com/platform/agent-marketplace
  build:
    tagPattern: "v{version}"      # 全域預設；MUST 恰含一個 {version}，{name} 選填
  packages:
    - name: example-package        # 必要：套件識別符
      source: example-package      # 必要：相對路徑／owner/repo／完整 URL
      version: "^1.0.0"            # 版本 range（semver 字串，pack 時才解析）
      description: Human-readable description
    - name: pinned-package
      source: acme-org/pinned-package
      ref: 3f2a9b1c                # 明確 git ref：SHA／tag／branch，覆蓋 version
      description: Fixed commit reference
    - name: local-tool
      source: ./packages/local-tool
      version: 0.1.0
      category: Productivity        # 輸出 codex 格式時必要
```

每個 `packages` 項目欄位語意（來源：[Manifest schema](https://microsoft.github.io/apm/reference/manifest-schema/)）：

- `name`、`source`：必要。
- 遠端套件**至少要有** `version` 或 `ref` 其中一個。
- `version`："Semver range (e.g. `^1.0.0`, `~2.1.0`, `>=3.0`). Stored as a string; resolution happens at pack time."
- `ref`："Explicit git ref (SHA, tag, or branch). Overrides `version` range when both are present."——與 2.1 節 consumer 語法的 `#ref` 概念一致，一樣接受 SHA／tag／branch 三種。
- `subdir`：repo 內子目錄（本地來源忽略此欄）。
- `tag_pattern`：覆蓋 `build.tagPattern`；`include_prerelease`：布林，是否允許 prerelease tag 參與匹配。
- `description`、`homepage`、`tags`、`keywords`、`author`、`license`、`repository`、`category`：純中繼資料透傳欄位。

### 2.3 `apm pack` 如何把 `source` 轉成 `marketplace.json`

來源：[Publish to a marketplace](https://microsoft.github.io/apm/producer/publish-to-a-marketplace/)。

> "apm pack resolves every remote packages: entry against git ls-remote, leaves local-path entries untouched, and writes each selected marketplace output atomically."

即：**`apm pack` 本身就是用 `git ls-remote` 去解析每一筆遠端套件**——這點對第 6 節的方案比較很關鍵，代表 APM 官方工具鏈本身在「查上游」這一步，能拿到的資訊上限就是 `git ls-remote`（repo 層級的 refs/commits），不天生具備「這個 commit 之後 subdir 有沒有變」的能力。輸出轉換規則：

- 遠端無 `subdir` → `marketplace.json` 產出 `source: "url"` 物件（含 `url`、`ref`、`sha`、`tag_pattern`）。
- 遠端有 `subdir` → 產出 `source: "git-subdir"` 物件（多一個 `path` 欄位）。
- 本地路徑 → 保持相對路徑字串，不轉物件（對照本 repo `.claude-plugin/marketplace.json` 中 `git-assistant` 等 4 筆自製套件的 `source` 確實是純字串，外部套件才是物件——與第 1.7 節的判定依據互相印證）。
- `apm.yml` 的 `packages:` 鍵在輸出時改名為 `plugins:`。

---

## 3. APM CLI 是否已內建檢查更新的指令

本機已安裝 `apm --version` → `Agent Package Manager (APM) CLI version 0.27.0`（`apm.exe`，路徑 `/c/Users/gn006/AppData/Local/Programs/apm/current/apm`）。以下指令與輸出皆為本機 `--help` 實際執行結果。

### 3.1 兩套並存但語意不同的「outdated」指令

**`apm outdated`**（consumer，針對 `dependencies:` + `apm.lock.yaml`）：

```
Usage: apm.exe outdated [OPTIONS]
  Show outdated locked dependencies
Options:
  -g, --global                   Check user-scope dependencies (~/.apm/)
  -v, --verbose                  Show additional info (e.g., available tags for outdated deps)
  -j, --parallel-checks INTEGER  Max concurrent remote checks (default: 4, 0 = sequential)
```

名稱是「Show outdated **locked** dependencies」——語意上針對已有 `apm.lock.yaml` 的專案。本 repo 沒有 `dependencies:` 區塊也沒有 lockfile（見 1.4），**這個指令不是本 repo 的適用對象**（未實際執行驗證此推論，因為執行會嘗試連網／可能因缺 lockfile 而報錯，標記為「未確認」）。

**`apm marketplace outdated`**（authoring，針對 `marketplace:` 區塊，即本 repo 的情境）：

```
Usage: apm.exe marketplace outdated [OPTIONS]
  Show packages with available upgrades
Options:
  --offline             Use cached refs only (no network)
  --include-prerelease  Include prerelease versions
  -v, --verbose         Show detailed output
```

依官方文件（[apm marketplace CLI reference](https://microsoft.github.io/apm/reference/cli/marketplace/)）：預設連網比對，`--offline` 才走快取；支援 `tag_pattern` 自訂標籤樣板。

**實測結果（本機 0.27.0，在本 repo 執行 `apm marketplace outdated -v`）**：

```
│ [x] │ git-assistant      │ -- │ 0.1.4 │ -- (Git ref or reposit… not found during ls-remo… │ -- │
...（advisor、code-review、slim-agents-md 相同）
│ [i] │ web-quality-skills │ -- │ --    │ -- (Pinned to ref; skipped)                        │ -- │
...（其餘 7 筆外部套件相同）
[i] All packages are up to date
    0 upgradable entries
```

- 8 筆外部套件全部是 `Pinned to ref; skipped`。有 `ref` 的條目不會比對，與是否填 `version` 無關。
- 4 筆自行開發的套件是 `[x]`，原因是 ls-remote 找不到 ref。
- 結尾仍輸出 `All packages are up to date`，exit code 0。

結論：本 repo 所有外部套件都用 `ref` SHA 釘選，所以這個指令一定回報「全部是最新」。實測的 `archify` 落後上游 41 個 commit（見 5.2），這個指令也沒有偵測到。**這個指令不能用來檢查本 repo 的外部套件更新。**

### 3.2 其他相關指令

- `apm marketplace check`："Validate marketplace entries are resolvable"，確認「每個套件項目都能解析到可達成的 git ref」，一樣有 `--offline`。這是「連得到、ref 存在」的驗證，不是「有沒有更新」的比對。
- `apm marketplace audit NAME`："Check that plugin dependencies resolve through the marketplace"，查的是套件**自身宣告的相依性**有沒有繞過 marketplace 版控，跟「上游是否有新版」無關。
- `apm view <owner>/<repo> versions`："List available remote tags and branches"，會連網查詢，可用來人工核對某一筆套件目前有哪些 tag／branch，但一次只能查一筆、不會自動跟 `apm.yml` 裡宣告的 `ref` 做比較。
- `apm lock`（"Resolve dependencies and write apm.lock.yaml without deploying"）與 `apm update`（"Refresh APM dependencies to the latest matching refs"）都會**寫檔案**，任務規則明確禁止執行；且兩者都是針對 `dependencies:` 區塊，本 repo 沒有這個區塊。
- `apm deps`（`list`／`tree`／`why`／`info`）操作對象也是已安裝的 `dependencies:`，`apm deps info` 是 `apm view` 的別名。

### 3.3 `apm-go` 0.3.0-rc.1 實測

`apm.yml` 註解使用 `apm-go pack`。本機 `apm-go --version` 輸出 `apm-go version 0.3.0-rc.1`。`go version -m apm-go.exe` 顯示模組是 `github.com/apm-go/apm`。`gh api repos/apm-go/apm` 回傳 404，所以沒有讀到原始碼。

`apm-go marketplace --help` 列出與更新有關的兩個子指令：

- `outdated`：「Show marketplace packages with available upgrades」
- `check`：「Verify every marketplace package's pinned ref/version exists on its remote」

兩個指令都在本 repo 執行。執行前後 `git status --short` 相同。

**`apm-go marketplace outdated -v`**（exit 0）：

```
│ i │ git-assistant      │ -- │ 0.1.4 │ -- │ -- │ local package; skipped │
...（其餘 3 筆自行開發套件相同）
│ i │ web-quality-skills │ -- │ --    │ -- │ -- │ pinned to ref; skipped │
...（其餘 7 筆外部套件相同）
 i All packages are up to date
  - 0 upgradable entries
```

結果與 `apm` 0.27.0 相同：8 筆外部套件全部跳過，結尾仍回報「全部是最新」。

**`apm-go marketplace check -v`**（exit 1）：

```
│ x │ web-quality-skills │ + │ x │ x │ package "web-quality-skills": pinned ref "afa8da94…" not found on "https://github.com/addyosmani/web-quality-skills.git" │
...（其餘 7 筆外部套件相同）
 x check failed: 8/12 package(s) have an unverifiable pin
```

8 筆外部套件的 `ref` 都回報 not found。以下查詢證明這些 SHA 在上游存在：

| 套件 | `gh api repos/{repo}/commits/{ref}` | 符合 `ref` 的 `git ls-remote` 條目 |
|---|---|---|
| `web-quality-skills` | 存在 | `HEAD`、`refs/heads/main` |
| `impeccable` | 存在 | `refs/tags/skill-v4.1.2^{}` 等 3 筆 |
| `archify` | 存在 | `refs/tags/v2.16.0^{}` |
| `beautify-github-readme` | 存在 | 無 |
| 其餘 4 筆 | 存在 | 1–2 筆 |

`web-quality-skills` 的 `ref` 就是上游 `main` 的最新 commit，`check` 仍回報 not found。所以 `check` 不能用 commit SHA 比對 ref。可能的原因是 `check` 只用 ref 名稱（branch 或 tag 名稱）比對。這個原因沒有原始碼證據：**未確認**。

### 3.4 小結

本 repo 只有 `marketplace:` 發布端區塊，沒有 `dependencies:`，也沒有 lockfile。對應的內建指令是 `marketplace outdated`，不是 `apm outdated`。

- `apm` 0.27.0 和 `apm-go` 0.3.0-rc.1 的 `marketplace outdated` 都跳過有 `ref` 的條目，並回報「全部是最新」。
- `apm-go marketplace check` 把 8 個存在的 SHA 都回報成 not found。

本 repo 的外部套件都用 `ref` SHA 釘選。所以這兩個 CLI 都沒有可用的更新檢查，需要自己寫腳本。

---

## 4. lockfile

### 4.1 `apm.lock.yaml` 格式

本 repo 沒有這個檔案（見 1.4）。以下欄位規範取自官方 [Lockfile spec](https://microsoft.github.io/apm/reference/lockfile-spec/) 頁面，並用 [`microsoft/apm` 自己的 `apm.lock.yaml`](https://github.com/microsoft/apm/blob/main/apm.lock.yaml) 對照驗證：

**頂層欄位**：`lockfile_version`（`"1"` 純 git 專案／`"2"` 有 registry 或 semver 解析時）、`apm_version`、`dependencies`（清單）、`mcp_servers`/`mcp_configs`/`mcp_target_servers`、`lsp_servers`/`lsp_configs`/`lsp_target_servers`、`local_deployed_files`、`deployments`。

**每筆 `dependencies` 項目**：

- `repo_url`：規範化的 repo 路徑／URL，是這筆條目的身分依據之一。
- `resolved_commit`："Exact 40-char commit SHA installed. The pin."
- `resolved_ref`："The user-supplied ref from `apm.yml` (`main`, `v1.2.0`, a SHA)."——**同時保留使用者原本寫的 ref 字面值，與實際解析出來的 commit**，兩者分開存放。
- `version`：對 registry 條目是「精確選定版本，供重裝用」。
- `package_type`：`apm_package`／`skill_bundle`／`claude_skill`／`hook_package`／`hybrid`／`marketplace_plugin` 之一。
- `deployed_files`（排序後路徑清單）、`deployed_file_hashes`（`path -> sha256`）：供 `prune`／`audit` 做檔案存在性與完整性檢查。
- `depth`（0=專案本身，1=直接依賴，更高=遞移依賴）、`resolved_by`（把這筆遞移依賴帶進來的父套件 `repo_url`）。
- `virtual_path`、`is_virtual`：追蹤 monorepo 子路徑套件。
- `content_hash`："SHA-256 of the materialized package tree, computed from sorted relative paths and raw file bytes."

### 4.2 沒有 lockfile 時如何得知目前版本

**直接讀 `apm.yml` 的 `ref` 欄位即可**——因為本 repo 的慣例是 `ref` 一律填完整 commit SHA（見 1.3），`apm.yml` 本身就等同「目前使用版本」的宣告，不需要另外一份 lockfile 記錄「解析後的值」。這是本 repo 特有的簡化狀態，不是 APM 通例：若某筆條目改用 `version` range 或可移動的 `#branch`，沒有 lockfile 就真的無法得知「上次安裝時到底落在哪一顆 commit」，必須靠 lockfile 或重新解析。

---

## 5. 取得上游最新狀態的做法

### 5.1 `git ls-remote`

已對 `apm.yml` 中的真實套件實測：

```
$ git ls-remote --tags --heads https://github.com/tt-a1i/archify.git
fc0b3b49845e2564ab8001b375984b7aa1dfdfa4  refs/heads/chore/linuxdo-community-link
...（可列出所有 branch／tag 與其 commit）

$ git ls-remote --symref https://github.com/tt-a1i/archify.git HEAD
ref: refs/heads/main  HEAD
a07fa1d5b2a10cbea110c5a2be2817397a301cdc  HEAD
```

- **不需要認證**即可查詢公開 repo（`git-scm.com` 文件範例本身就是對公開 repo 做匿名查詢；本機實測也未帶任何憑證即成功）。
- **速率限制**：GitHub 官方部落格 2025-05-08 的公告（[Updated rate limits for unauthenticated requests](https://github.blog/changelog/2025-05-08-updated-rate-limits-for-unauthenticated-requests/)）明確提到這次調整涵蓋「cloning repositories over HTTPS」，但公告全文**沒有給出具體的匿名 git 協定請求數字上限**（只講 REST API 的 60/hr，見 5.2）。GitHub 社群討論（非官方文件，僅供旁證）表示 clone／`ls-remote` 官方沒有公開明確配額，只在「使用量高到影響服務」時才會限制。**匿名 git 協定的確切速率限制數字：未確認**。
- **對 subpath 依賴的限制**：`git ls-remote` 的協定層級只回傳「repo 有哪些 refs、各自指向哪個 commit」，**看不到任何檔案路徑資訊**，因此無法判斷 `show-me`（`subdir: plugins/show-me`）或 `archify`（`subdir: archify`）這種 monorepo 子目錄依賴，其對應的子目錄本身有沒有變動——即使 `ls-remote` 回報 default branch commit 換了，也可能只是同一個 repo 裡不相干的其他檔案在動。這一點與 2.3 節「`apm pack` 本身也只靠 `ls-remote`」的證據相互印證：**apm 官方工具鏈與最陽春的 `git ls-remote` 方案，在 subdir 感知能力上是同一個天花板**。

### 5.2 GitHub REST API

**速率限制**（來源：[Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)）：

- 未認證："The primary rate limit for unauthenticated requests is 60 requests per hour."
- 已認證："All of these requests count towards your personal rate limit of 5,000 requests per hour."（本機 `gh api rate_limit` 實測核對：`"core":{"limit":5000,"used":36,"remaining":4964}`，`gh` 已用個人帳號認證。）

**條件式請求**（來源：[Best practices for using the REST API](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)）：

> "Making a conditional request does not count against your primary rate limit if a `304` response is returned and the request was made while correctly authorized with an `Authorization` header."

即：**只有「已認證＋收到 304」才不計入速率限制**；未認證的條件式請求即使收到 304，官方文件的措辭仍以「帶 Authorization header」為前提，因此未認證情境下是否同樣豁免——**未確認**（文件此句只描述已認證情境，未反向說明未認證情境）。

**`GET /repos/{owner}/{repo}/commits`**（來源：[Commits – list commits](https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28)），相關參數：

- `sha`（optional）："SHA or branch to start listing commits from. Default: the repository's default branch."
- `path`（optional）："Only commits containing this file path will be returned."——**這是唯一能做到「只看子目錄」的官方端點參數**。
- `per_page`（optional，max 100，預設 30）。

本機實測（對 `archify` repo，篩選 `path=archify` 子目錄、`sha=main`）：

```
$ gh api --method GET repos/tt-a1i/archify/commits -f path=archify -f sha=main -f per_page=1
[{"sha":"a07fa1d5b2a10cbea110c5a2be2817397a301cdc", "commit":{...}}]
```

（注意：`gh api` 帶 `-f` 參數預設會把方法切成 `POST`，此端點只收 `GET`，會回 404——必須顯式加 `--method GET`，這是本次實測踩到的坑，記錄供腳本撰寫時參考。）

**`GET /repos/{owner}/{repo}/compare/{basehead}`**（同上來源），`basehead` 格式 `BASE...HEAD`，回應含 `files[]`（`filename`、`status`、`additions`/`deletions`/`changes` 等），文件明講：「The list of changed files is only shown on the first page of results, and it includes up to 300 changed files for the entire comparison.」本機實測：

```
$ gh api repos/tt-a1i/archify/compare/c826e6c3a7abad19c0f3cd1ca57207d54b1ad8de...main
{"ahead_by":41,"behind_by":0,"files":[".coderabbit.yaml", ..., "archify/SKILL.md", "archify/bin/archify.mjs", ...]}
```

`ahead_by: 41` 且 `files[]` 內含多筆 `archify/` 前綴路徑，證實：**目前 `apm.yml` 釘住的 commit，落後上游 `main` 41 個 commit，且落後的內容確實觸及 `subdir: archify` 目錄本身**（不是只有 repo 其他部分在動）。這是三種方案裡唯一能同時做到「量化落後幾個 commit」與「精確判斷是否影響指定 subdir」的做法。

### 5.3 GraphQL 批次查詢

**可以一次查多個 repo**，用 alias 語法。本機實測（同時查 `archify` 與 `impeccable` 兩個 repo 的 default branch 最新 commit）：

```
$ gh api graphql -f query='
{
  a: repository(owner:"tt-a1i", name:"archify") { defaultBranchRef { target { ... on Commit { oid committedDate } } } }
  b: repository(owner:"pbakaus", name:"impeccable") { defaultBranchRef { target { ... on Commit { oid committedDate } } } }
}'
{"data":{"a":{"defaultBranchRef":{"target":{"oid":"a07fa1d5b2a10cbea110c5a2be2817397a301cdc", ...}}},
          "b":{"defaultBranchRef":{"target":{"oid":"cb56ed6c19a07329a9fa0cd4e657bee040156593", ...}}}}}
```

單一 HTTP 請求拿回兩個 repo 的最新 commit，**8 筆外部套件可以合併成 1 次 GraphQL 請求**。速率限制（來源：[GraphQL rate limits](https://docs.github.com/en/graphql/overview/rate-limits-and-node-limits-for-the-graphql-api)）採點數制，「一般查詢僅 1 點」；一般使用者每小時 5,000 點；另有節點數上限「Individual calls cannot request more than 500,000 total nodes」，8 個 repo 的簡單欄位查詢遠低於此上限。GraphQL 的 `Commit.history` 可以用 `path` 篩選。實測 `repository(owner:"tt-a1i", name:"archify") { defaultBranchRef { target { ... on Commit { history(first: 2, path: "archify") { totalCount } } } } }` 回傳 `totalCount: 176`。

### 5.4 非 GitHub 來源

`apm.yml` 目前 12 筆套件（4 自製 + 8 外部）的 `source` 全部是 `https://github.com/...`，無 GitLab、Azure DevOps 條目。依任務規則「如 apm.yml 中確實出現才需要研究」，**本節略過非 GitHub 來源的研究**。

---

## 6. 建議做法

### 6.1 方案 A：呼叫 `apm`／`apm-go` 的 `marketplace outdated`

- **能偵測**：只對沒有 `ref`、只有 `version` range 的條目，比對上游符合 `tag_pattern` 的 tag。
- **漏掉**：有 `ref` 的條目全部跳過（3.1、3.3 實測，兩個 CLI 結果相同）。本 repo 8 筆外部套件都有 `ref`，所以全部漏掉。
- **相依工具**：`apm` 0.27.0 或 `apm-go` 0.3.0-rc.1。`apm` 0.30.0 是否改變這個行為：未確認。
- **判定**：排除。`apm-go marketplace check` 也不能補足：它把 8 個存在的 SHA 都回報成 not found（3.3）。

### 6.2 方案 B：`git ls-remote` 比對 `apm.yml` 裡的 `ref`

- 對每筆外部套件的 `source` 執行 `git ls-remote <url>`，取 default branch／各 tag 的 commit，與 `apm.yml` 記錄的 `ref` SHA 做字串比較。
- **能偵測**：repo 層級「有沒有任何新 commit／新 tag」。
- **漏掉**：完全無法判斷變動是否落在 `subdir` 內（5.1 節已用 `archify` 實測證實：`ls-remote` 只能說「repo 動了」，說不出「`archify/` 動了」）；也無法量化「落後幾個 commit」，只有布林式的「HEAD 變了沒」。
- **請求數與相依工具**：只需要 `git`，8 筆套件＝8 次外部程序呼叫；不需要 `gh`、不需要 GitHub 帳號、不吃 REST 額度，是三個方案中對執行環境要求最低的一個。

### 6.3 方案 C：`gh api`／GraphQL 依 subpath 精準查詢

- 先用一次 GraphQL 批次請求（5.3）拿到所有外部套件 repo 的 default branch 最新 commit，快速篩出「完全沒變」的套件（HEAD == 已釘的 `ref`，直接跳過）。
- 對「HEAD 有變」的套件，若該套件有 `subdir`，再用 `GET /repos/{owner}/{repo}/commits?path=<subdir>&sha=<branch>&per_page=1`（5.2）確認「變動是否真的觸及該子目錄」；若還要看清單，用 `GET /repos/{owner}/{repo}/compare/{pinned_sha}...{head}`（可選擇性用 `files[].filename` 是否以 `<subdir>/` 開頭做二次篩選）。
- **能偵測**：repo 層級變動、精確到 subdir 層級的變動、落後的 commit 數（`ahead_by`）、變動檔案清單——三個方案中最完整。
- **漏掉**：只是 commit-level diff，不天生知道「這算不算一個正式 release」；仍須自行決定要不要用 tag／release 資訊補充版本號。
- **請求數與相依工具**：1 次 GraphQL（8 個 repo 打包）＋僅對「有變動」的套件才追加 1-2 次 REST（`commits?path=` 與視情況的 `compare`），實測值：`archify` 一筆的完整查證只用了 1 次 GraphQL（共用）＋1 次 `commits?path=`＋1 次 `compare` ＝遠低於 60/hr（未認證）或 5,000/hr（已認證，本機 `gh` 已認證）的額度。需要 `gh` CLI（或直接呼叫 REST/GraphQL 端點，不一定要 `gh`），不需要本機安裝 `apm`。

### 6.4 比較表

| | 方案 A：`apm`／`apm-go` `marketplace outdated` | 方案 B：`git ls-remote` | 方案 C：`gh api`／GraphQL + subpath |
|---|---|---|---|
| 有 `ref` 的條目 | 跳過（實測） | 可以（比對 SHA） | 可以（比對 SHA，再視需要查 subdir） |
| repo 層級新版偵測 | 不適用 | 可以 | 可以 |
| subdir 精確偵測 | 不適用 | 不行（協定層級無檔案資訊） | 可以（`commits?path=`／`compare` 的 `files[]`） |
| 量化落後幾個 commit | 不適用 | 不行（只有布林） | 可以（`ahead_by`） |
| 相依工具 | `apm` 或 `apm-go` CLI | 僅 `git` | `gh` CLI 或直接呼叫 REST/GraphQL |
| 是否需要 GitHub 帳號／額度 | 否 | 否（git 協定） | GraphQL 需要認證；REST 未認證 60/hr，認證 5,000/hr |
| 8 筆套件所需請求數量級 | 不適用 | 8 次 git 協定呼叫 | 1 次 GraphQL（全部）＋僅對有變動者各加 1-2 次 REST |

### 6.5 建議方案：方案 C，以方案 B 的邏輯做第一層快速篩選

理由：

1. 本 repo 8 筆外部套件中有 2 筆（`show-me`、`archify`）用了 `subdir`，README.md 與 1.6 節的演進歷史都顯示這個 repo 對「精確版本」很在意（連 tag 都不信任、只信任 commit SHA）。方案 A、B 在 subdir 這件事上的能力天花板，跟 APM 官方工具鏈自己的天花板一樣低（2.3 節證據），**無法滿足「精確知道 subdir 是否真的變動」這個本 repo 特有的需求**。
2. 方案 C 的請求成本經實測驗證是最低的：先用 1 次 GraphQL 批次請求把 12 筆套件（或篩掉 4 筆自製後的 8 筆外部套件）的「HEAD 有沒有變」一次問完，未變動的套件完全不用再花任何 REST 請求；只有「HEAD 真的變了」的少數套件才需要額外 1-2 次 REST 呼叫去確認 subdir。這個「先 GraphQL 粗篩、再 REST 精查」的兩段式，本質上就是把方案 B 的「布林式 repo 層級檢查」當第一層 gate，再疊加方案 C 獨有的 subdir 精查能力，因此不需要把 A/B/C 當互斥選項，方案 C 本身已內含方案 B 的第一層邏輯。
3. 方案 A 已由實測排除：`apm marketplace outdated` 跳過全部 8 筆外部套件，並回報「全部是最新」（3.1）。
4. 唯一的代價是要寫一小段腳本邏輯（判斷有無 `subdir`、組 `path=` 參數），但這正是使用者要求的「寫一個腳本」本身，不是額外負擔；且腳本可以直接讀 `apm.yml` 的 `ref` 欄位當作「目前版本」，不需要處理 lockfile（4.2 節結論）。

---

## 7. 決策與實作

### 7.1 更新判定規則（使用者決定）

| 條目 | 有更新 | 有變動 | 錯誤 |
|---|---|---|---|
| 有 `version` | 上游有符合 `tag_pattern` 且較新的 tag | 不適用 | `version` 對應的 tag 不存在，或 tag 指向的 commit 不是 `ref` |
| 沒有 `version` | 上游 `plugin.json` 的 `version` 與 `ref` 時不同 | 內容路徑有新 commit，但 `plugin.json` 的 `version` 沒變 | 不適用 |

- 內容路徑：有 `subdir` 時用 `subdir`；沒有時用 `skills/` 與 `.claude-plugin/`。
- `plugin.json` 位置：`<subdir>/.claude-plugin/plugin.json`，或 `.claude-plugin/plugin.json`。

### 7.2 決策依據（2026-09-14 實測）

**有 `version` 的 4 筆**：`tag_pattern` 套入 `version` 後的 tag 都指向 `ref`（`git ls-remote --tags`，附註 tag 取 `^{}` 條目）。`impeccable` 上游有 `skill-v4.3.1`。其他 3 筆沒有較新的 tag。`archify` 在 `v2.16.0` 後有 41 個 commit，但沒有新 tag，依規則不算更新。

**沒有 `version` 的 4 筆**：上游都沒有 tag 或 release。

| 套件 | 上游 `plugin.json` `version` | 內容路徑 commit 數 | `plugin.json` 修改次數 |
|---|---|---|---|
| `web-quality-skills` | 2.0.0 | `skills` 自 2026-03-14 起 14 | 2 |
| `taste-skill` | 1.0.0（`CHANGELOG.md` 已寫 v2） | `skills` 自 2026-03-14 起 30 | 1 |
| `show-me` | 1.0.1 | `plugins/show-me` 共 4 | 2 |
| `beautify-github-readme` | 沒有 `plugin.json` | `skills` 共 9 | 不適用 |

`plugin.json` 的 `version` 不一定跟著內容更新（例如 `taste-skill`），所以只用它判斷會漏報。只看 commit 會把只改 `README.md` 的 commit（`beautify-github-readme` 目前的 1 個新 commit）算成更新。所以兩個訊號同時使用。

**`apm.yml` 自訂欄位**：在副本中加上 `x-watch-paths: [skills]`，`apm-go validate` 通過，`apm-go pack --claude-source-style url` 的兩份輸出與不加欄位時相同。這次選擇固定的預設路徑，沒有使用自訂欄位。

### 7.3 實作：`scripts/check_upstream_updates.py`

執行：`uv run scripts/check_upstream_updates.py [apm.yml 路徑]`。需要 `git` 與已登入的 `gh`。有「錯誤」時 exit code 為 1。

與 6.5 的差異：

- 沒有使用 GraphQL 批次篩選。沒有 `version` 的條目每筆直接呼叫一次 `compare/{ref}...HEAD`，8 筆套件的請求數差異很小。
- 有 `version` 的條目只用 `git ls-remote --tags`，不呼叫 REST。
- 內容 commit 數不計 merge commit。REST `commits?path=` 一次只篩一個路徑，會略過合併多個路徑變動的 merge commit；`git rev-list` 一次篩多個路徑時會計入。實測 `taste-skill`（ref `d124aaf`）：含 merge commit 時 REST 為 5、`git rev-list` 為 6；不計 merge commit 時兩者都是 4。

驗證：

- `scripts/test_check_upstream_updates.py`：18 個測試，以假的 `GitHub` 物件取代 `gh`／`git` 呼叫。執行 `uv run --no-project --with pytest --with pyyaml pytest scripts/test_check_upstream_updates.py`。
- 以較舊的真實 `ref` 建立測試用 manifest，確認「有更新」（`version` tag、`plugin.json`）、「錯誤」（ref 不符、非 GitHub 來源）。`web-quality-skills`、`show-me`、`taste-skill` 的內容 commit 數與 `git rev-list --no-merges` 的結果相同。

---

## 附錄：仍「未確認」的項目

1. APM 0.30.0 的 `apm marketplace outdated` 是否仍跳過有 `ref` 的條目——只在本機 `apm` 0.27.0 與 `apm-go` 0.3.0-rc.1 實測。
2. `apm-go marketplace check` 把存在的 SHA 回報成 not found 的原因——`github.com/apm-go/apm` 以 API 查詢回傳 404，沒有讀到原始碼。
3. GitHub 匿名（未認證）git 協定（`git ls-remote`／`git clone` over HTTPS）的具體速率限制數字——官方僅公告 2025-05-08 起會調整，未公布確切門檻。
4. GitHub REST API 條件式請求在**未認證**情境下，收到 304 是否仍計入速率限制——官方文件此句僅描述「已認證＋304」的豁免情境，未反向說明未認證情境。
5. `apm outdated`（consumer 版，非 `apm marketplace outdated`）在完全沒有 `apm.lock.yaml` 的專案上執行會如何表現（報錯或視為 0 筆）——未實際執行驗證。
