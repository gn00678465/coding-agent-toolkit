# verification-gate skill — 驗證紀錄與待解缺陷

記錄 `code-review:verification-gate` skill 抽離自 [old-coder](https://github.com/AmazingAng/old-coder) 之後的可用性驗證。日期：2026-08-25，平台：WSL2（Ubuntu on Linux 5.15）。

本文只記錄 **SKILL 本身的缺陷**，不含操作者（agent）自身的失誤與環境成本。

## 驗證進度與中斷點

### 已完成：demo 專案（negative control）

對 old-coder 內建的 `demo-rate-limiter` 執行：

- `gate` at HEAD → 12 層全綠，與 upstream `evidence.md` 逐項相符；在全新 clone 內重現 tree hash `5aa96ec5487c957c`。
- `evidence` on `86bfcf4...d45cc2f` → 產出 `.gate/source-state-binding/{evidence.md,baseline.md,red.md}`。
- RED 重建：6 個新測試在 base 全數失敗，且失敗輸出重現了被修掉的 fail-open 缺陷（舊 shell pipeline 在輸入缺失時仍 exit 0）。
- git 機械確認 spec（`86bfcf4`, 00:31:13）早於實作（`d45cc2f`, 00:36:40）。

**方法論限制**：demo 是自己人設計的乾淨專案，只能做確認／回歸，**不是發現工具**。真正的缺陷發現需要「非我挑選的目標 + 全新 context 的執行者」。

順帶發現（屬 old-coder demo，不是本 skill 的缺陷）：upstream `evidence.md` 的 Suite health 列宣稱 `10/10 consecutive runs`，但其 entry point 既無 suite-health 層也無重複迴圈 — 那個數字是 entry point 產不出來的。

### 中斷中：真實專案

- **目標**：`/home/madao/project/google-sheet-languages-model`，branch `rewrite/napi`
- **執行者**：herdr pane `w1:p4`（agent 名 `evalpanel`），kind codex，gpt-5.6-terra xhigh，全新 context
- **變更集**：`main...rewrite/napi`，base `7b9fb51`，HEAD `5ea0ff4`，121 檔，自行判定 Tier 3
- **給執行者的條件**（刻意不告知我預測的缺陷、不告知 spec 位置）：
  - 不修改任何產品程式碼、不執行 `git commit`、不動 `.gitignore`
  - 可在 `tools/` 新增 gate entry point 與 helper，可寫 `.gate/<scope>/`
  - 要求 2：遇到 SKILL.md 沒有定義、或定義不足以決定下一步的地方，逐項記下（哪一步、缺什麼、最後怎麼處理）
- **執行者已完成**：自行找到 `docs/specs/0001–0005`、提出規定的單一人類提問、讀完 5 份 spec 並抽出真實 Must NOT（不可在設定檔存金鑰／空 Sheet 或空本地資料未加 `--force` 不可覆寫／不得把文字以公式模式寫入／不得自動重試／core 不可有 I/O）

**中斷原因**：執行者停在等待授權。使用者已口頭授權（安裝 `cargo-llvm-cov`、`cargo-mutants`、`cargo-audit`、`cargo-deny`、`gitleaks`、property-testing 相依，並在 base worktree 安裝相依；**mutation 限縮變更檔**），但該授權**未送達** `evalpanel`。WSL 上 cargo 效能不足，決定換機重跑 — herdr session 不隨機器移動，實務上整輪重來。

## 已確認缺陷

### 1.【High】`changed_unit_command` 不可機械化

- **出處**：`assets/templates/evidence.md` 要求 header 欄位 `changed_unit_command`（「the command that produced the changed-unit list」）；`SKILL.md:88` 的取得方式是「derive from the diff: added/modified/deleted functions, methods, branches, exported symbols, config keys, endpoints, migration steps」。
- **問題**：沒有任何單一命令能從 diff 產出這份清單。跨語言的符號級抽取需要 per-language 工具，SKILL 未指定任何一個。
- **證據**：demo 實跑時我只能把該欄位填成「加上逐檔 `git show` 符號抽取」— 那是一段**人工流程的敘述**，不是命令。欄位契約在實跑第一次就被違反。
- **建議**：要嘛把欄位降級為「產生方式（命令或程序）」並允許敘述，要嘛在 `references/` 給出 per-ecosystem 的實際命令；不能兩者皆無卻要求填命令。

### 2.【High】reproducibility 沒有降級狀態

- **出處**：`SKILL.md:308-313` 要求「reproducible from the repo alone ... dev-tool versions pinned or recorded, one entry-point command, source state identified」；template 的 `source_state` 是必填。
- **問題**：intent 有三種宣告狀態（`confirmed` / `unconfirmed` / `absent`），layers 有三分法（`N-A` / `UNAVAILABLE` / `SUBSTITUTED`），**唯獨 reproducibility 只有「成立」一種**。工作樹為髒、無法釘選工具版本、base 無法取得（shallow clone）時，報告沒有一個誠實的落點；只能造假或整份不產出。
- **建議**：比照另外兩處補上明確的降級狀態與其語意（哪些結論在該狀態下不再成立）。

### 3.【Medium】git 事實層宣稱「always available」但無失敗路徑

- **出處**：`SKILL.md:81` 標題 `### From git — facts, always available in a repository`。
- **問題**：此陳述在下列情況為假 —（a）非 git 專案（template 自己就有 `no git: sha256 tree hash` 的路徑，兩處互相矛盾）；（b）shallow clone／歷史被截斷，`git log <base>..HEAD` 與「checkout base 到 worktree 跑 baseline」皆不可行。`references/entry-point.md` 只說「CI 必須抓完整歷史，而非跑弱化版 gate」— 那是一條指令，不是可回報的狀態。
- **建議**：修掉標題的絕對宣稱，並定義「baseline 無法建立」「RED 重建不可行」時的回報狀態（與缺陷 2 同一套機制）。

### 4.【High】單一生態系假設 — 多語言專案無定義

**這是唯一一項不是我從文本預測、而是由全新 context 的執行者實跑撞到的。**

- **出處**：`references/layers.md` 是 8 張 per-ecosystem 工具表（Python / JS-TS / Go / Rust / Java / Scala / SQL / Emacs Lisp），結構上假設「一個專案對應一張表」。
- **執行者原話**：
  > 技能未定義這些工具的精確版本，也未定義 Rust+Node 混合專案的 changed-line coverage 合併格式；我會採各工具當下可取得的穩定版、在 `tools/` 明確釘選，並以 Rust/JS 兩份 LCOV 分別核對 `main...HEAD` 的對應語言新增行。這項決策、其缺口與影響會逐條寫入 evidence。
- **具體缺口**（Rust + Node 混合專案）：
  - **changed-line coverage 無合併格式**：兩份 LCOV，Gate 表只有一格。分子分母怎麼加？分開列是否算通過該層？未定義。
  - **mutation score 無合併定義**：`cargo-mutants` 與 JS mutation 工具的 killed/total 不同量綱，未定義如何合併或是否允許分列。
  - **「單一 entry point」跨兩套建置系統的意義未定義**：一支腳本呼叫兩套是可行的，但 expected-layer manifest 的層名變得歧義 — `tests` 是一層還是兩層？其中一邊過、一邊掛，該層算什麼？
  - **工具版本釘選位置未定義**：SKILL 要求釘選，但 `requirements-dev.txt` / `package.json` / `Cargo.toml` 三處並存時，沒有規定的落點。
- **建議**：在 `references/layers.md` 補一節多生態系規則 — 每個生態系各自成層並在層名加後綴（如 `tests-rust` / `tests-node`），Gate 表允許同層分列，並明訂「任一生態系該層失敗即該層失敗」。

## 已排除：不是缺陷

以下三項我曾在中途誤報為卡死點，重讀原文後確認 SKILL 已有定義，**不要再提**：

- **changed-line coverage 未達標 × 反作弊規則 6**：規則 6 已定義行為 —「Failing gate blocks done… report the failure verbatim as the outcome」。不是死結。
- **RED 重建的粒度**：SKILL 已寫明 case by case，不是未定義。
- **flaky test**：SKILL 已定義後果 —「quietly invalidates the report」。

## 待補

- `plugins/code-review/skills/verification-gate/` 缺 `evals/evals.json`，與同 plugin 內的 `review-forge` 不對等。

## 換機後接續步驟

1. clone 本 branch，把 `plugins/code-review/skills/verification-gate/` 複製到目標專案的 `.agents/skills/`。
2. 於目標專案開新的 herdr eval panel（codex，全新 context），沿用上方「給執行者的條件」原文，**仍不告知**本文列出的任何缺陷。
3. 一併給出授權：安裝上列驗證用工具與 base worktree 相依，**mutation 限縮變更檔**。
4. 收下執行者的「未定義事項逐項紀錄」，與本文第 1–4 點比對，新項目補進本文。
