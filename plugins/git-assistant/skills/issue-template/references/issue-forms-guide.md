# GitHub 成熟開源專案之 Issue 模板架構研究與低摩擦表單設計指南

在當代開源軟體（Open Source Software, OSS）與企業級研發協作中，GitHub Issues 已從單純的錯誤追蹤清單，演進為專案治理、自動化分流（Triage）與開發者體驗（Developer Experience, DevEx）的核心樞紐。早期 GitHub Issues 因強調高度彈性而缺乏標準化結構，導致回報者提交的資訊往往殘缺不全，迫使維護者耗費大量時間於來回追問基本環境與重現條件，嚴重阻礙軟體維護效率。然而，當眾多成熟專案試圖透過繁複的模板強制收集資訊時，卻引發了另一項嚴峻的反效果，即填寫摩擦力過高所導致的回報放棄（Submission Abandonment）。本指南結合大型軟體工程實證研究數據，深度剖析 GitHub 頂尖開源專案（Vite、Next.js、Kubernetes、Astral Ruff 與 uv、Microsoft VS Code）之 Issue 格式架構，並整理出一套兼顧極低回報摩擦與高維度自動化分流的黃金標準模板設計規範。

---

## 一、開源專案 Issue 演進趨勢與表單放棄率之實證研究

### 1. 從自由格式 Markdown 到結構化 YAML Issue Forms 的典範轉移

GitHub Issue 模板技術經歷了兩個世代的架構演進：
* **第一代 Markdown 模板（.md）**：存放於儲存庫根目錄的 `ISSUE_TEMPLATE.md` 或 `.github/ISSUE_TEMPLATE/` 目錄下，利用 YAML Frontmatter 定義標題與預設標籤，並在內文中以 HTML 註解（`<!-- ... -->`）提示填寫方向。然而，Markdown 作為標記語言，其最大缺陷在於缺乏結構約束力，回報者可隨意刪除預設標題、改寫段落順序，甚至清空整份模板直接輸入無結構文字，導致依賴固定格式運作的自動化工作流失效。
* **第二代結構化 YAML Issue Forms（.yml / .yaml）**：運用 GitHub Form Schema 定義嚴格的網頁表單元件，包含單行輸入框（`input`）、多行文字區（`textarea`）、下拉選單（`dropdown`）、核取方塊（`checkboxes`）與說明文字（`markdown`）。表單送出時，系統強制將各欄位轉換為具固定 `### 標題` 的標準化 Markdown 內文，使回報者無法破壞結構，GitHub Actions 便能精準擷取欄位值並自動分派標籤。

### 2. 實證數據揭示的雙面刃效應：解決時間縮短 vs. 填寫放棄率

* **正面效益**：在針對 101 個大型 GitHub 開源專案、350 份模板與超過 190 萬筆 Issues 的實證分析中，高達 99% 的活躍專案已導入 Issue 模板，且採用結構化模板的專案在**問題解決時間（Resolution Time）**與**無效來回討論評論數（Discussion Comments）**上皆呈現統計顯著的下降。
* **負面衝擊（填寫放棄率）**：導入模板後，專案每月的 Issue 與 PR 提交總量往往出現明顯下滑。調查證實，當模板包含過多且無關的資訊要求時，會形成高昂的認知門檻，導致回報者中途放棄提交（Submission Abandonment）。
* **核心欄位邊際貢獻度**：實證調查與迴歸分析一致證明，真正對縮短 Bug 解決時間具備顯著加速效果的核心要素，僅有**「重現步驟（Steps to Reproduce）」**與**「錯誤堆疊 / 日誌（Stack Traces / Logs）」**。模板中每增加一個非核心的必填欄位（`validations: required: true`），都會線性推升放棄風險，卻幾乎無法為除錯帶來額外效益。

---

## 二、專案問題分流架構：Bug、Feature 與跨類別路由機制

成熟專案將 Issue Tracker 視為多層次的入站流量路由器（Inbound Traffic Router），透過 `.github/ISSUE_TEMPLATE/` 隔離非工程訴求：

### 1. 入口層攔截：透過 `config.yml` 隔離非工程問題

* **關閉空白 Issue**：設定 `blank_issues_enabled: false`，強制所有外部回報者必須選擇特定模板，防止無上下文的垃圾 Issue 污染追蹤清單。
* **外部導流連結（`contact_links`）**：
  * **技術問答 / 使用求助**：導流至 GitHub Discussions、Discord 或 Stack Overflow。
  * **資安漏洞（Security Vulnerabilities）**：引導至 GitHub 私密通報管道（如 `https://github.com/OWNER/REPO/security/advisories/new`），嚴防公開洩漏零日漏洞。

### 2. 四大核心問題分類與資訊收集邊界

| Issue 分類類別 | 代表性檔案命名範例 | 預設標籤（Labels） | 核心資訊收集目標（最小集合） | 生命周期處置策略 |
| :--- | :--- | :--- | :--- | :--- |
| **Bug Report**（錯誤回報） | `1-bug-report.yml` | `bug`, `pending-triage` | 1. 現象與預期行為落差<br>2. 最小可重現方式（MRE）<br>3. 錯誤日誌與執行環境（選填/自動包裹） | 自動化 Bot 或維護者進行重現驗證；缺乏重現資訊則標記 `info-needed` 並定期關閉。 |
| **Feature Request**（功能提案） | `2-feature-request.yml` | `enhancement`, `needs-discussion` | 1. 欲解決的實際痛點與場景<br>2. 期望的解決方案或 API 行為<br>3. 替代方案與貢獻意願（選填） | 避免初期索取底層實作細節；以 👍 (Upvote) 累積熱度，或轉移至 GitHub Discussions Ideas 專區。 |
| **Documentation**（文件修正） | `3-docs.yml` | `documentation` | 1. 文件缺漏或誤導之處<br>2. 建議修改內容或正確範例 | 保持極度精簡，不要求系統環境或重現步驟；鼓勵貢獻者直接提 PR。 |
| **Task / Question**（任務/特定問答） | `4-task.yml` | `chore`, `task` | 1. 內部重構目標、發佈檢查清單（Checklist） | 專案內部追蹤或發佈回歸測試清單。 |

---

## 三、五大成熟開源專案 Issue 格式對比

| 評估維度 | Vite (`vitejs/vite`) | Next.js (`vercel/next.js`) | Kubernetes (`kubernetes/kubernetes`) | Astral (`astral-sh/ruff`, `uv`) | Microsoft VS Code (`microsoft/vscode`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **模板檔案架構** | `bug_report.yml`, `feature_request.yml`, `docs.yml` + `config.yml` | 數字前綴排序：`1.bug_report.yml`, `3.feature_request.yml` | `bug-report.yaml`, `enhancement.md` | `1_bug_report.yaml`, `feature_request.yml`, `3_question.yaml` | `bug_report.yml` + `config.yml` 結合 IDE 內建 Report Issue 精靈 |
| **環境資訊收集** | 手動執行 `npx envinfo --system` 貼上 | CLI 診斷指令輸出或崩潰日誌自動生成貼上 | 必填僅 `$ kubectl version`，CRI/CNI/雲端平台皆為選填 | 單行版本輸出與 `pyproject.toml` 設定片段貼上 | **全自動遙測預填**（版本、OS、外掛清單全自動採集） |
| **重現機制要求** | **極高**（強制要求 GitHub Repo 或 StackBlitz 連結） | **高**（要求提供可重現 Repo 連結與步驟） | **中**（文字描述最小且精確的重現步驟與指令） | **低摩擦**（直接於文字框貼上觸發之程式碼片段） | **中低**（條列步驟、程式碼片段與內建截圖標註） |
| **分類與防呆** | 底部設有 **7 項必填核取方塊（Validations）** 作為守門員 | 設有 Area 與 Stage 選擇器，且 Area 包含 **Not sure** 選項 | 頂部提醒資安漏洞私密通報，底部折疊非核心環境欄位 | 嚴格區分 Bug、Feature 與 Question 三類模板入口 | 內建相似 Issue 即時搜尋與 Extension Bisect 擴充套件二分法排查 |
| **主要優勢** | 沙盒重現極大化除錯速度，有效過濾下游框架問題 | CLI Fatal Error 直接印出帶模板參數之回報網址，模組路由極精準 | 克制必填欄位數量，避免龐大基礎設施參數嚇跑回報者 | 填寫時間極短，無須離開頁面建立外部儲存庫，放棄率極低 | 手動環境查閱成本歸零，並能自動路由至正確擴充套件庫 |
| **潛在缺點** | 7 項核取方塊引發盲目勾選；無法抽離沙盒之企業 monorepo 問題難提交 | 對於簡單問題仍要求完整 Repo 連結，門檻偏高 | 若問題依賴特定 CNI/CRI 而未填，需二次追問 | 僅適用於純文字與 CLI 輸入輸出之工具，不適用於複雜 UI | 建置客戶端回報器之工程成本高；擴充套件過多時需處理認證與負載限制 |

---

## 四、避免回報者放棄填寫之核心設計工程學（60 秒填寫原則）

1. **必填欄位預算制與雙欄合併術**：
   * 將必填限制在 2~3 個以內。
   * 將「發生了什麼現象」與「原本預期行為」合併為單一 `textarea`（標題定為 `問題現象與預期行為 (What happened & Expected behavior)`），使用者只面對「問題描述」與「如何重現」兩個核心文字框，大幅降低認知超載。
2. **運用 `render` 自動語法包裹**：
   * 在 `textarea` 設定 `render: text`、`render: shell`、`render: bash` 或 `render: yaml`。
   * GitHub 會在表單送出後自動包裹反引號代碼塊，免除回報者手動排版的困擾與格式錯亂。
3. **以 `type: markdown` 取代儀式性核取方塊牆**：
   * 移除底部繁複的多選必填確認清單（如「已搜尋重複問題」、「已閱讀文件」）。
   * 改於表單頂部放置單行 `type: markdown` 提示。該元素僅在填寫介面呈現，**送出後完全不污染 Issue 內文**。
4. **提供彈性重現途徑與「不確定（Not sure）」逃生口**：
   * 允許 3 種層次的重現方式：(1) 幾行可複製的最小程式碼片段、(2) 清楚的 1-2-3 操作步驟、或 (3) StackBlitz / GitHub 最小儲存庫連結。
   * 分類 dropdown 務必將首項設為 `不確定 / 通用 (Not sure)`，避免使用者因不熟悉專案內部架構而卡關放棄。
5. **規避 GitHub Issue Forms 底層限制與陷阱**：
   * **禁用保留字 `None`**：`dropdown` 的 options 若包含 `None` 且 `required: true`，會觸發 schema 驗證錯誤導致模板失效。應改用 `不確定 / 通用 (Not sure)`。
   * **嚴格禁止 `---` 分隔線**：不可仿照舊版 Markdown frontmatter 在 YAML 標頭與 body 之間加入 `---`，會導致解析器報錯。
   * **私有庫必填降級特性**：GitHub 在 Private / Internal 儲存庫會刻意將 `required: true` 自動降級為選填，應改用 `value` 預填骨架引導內部成員。
   * **公開模板避免寫死 `projects`**：若提單者無該 Project 寫入權限，會靜默失敗；應改用 `labels` 搭配 GitHub Actions Auto-add 工作流匯入看板。
   * **明確唯一的 `id`**：每個欄位均需設置簡潔的 `id`，便於 CLI 或錯誤頁面動態拼裝 URL Query Parameter（`?template=1-bug-report.yml&version=v1.2.0`）實現一鍵預填。
