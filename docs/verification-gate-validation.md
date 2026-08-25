# verification-gate skill — 驗證紀錄與待解缺陷

記錄 `code-review:verification-gate` skill 抽離自 [old-coder](https://github.com/AmazingAng/old-coder) 之後的可用性驗證。日期：2026-08-25，平台：WSL2（Ubuntu on Linux 5.15）。

本文只記錄 **SKILL 本身的缺陷**，不含操作者（agent）自身的失誤與環境成本。

## 驗證進度

### 已完成：demo 專案（negative control）

對 old-coder 內建的 `demo-rate-limiter` 執行：

- `gate` at HEAD → 12 層全綠，與 upstream `evidence.md` 逐項相符；在全新 clone 內重現 tree hash `5aa96ec5487c957c`。
- `evidence` on `86bfcf4...d45cc2f` → 產出 `.gate/source-state-binding/{evidence.md,baseline.md,red.md}`。
- RED 重建：6 個新測試在 base 全數失敗，且失敗輸出重現了被修掉的 fail-open 缺陷（舊 shell pipeline 在輸入缺失時仍 exit 0）。
- git 機械確認 spec（`86bfcf4`, 00:31:13）早於實作（`d45cc2f`, 00:36:40）。

**方法論限制**：demo 是自己人設計的乾淨專案，只能做確認／回歸，**不是發現工具**。真正的缺陷發現需要「非我挑選的目標 + 全新 context 的執行者」。

順帶發現（屬 old-coder demo，不是本 skill 的缺陷）：upstream `evidence.md` 的 Suite health 列宣稱 `10/10 consecutive runs`，但其 entry point 既無 suite-health 層也無重複迴圈 — 那個數字是 entry point 產不出來的。

### 已完成：真實專案（本輪的實際發現來源）

- **目標**：`/home/madao/projects/google-sheet-languages-model`，branch `rewrite/napi`
- **執行者**：herdr pane `w1:p4`（label `gslm-eval`），kind codex，gpt-5.6-terra xhigh，全新 context
- **變更集**：`main...rewrite/napi`，base `7b9fb51`，HEAD `5ea0ff4`，121 檔，執行者自行判定 Tier 3
- **條件**：不改產品碼／不 commit／不動 `.gitignore`；可寫 `tools/` 與 `.gate/<scope>/`；要求 2 = 逐項記下 SKILL 未定義或定義不足之處
- **未告知**：本文列出的任何缺陷、spec 位置、我的任何預測
- **耗時**：36 分 05 秒，單一 turn

**結果**：gate 結論 **BLOCKED**。

- 通過：harness self-test、source state、build、109 Rust + 38 Node tests、types、fmt/clippy、Rust 與 JS coverage 蒐集
- 阻擋：changed-line coverage `2410/2839`，429 條新增可執行行未覆蓋，entry point exit 1
- 因 fail-first 而未執行：mutation、property、complexity、supply-chain/secrets、real execution、suite health、adversarial（**7 層**）

產出：`.gate/rewrite-napi/{EVIDENCE.md,VERIFICATION-GATE-GAPS.md,baseline.md,red.md,final-gate.log,run/}`、`tools/verification-gate/{gate.sh,self_test.sh,source_state.sh,changed_lines.mjs,rust_coverage.sh,…}`。

## 可用性結論（skill 有效的部分）

這輪是端到端跑通的，以下機制在真實壓力下**成立**，不要動它們：

- **fail-first entry point + manifest 稽核**：對一個 121 檔的跨語言重寫，gate 沒有橡皮圖章，而是在一個真實缺口（429 行未覆蓋）上硬停。這是 skill 的核心宣稱，成立。
- **反作弊規則**：執行者未弱化任何檢查、未把未執行的層報成 pass、失敗逐字回報。規則 6 的行為在實跑中被證實不是死結。
- **三分法詞彙**：`UNAVAILABLE` 與 `SUBSTITUTED may never be a pass` 被正確理解並使用（Rust branch coverage 被標 `UNAVAILABLE` 而非降級成 pass）。
- **negative control 紀律**：執行者為 orchestration、grep、changed-line、source-state 各自建了控制組並記錄。
- **單一人類提問**：一問即取得 `intent_status: confirmed`，並從 spec 抽出 6 條含負向約束的意圖清單 — 這是 diff 產不出來的部分。
- **artifact 佈局與 isolation**：worktree 隔離、產品碼零變更、`.gitignore` 未動。

缺陷全部集中在**邊界的欠定義**，不是核心機制失效。

## 已確認缺陷

編號 1–4 為前一輪已記錄，本輪補上實跑證據；5 以後為本輪新增。

### 1.【High】`changed_unit_command` 不可機械化 — 且可被「合規地」填成無意義的值

- **出處**：`assets/templates/evidence.md:19` 要求 header 欄位 `changed_unit_command`；`SKILL.md:88` 的取得方式是「derive from the diff: added/modified/deleted functions, methods, branches, exported symbols, config keys, endpoints, migration steps」。
- **原問題**：沒有任何單一命令能從 diff 產出符號級清單，SKILL 也未指定任何 per-language 工具。demo 實跑時我只能把該欄位填成一段人工流程敘述。
- **本輪新證據（更糟）**：執行者把該欄位填成 `git diff --find-renames --name-status 7b9fb51...5ea0ff4` — 一個**路徑級**命令。欄位的字面契約（「一個命令」）滿足了，但欄位存在的理由（rows 在**單位**粒度上不可挑選）消失了，而報告讀者無從分辨。執行者在 gaps 清單中同步坦承「不聲稱逐函式 test mapping」，但那句話在 EVIDENCE 主體之外。
- **判定**：這個欄位目前**鼓勵**一個看起來合規、實際降級的填法。
- **建議**：欄位改為兩格 —「命令」與「粒度（symbol / path / module）」，並規定粒度不是 symbol 時 Table 1 必須標示。或在 `references/` 給出 per-ecosystem 的符號抽取命令。

### 2.【High】reproducibility 沒有降級狀態

- **出處**：`SKILL.md:308-313`；template 的 `source_state` 為必填。
- **問題**：intent 有三態（`confirmed`/`unconfirmed`/`absent`），layers 有三分法（`N-A`/`UNAVAILABLE`/`SUBSTITUTED`），**唯獨 reproducibility 只有「成立」一種**。
- **本輪證據**：見缺陷 6 與 12 — 執行者被迫自行發明兩個狀態（`NOT EXECUTED`、`UNVERIFIED, not N-A`）與一個 header 欄位（`final_run`）才能誠實地把報告寫完。三次自創都落在同一個空缺上。
- **建議**：比照另外兩處補上明確的降級狀態與語意（哪些結論在該狀態下不再成立）。

### 3.【Medium】git 事實層宣稱「always available」但無失敗路徑

- **出處**：`SKILL.md:81` 標題 `### From git — facts, always available in a repository`。
- **問題**：（a）非 git 專案（template 自己就有 `no git: sha256 tree hash` 路徑，兩處矛盾）；（b）shallow clone／歷史截斷時 `git log <base>..HEAD` 與 base worktree baseline 皆不可行。`references/entry-point.md:144` 只說「CI 必須抓完整歷史」— 那是指令，不是可回報的狀態。
- **本輪證據**：執行者的 source-state negative control 明確做了「depth-1 clone 被拒為 shallow history」。**檢查會拒絕，但 skill 沒定義被拒之後報告該長什麼樣。** 本次目標倉庫歷史完整，所以未走到那條路徑。
- **建議**：修掉標題的絕對宣稱，並與缺陷 2 共用同一套降級狀態機制。

### 4.【High】單一生態系假設 — 多語言專案無定義

- **出處**：`references/layers.md` 是 8 張 per-ecosystem 工具表，結構上假設「一個專案對應一張表」。
- **本輪證據（全部命中，且比預測更嚴重）**：Rust + napi-rs + Node 混合專案下 —
  - **沒有任何現成命令可用**：執行者必須自行寫 `rust_coverage.sh`（fresh target、`-C instrument-coverage`、Rust tests + `build:debug` + Node tests、`llvm-profdata merge`、`llvm-cov export` 同時引用 workspace test objects 與 NAPI shared library）與 `changed_lines.mjs`（自行合併 Rust/JS 兩份 LCOV 並比對 diff 新增行）。**skill 的整個 changed-line coverage 層在此專案上是從零手造的。**
  - 第一版純 Rust collector **完全沒觀測到經由 Node 載入 NAPI 後執行的程式碼** — 亦即照 `references/layers.md` 的 Rust 列直接做，會得到一個系統性低估、卻看起來正常的覆蓋率數字。
  - `cargo llvm-cov --branch`（`layers.md:46`）在 pinned stable 1.97.1 上不可用（需 nightly `-Z coverage-options=branch`），reference 未給替代或狀態。
- **建議**：`references/layers.md` 補一節多生態系規則 — 每生態系各自成層並加後綴（`tests-rust`/`tests-node`），Gate 表允許同層分列，明訂「任一生態系該層失敗即該層失敗」；並補一段「跨語言邊界（FFI/NAPI/JNI）的覆蓋率蒐集必須涵蓋跨邊界執行路徑，否則該層記為 `SUBSTITUTED`」。

### 5.【High】fail-first entry point 與「每層都要有狀態」互斥 — gate 只有一次過關才可能完工

- **出處**：`SKILL.md:174`「Run every applicable layer」、`SKILL.md:437` Completion Criteria「every applicable layer ran, or is recorded as `N-A`/`UNAVAILABLE`/`SUBSTITUTED`」；`references/entry-point.md:3`「fails on the first broken one」。
- **問題**：兩條規則在**任何一次失敗的 gate** 上直接衝突。第一個壞掉的層之後的所有層都沒跑，而它們不是 `N-A`（surface 存在）、不是 `UNAVAILABLE`（工具都裝好了）、更不是 `SUBSTITUTED`（沒有東西替代）。Completion Criteria 因此**恰好在 gate 發揮作用時無法滿足**。
- **本輪證據**：17 列 Gate 表中 **7 列**是「not run — fail-first entry point stopped at coverage」。執行者自行發明狀態 `NOT EXECUTED (required fail-first behavior)`，並在 gaps 中寫明「skill 沒說要否另跑 mutation 再拼回 evidence」，最後選擇遵循較具體的 fail-first reference。
- **判定**：這是本輪最尖銳的結構缺陷，且 demo 永遠測不到 — demo 12 層全綠，一次也沒觸發。
- **建議**：補第四狀態 `NOT REACHED (gate stopped at an earlier layer)`，明訂它既非 pass 亦非 unavailable；並明確裁決「失敗後可否為了資訊價值另跑後續層」— 若可，規定那些數字必須標為非 final-run 來源。

### 6.【High】gate 自身的產出使 source-state 檢查必然失敗

- **出處**：`references/entry-point.md:140-142`「the provenance computation must refuse to emit a state when the working tree is dirty」；`SKILL.md:287-291` entry point 與 helper **必須**落在產品路徑 `tools/`；`SKILL.md:412-424` artifacts 落在 `.gate/`，且「do not edit `.gitignore` unless asked」。
- **問題**：三條規則合起來保證 —「首次執行 gate 必定產生 non-ignored untracked 檔案，因此 source-state 檢查必定拒絕出狀態」。skill 沒有任何一句處理自己造成的髒污。
- **本輪證據**：執行者被迫在 `source_state.sh` 內自建白名單（`.agents/*`、`.gate/rewrite-napi/*`、`tools/verification-gate/*`），並在 gaps 首項寫明「skill 要拒絕非忽略 untracked 檔，又要求持久 gate/tool/artifact；沒有說如何讓新建 verifier 本身不把 source-state 永久弄髒」。白名單是它自己發明的，skill 無此概念。
- **建議**：在 source-state 契約中明訂 verifier 自身路徑的排除規則（白名單或必須先 commit），並說明排除本身如何在 EVIDENCE 中揭露。

### 7.【High】changed-line coverage 的「changed line」沒有定義 — gate 頭號數字的分母未定

- **出處**：`SKILL.md:183`「every changed/added line executed by a test」；template line 75 `<covered>/<total> changed lines`。
- **問題**：diff 的新增行包含註解、宣告、屬性、空白、型別定義等**不可執行行**；LCOV 只對編譯器判定為可執行的行發 `DA`。skill 沒有規定分母是「diff 新增行」還是「diff 新增行 ∩ 有 coverage mapping 的行」，也沒有規定如何區分「本來就不可執行」與「coverage mapping 漏掉」。這兩者在數字上不可分辨，而後者是靜默的假綠。
- **本輪證據**：執行者必須自行定義門檻為「final LCOV 有 DA 的新增 Rust/JS executable lines」，並在 gaps 中記明 skill 未指示如何區分兩者。整個 `2410/2839` 的意義取決於它自訂的這條規則。
- **建議**：template 的該列拆成 `<covered>/<executable>`（並要求另記 `<diff 新增行總數>`），並規定「diff 新增但無 coverage mapping 的行」必須單獨列出，不得併入不可執行行。

### 8.【High】baseline 在架構替換型變更下無定義

- **出處**：`SKILL.md:91`「check out `base` in a worktree and run the suite」；template `## Baseline` 為必填。
- **問題**：當變更本身是**技術棧替換**時，base 上根本不存在對應的 suite。skill 只設想「base 有些測試已經在紅」，沒設想「base 沒有這個 suite」。
- **本輪證據**：base `7b9fb51` 是純 TypeScript 專案，沒有 Cargo workspace；`cargo test --workspace` 在 base 上連 manifest 都沒有。執行者只在 base 跑其原有的 `pnpm test`（27/27 綠），並把 Rust baseline 標為「不存在」。這個處理是對的，但是它自己決定的。
- **建議**：明訂「base 缺少對應 suite」時 baseline 的記法，並說明此時「zero NEW failures」這條線實際保證了什麼、沒保證什麼。

### 9.【High】RED 重建在全新平台下全面退化為 collection error，而 skill 沒有失效門檻

- **出處**：`SKILL.md:235-261`；`SKILL.md:254`「A test that fails on import or collection is a weaker RED than an assertion failure. Note it rather than counting it the same.」
- **問題**：skill 只要求「註記」較弱的 RED，沒有規定**當比例達到多少時 RED 整體不再構成證據**。當變更引入全新平台時，所有新測試在 base 上都會因為缺 entry point／manifest 而在 collection 掛掉 — RED 全紅，但那個紅只證明「base 沒有這個專案」，不證明任何測試有斷言能力。
- **本輪證據**：9 個新 JS 測試在 base 全部 import/collection 失敗（base 無 `packages/gslm/index.js`）；Rust integration tests 全部因缺 Cargo manifest 在執行前就被擋；嵌在新模組內的 Rust 單元測試根本無法複製。執行者如實標記「全列為弱 RED，不把 rc=1 誇稱成 regression assertion」，並在 gaps 中指出 skill 未給這種情況的 assertion-level RED 做法。
- **判定**：在大型重寫上，RED 這一層目前**結構上無法產生證據**，但報告仍可照常填出一張全紅的表。
- **建議**：明訂「當新測試在 base 全數為 collection 失敗時，RED 記為 `NOT EVIDENCE (base lacks the platform)`」，並提供替代做法（例如把新測試對 HEAD 的一次性 throwaway mutant 當作斷言能力證明）。

### 10.【High】Real execution 層對需要外部憑證或副作用的變更不可達

- **出處**：`SKILL.md:187` Real execution 為 always-on 層；Tier 3 另要求 adversarial pass。
- **問題**：當被驗證的變更本體就是**第三方 API 客戶端**時，「真的跑一次」需要憑證與一個可寫的外部資源。skill 沒有規定 verifier 可否取得憑證、可否對外部產生副作用，也沒有規定不可得時該層的狀態。
- **本輪證據**：目標的 live TLS/Google 測試被標為 ignored，使用者未提供憑證與可寫 Sheet。執行者拒絕猜測或碰外部 Sheet，預定退回本機 `gslm --version` + schema parse，並明確拒絕讓 mock server tests 頂替 live API/TLS。它在 gaps 與 structural blind spots 兩處都記了。
- **建議**：明訂 real execution 在「需要外部憑證／會產生外部副作用」時的預設 — 不得執行，記為 `UNAVAILABLE`，且必須在 structural blind spot 具名。

### 11.【High】「每個新依賴都要對應 intent 的正當性」對真實依賴樹不可滿足

- **出處**：`SKILL.md:188`「every new dependency must trace back to a justification in the intent record」；`references/layers.md:117-118` 重申「each one needs a one-line justification in the intent record」。
- **問題**：規範沒有區分 **direct 與 transitive** 依賴。任何真實變更引入的 transitive 依賴以百計，而人類寫的 spec/ADR 描述的是架構選擇，不會逐套件列理由。skill 也沒說可否從 manifest 反推正當性、反推算不算 intent。
- **本輪證據**：執行者在 gaps 中明確拒絕「自行替每個 dependency 編造正當性」— 這正是規則寫成現況時唯一能通過的做法，也正是規則想防的事。
- **建議**：把要求限縮到 direct dependencies，transitive 改為「鎖檔差異全量記錄 + audit 結果」，並明訂 spec 未逐項列理由時的合規記法。

### 12.【High】capability diff 與「本 skill 不做 code review」的 scope boundary 互相牴觸

- **出處**：`SKILL.md:30-31`「This skill **does not review code**. It does not look for defects」；`SKILL.md:188` 與 `references/layers.md:108` 要求「eyeball the capability diff: did the change start using network / subprocess / filesystem / env it didn't before?」（工具欄寫明 `manual diff review`）。
- **問題**：「人工檢視 diff 判斷是否新增了未被要求的能力」就是讀 code 找可疑之處。兩條規則直接對撞，skill 沒有給界線。
- **本輪證據**：執行者在 gaps 中原文指出這一點，並自行劃線 —「僅從已確認 specs/ADRs 和測試名稱列 failure model，未以 implementation inspection 作 code review；未證實的 capability 仍列 structural blind spot」。
- **建議**：改為機械化定義（例如以 import/依賴清單、manifest 權限、syscall 類別的差異為準），或明確把 capability diff 標為 scope boundary 的具名例外並說明允許到什麼程度。

### 13.【Medium】現成工具的 warning 無處理規定

- **出處**：`SKILL.md:203-219` Checker note 只規範 crash、unreadable input、unexpected exit code、silently skipped item；`references/entry-point.md:14-22` 同。
- **問題**：現成工具 exit 0 但輸出明確削弱結果可信度的 warning 時，該層算 pass 還是 fail，未定義。
- **本輪證據**：final `llvm-cov export` exit 0，同時輸出 `warning: 14 functions have mismatched data`。執行者選擇保留工具的非零語意（記為 pass）、把 warning 與其降低的 confidence 寫進 EVIDENCE。
- **建議**：明訂「已知會削弱測量有效性的 warning 必須在該層 Result 欄逐字保留」，並給出何時應升級為該層失敗的判準。

### 14.【Medium】驗證工具自身在產品目錄留下檔案，無「執行後再驗 source state」規定

- **出處**：`references/entry-point.md:127-142` 的 self-tests 全部規定在「real layers 之前」執行。
- **問題**：沒有任何規定要求 verifier 不得在產品路徑產生 non-ignored 暫存檔，也沒有要求在 run 結束後重驗 source state。前置檢查通過、run 過程弄髒、報告仍宣稱一個乾淨的 source state — 這條路徑是開的。
- **本輪證據**：c8 載入 instrumented NAPI library 後在 `packages/gslm/` 留下 8 個 `default_*.profraw`。執行者自行改導 `LLVM_PROFILE_FILE`、刪除該 8 檔、重跑 entry point，並**自行加上**「最終後再次以 source-state script 驗證 exact HEAD」。
- **建議**：把 source-state 檢查明訂為 run 前後各一次，並要求 verifier 產生的任何暫存輸出必須落在 `artifact_root` 內。

### 15.【Medium】git ordering 的分類與可信度未定義

- **出處**：`SKILL.md:90`「Ordering | whether test files were committed before the implementation they cover」。
- **問題**：只給了二分法。實務上大量出現的三種情況沒有歸屬：測試與實作同一個 commit、整檔新增（無「之前」可言）、spec 在實作之後才進入歷史。
- **本輪證據**：執行者以 commit/file-add chronology 記錄「tests 多為同時或後於 implementation」，並發現 `spec 0004` 也在實作後入歷史，最後選擇不宣稱 test-first。
- **建議**：定義四類（before / same-commit / after / whole-file-add）與各自可支持的結論強度。

### 16.【Medium】Complexity budget 是 always-on 層，卻沒有工具、沒有預算來源、沒有 fallback

- **出處**：`SKILL.md:186` 列於 always-on 層表；`SKILL.md:437` Completion Criteria 要求它必須有狀態。
- **問題**：`references/layers.md` 的 **8 張生態系表與延伸清單全部沒有 complexity 這一列**，也沒有任何工具。SKILL.md 只給敘述性判準（「需要一段話解釋就拆開」），無法進入 fail-closed entry point，因此與「every number came from one fresh run of a persisted entry point」直接衝突。
- **本輪證據**：執行者只能預定用 clippy 的結構性 proxy 標 `SUBSTITUTED` 並列出盲點；在 gaps 中記明「specs 沒有數值預算，project 也沒有既有 analyzer，skill 沒有定義可接受的 fallback」。
- **建議**：要嘛在 `references/layers.md` 補 per-ecosystem 的複雜度工具與預設閾值，要嘛把此層降級為非 always-on 的敘述性檢查並移出 entry point 的 manifest。

### 17.【Medium】verifier 可否為驗證安裝專案沒有的框架／runner，未定義

- **出處**：`SKILL.md:399-405` 只覆蓋 test runner、linter、type checking 三者的補齊；Tier 3 要求 property-based tests；`references/layers.md:109` 要求 randomized order。
- **問題**：專案沒有 property framework 或 shuffle runner 時，verifier 可否安裝？安裝後那些 property 算不算專案測試、要不要計入 suite？未定義。
- **本輪證據**：執行者依本輪的預先授權在 `tools/verification-gate` pin 了 fast-check 並寫了兩個固定種子 property（200 examples），但在 gaps 中記明 skill 未指示這是否被允許、也未指示怎麼計入。suite health 則選擇「不安裝、不假裝 randomization」，記為 unverified。
- **判定**：本輪之所以沒卡住，是因為我事先給了授權；**skill 自身沒有這條路**。
- **建議**：把 `SKILL.md:399` 的補齊清單擴到 property framework 與 shuffle runner，並明訂 verification-only 相依的落點與其在 EVIDENCE 的揭露方式。

### 18.【Medium】多平台／多目標 spec 在單機驗證下的狀態未定義

- **出處**：三分法 `N-A` / `UNAVAILABLE` / `SUBSTITUTED`。
- **問題**：spec 明確要求 N 個平台產物，而驗證只在單一主機上進行時，該記 `N-A`（不對，surface 存在）、`UNAVAILABLE`（不精確，工具沒缺）、還是 fail？未定義。
- **本輪證據**：spec 0001 要求 7 個 native target artifacts、registry install 延至 beta。執行者拒絕標 `N-A` 也拒絕標 pass，自行發明第三個詞 `UNVERIFIED, not N-A`。
- **建議**：併入缺陷 2/5 的狀態機制，明訂「surface 存在但本次執行環境無法覆蓋」的狀態。

### 19.【Medium】「所有數字來自單一 final fresh run」與 baseline／RED 必須在 base 執行互相牴觸

- **出處**：`SKILL.md:306-307`「All numbers must come from one final fresh run」；template line 67 同；但 baseline（`SKILL.md:91`）與 RED（`SKILL.md:241`）**本質上只能在 base worktree 產生**。
- **問題**：規則寫成絕對式，卻有兩個必要區塊必然違反它。也沒有規定 gate 失敗時可否呈現 preflight 診斷數據。
- **本輪證據**：執行者自行把規則限縮為「只有 Gate 表的數字須來自 final run」，並把 baseline/RED 標為前置必需步驟，明確不把先前的 coverage/preflight/mutation 結果混入 final score。
- **建議**：把該規則的作用域明寫為「Gate（final fresh run）表」，並定義 preflight 診斷的呈現規則。

### 20.【Medium】`scaffold` 在使用者限制寫入路徑時無定義

- **出處**：`SKILL.md:42-43` `scaffold` 寫產品路徑、需先確認；`SKILL.md:287-291` entry point 必須在 `tools/`。
- **問題**：使用者只授權部分路徑時（本輪即是），skill 沒有說 persistent entry point 該怎麼建、建在哪、算不算合規。
- **本輪證據**：執行者自行選擇 `tools/verification-gate/` 子目錄並記錄依據。
- **建議**：明訂 entry point 的最小可接受落點與受限授權下的降級規則。

### 21.【Medium】`must_not_match` 參考實作在檔案清單為空時 fail open — 且盲點會被完整複製

- **出處**：`references/entry-point.md:110-125` 的 must-find-nothing grep 參考實作；`references/entry-point.md:137-139` 的 checker self-test 清單（三條）。
- **問題**：`must_not_match "$pattern"` 在 shift 之後若沒有路徑參數，`grep -rniE` 會退回讀 **stdin**。三種情境全部回 rc 1 → 函式回 0 → **pass**，包含 stdin 裡確實含違規內容的那次。呼叫端若以動態計算的檔案清單傳入（例如 `$(git diff --name-only …)`），清單為空時這個「必須找不到東西」的檢查會靜默通過。
- **機械驗證**（逐字抄用參考實作）：

  ```text
  rc=1 | forbidden pattern present   -> 期望 nonzero  ✔
  rc=0 | clean tree                  -> 期望 0        ✔
  rc=2 | nonexistent path            -> 期望 2        ✔
  rc=1 | 空檔案清單（stdin 為 tty/關閉）              -> 函式 return 0 = pass
  rc=1 | 空檔案清單 + stdin 為空管線                  -> 函式 return 0 = pass
  rc=1 | 空檔案清單 + stdin 含 AWS_SECRET_ACCESS_KEY  -> 函式 return 0 = pass
  ```

- **本輪證據（盲點確實會傳染）**：執行者把 `must_not_match` **逐字**複製進 `tools/verification-gate/self_test.sh:48-52`，並且斷言的控制組正好是參考文件列出的那三條（`self_test.sh:70-72`），一條不多。一個 xhigh 推理的全新 context 執行者把 reference 的 self-test 清單當成窮盡清單處理。
- **附帶觀察**：`must_not_match` 只出現在 `self_test.sh`，`gate.sh` 從未實際使用它 — `entry-point.md:48` 的範例 manifest 含 `must-not-scans` 層，但文件從未定義 must-not scan 要掃什麼、何時適用，於是被自我測試、卻沒有被使用。
- **建議**：（a）參考實作加入 `[ "$#" -eq 0 ] && { echo "FAIL: no paths given"; return 2; }`；（b）self-test 清單補上「空參數清單必須 rc 2」；（c）明寫該清單是**下限而非窮盡**；（d）定義 `must-not-scans` 層的用途，或從範例 manifest 移除。

### 22.【Medium】changed-line coverage 的強制失敗要求，8 張生態系表中只有 1 張給得出

- **出處**：`SKILL.md:183` 絕對要求「**This layer must exit nonzero when its threshold is missed**… a layer that prints a percentage and exits 0 is a report, not a gate layer」。
- **問題**：`references/layers.md` 的 8 個生態系裡 —
  - **Python**（line 13）是唯一給了會失敗的命令的；但主推的 `--cov-fail-under` 閘的是**全域**覆蓋率，正是 SKILL.md 自己稱為 vanity 的指標；真正閘 changed lines 的 `diff-cover --fail-under=100` 只是附帶提及。
  - **JS/TS**（line 24）`npx vitest run --coverage` + 「check touched files」— exit 0。
  - **Go**（line 35）`go tool cover -func=c.out` — exit 0。
  - **Rust**（line 46）`cargo llvm-cov --branch` — exit 0（未提 `--fail-under-lines`）。
  - **Java / Scala**（line 57 / 68）「inspect the XML/HTML report」— 人工，無 exit code。
  - **SQL / Emacs Lisp**（line 83 / 94）「map… / verify…」— 人工。
- **本輪證據**：執行者必須從零寫 `changed_lines.mjs` 才能得到一個會 exit 1 的 changed-line 層 — 而那正是本輪唯一擋下 gate 的層。若它照 `layers.md` 的 Rust/JS 列直接做，這個 gate 會全綠通過。
- **建議**：每張表的 coverage 列都必須給出「會 exit nonzero 且針對 changed lines」的形式，給不出的生態系明寫「無現成命令，必須自建 checker，並套用 checker note 的 negative control 規則」。

### 23.【Low】`references/layers.md` 自述的 always-on / 延伸層分界，被它自己的列違反

- **出處**：`references/layers.md:100-101`「Always-on layers live in SKILL.md's table; these are picked per task by the Tier 3 failure model」。
- **問題**：`Suite health` 同時出現在 SKILL.md 的 always-on 表（line 189）與延伸清單（line 109）；SKILL.md 的 `Supply chain & secrets`（line 188）在延伸清單被拆成 Dependency audit / License check / Secret scan / Capability diff 四列。讀者無法判定這些層到底是 always-on 還是 Tier 3 才選。
- **相關**：Calibration 也不自洽 — Tier 1 只跑「full suite + lint」（10 個 always-on 層中的 2 個），與「Run every applicable layer… never skip a layer silently」衝突；Tier 3 又重新列出 property-based 與 mutation，而兩者本已是 always-on。
- **建議**：把 always-on 集合定義成單一權威清單，Tier 只調整**深度**不調整**集合**；或明訂 Tier 1/2 的 always-on 子集並讓 Completion Criteria 引用該子集。

### 24.【Low】手寫 mutant 的等價控制組與 SKILL.md 的等價 mutant 規則互相牴觸

- **出處**：`references/mutation.md:54-60` 要求「a fixed control pair — one mutant that must be killed and one **deliberately equivalent** mutant that must survive」；`SKILL.md:232-233`「Hand-written mutants (the manual procedure) get no such excuse: you chose them, so choose real bugs」。
- **問題**：一邊強制要求刻意寫一個等價的手寫 mutant，一邊說手寫 mutant 不得以等價為由開脫。兩處都在講手寫 mutant，讀者需要自行推斷「控制組不是計分 mutant」— 文件沒說。
- **建議**：在 `mutation.md` 明寫控制對不計入 killed/total，且不受 SKILL.md 等價規則約束。

### 25.【Low】manual mutation 步驟 3 與反作弊規則 2 未協調

- **出處**：`references/mutation.md:37-39`「A surviving mutant means a missing or vacuous assertion — add the test that kills it, then continue」；`SKILL.md:377-379` 規則 2「Never edit a test and the implementation in the same step to reach green」。
- **問題**：mutant 仍套用在實作上時去補測試，就是在被改過的實作上定義正確性 — 正是規則 2 要防的情形。步驟 3 沒有要求先還原。
- **建議**：步驟 3 改為「先還原 mutant → 補測試 → 對原始碼確認綠 → 重新套用該 mutant 確認被殺」。

## 已排除：不是缺陷

以下三項曾被誤報為卡死點，重讀原文後確認 SKILL 已有定義，**不要再提**：

- **changed-line coverage 未達標 × 反作弊規則 6**：規則 6 已定義行為 —「Failing gate blocks done… report the failure verbatim as the outcome」。本輪實跑證實：gate 在此停住、報告如實標為 BLOCKED、執行者未弱化任何東西。不是死結。
- **RED 重建的粒度**：SKILL 已寫明 case by case，不是未定義。（但見缺陷 9 — 未定義的是「全部退化為 collection error 時 RED 是否還算證據」。）
- **flaky test**：SKILL 已定義後果 —「quietly invalidates the report」。

## 待補

- `plugins/code-review/skills/verification-gate/` 缺 `evals/evals.json`，與同 plugin 內的 `code-review` 不對等。

## 修補優先序建議

依「不修就會產生看起來合規的假證據」排序：

1. **缺陷 5**（fail-first vs 每層須有狀態）— 任何失敗的 gate 都無法合規完工。
2. **缺陷 6**（gate 自身弄髒 source state）— 首次執行必然觸發。
3. **缺陷 22 + 4**（changed-line coverage 在多數生態系不會失敗、跨語言邊界漏測）— 直接產生假綠。
4. **缺陷 7**（changed line 的分母未定義）— 頭號數字無定義。
5. **缺陷 9**（大型重寫的 RED 結構上無法產生證據）。
6. **缺陷 1**（`changed_unit_command` 可被合規地降級）。
7. 其餘依嚴重度。

## 修正紀錄 — A+B（2026-08-25）

已修 10 項，只動 skill 的 4 個檔，未碰任何專案程式碼。**尚未重跑驗證**。

| # | 修正 | 落點 |
|---|---|---|
| 5 | 新增第四狀態 `NOT REACHED`；明訂 blocked gate 是「完成且失敗」而非未完成報告；禁止為多跑幾層而重排 entry point；裁決失敗後另跑的層數字只能進 Honest notes、不得進 Gate 表或升級 `NOT REACHED` | `SKILL.md`（Layers not run / Completion Criteria）、`assets/templates/evidence.md` |
| 6 | source-state 明訂以「固定列舉的 verifier 路徑白名單」解決，禁止放寬成忽略 untracked、禁止延伸到產品路徑；白名單須在 EVIDENCE 逐字揭露；工具輸出須導向 `artifact_root`；source state 改為 run 前後各驗一次；self-test 補正向控制（只有白名單髒污時必須仍能出狀態） | `SKILL.md`（Entry Point）、`references/entry-point.md`（新增「The verifier's own footprint」）、template 新增 `source_state_exclusions` |
| 12 | capability diff 改為機械化定義（只讀宣告面：import/require、依賴 manifest、build script、CI 權限、平台能力宣告），明列為 Scope Boundary 的具名例外，並禁止讀函式內容判斷用法；動態取得的能力歸 structural blind spot | `SKILL.md`（Scope Boundary）、`references/layers.md`（Capability diff 列） |
| 19 | 「單一 final fresh run」作用域限縮到 Gate 表；baseline/RED 明訂為 base ref 的前置執行、本質不適用；preflight 診斷只能進 Honest notes 並標明非 final run | `SKILL.md`、template |
| 22 | 表格前新增規範段：所有生態系表給的是 **producer**，gate 需要 producer + gate step；原生 threshold 閘的是全域覆蓋率（SKILL 自稱 vanity）不算此層；8 個生態系的 coverage 列全部改寫，逐一標明「producer only」與該補的 gate step；無現成檢查者時須自建並套用 checker note（含 zero-hit 負向控制） | `references/layers.md` |
| 4 | 新增「Projects that span several ecosystems」：每生態系各自成層並加後綴、任一失敗即該層失敗、禁止跨生態系合併分數（mutation 分數量綱不同）、各自在自己的 manifest 釘版本。新增「Cross-language boundaries (FFI/N-API/JNI/cgo/WASM)」：呼叫方與被呼叫方的 instrument 互相看不到對方，producer 必須在同一次 profiling session 內同時 instrument 被呼叫方並跑呼叫方測試再合併，做不到即 `SUBSTITUTED`；附一條 sanity check | `references/layers.md` |
| 7 | changed line 明訂為三個集合：可執行且已 instrument（分母）／不可執行／**可執行但無 coverage mapping**；第三類必須單獨列出、禁止併入第二類；三個數字都要報，第三類非零即封頂該層可宣稱的範圍 | `SKILL.md`（新增 Changed-line accounting）、layers.md 規範段、template coverage 列 |
| 9 | 新增 RED 失效條款：當新測試全部因 base 缺少該 platform 而在 collection 失敗時，整節記為 `NOT EVIDENCE (base lacks the platform under test)` 並註明比例；替代方案為對 **HEAD** 逐測試投一次性 throwaway mutant 證明斷言能力，且必須標明那是較弱的宣稱 | `SKILL.md`（Reconstructing RED）、template |
| 1 | template 新增 `changed_unit_granularity`（symbol / path / module）；SKILL 明訂路徑級在無符號抽取器時可接受、但不標示則否，因為兩者在 header 上看起來一樣；粗粒度時 Table 1 須說明留下什麼未對應 | `SKILL.md`（Table 1）、template |
| 21 | `must_not_match` 補空參數守衛（rc 2）並附說明；抽出通則「任何吃工作清單的檢查者都可能被餵空清單，『什麼都沒檢查』不得與『什麼都沒找到』共用結束碼」；self-test 清單明寫是**下限非窮盡**並新增一條控制；補述 `must-not-scans` 不是必備層、留著就要給真的 pattern 與路徑 | `references/entry-point.md` |

**機械驗證**：修正後的 `must_not_match` 直接從文件中抽出執行 — 違規存在 rc 1、乾淨 rc 0、路徑不存在 rc 2、空清單 rc 2、空清單且 stdin 含違規 rc 2。原三條控制行為不變，fail-open 路徑消失。

**未修（C+D）**：2、3、18（狀態詞彙）、8、10、11、13、14、15、16、17、20、23、24、25。這些不會產生假綠，留待下一輪或寫成 known limit。

## 下一輪：回歸驗證（尚未執行）

前置條件：實作端處理完 429 行未覆蓋（已於本日移交 gslm-orchestrator → gslm-implementor）。

做法：同一目標、同一組條件、**全新 context 執行者**，一次重跑。同時買到兩樣東西 —

1. 第一次有機會通過 coverage，實際跑到目前完全未測量的 7 層（mutation、property、complexity、supply-chain/secrets、real execution、suite health、adversarial）。
2. A+B 的回歸檢查：看那 10 項是否不再需要執行者自行發明規則。判準是新一輪的 gaps 清單中，這 10 項各自不再出現。

## Round 2 — A+B 回歸驗證（2026-08-25，未完成）

### 條件

- **淨室**：round-1 的 `tools/verification-gate/` 與 `.gate/`（含 `VERIFICATION-GATE-GAPS.md`）整批移出倉庫至 `/home/madao/projects/gslm-gate-round1/`，執行者無從發現既有 entry point，必須從新版 skill 文本重建
- **執行者**：全新 codex session `01a0391a`，YOLO，gpt-5.6-terra xhigh
- **提示詞**：round-1 原文，只改 HEAD → `4b2730d`（實作端補完 coverage 後的 commit，19 檔 +1169/-13，經獨立驗證為純測試碼）
- **未告知**：這是第二輪、skill 被修改過、任何缺陷

### 兩個中斷

1. **gate 本身停在第 3 層**：`source-state-pre` FAIL — `untracked non-verifier path: .agents/skills/verification-gate/NOTICE.md`
2. **執行者撞到 codex 週額度上限**：停在準備裝 Stryker 跑 JS mutation 診斷時，evidence 尚在補寫

**但這輪的 gaps 清單仍有效**：它在最終 entry-point run 之前已把幾乎每一層當診斷跑過（`diagnostics/` 下有 coverage-ffi、mutation、real-execution、node-matrix、property-based、adversarial、audit、licenses、gitleaks），所以缺口是真的撞出來的，不是沒跑到。

### 主要結果：gaps 21 → 7

這是單一配對比較，不是 n>1 的受控實驗；但對照條件（同目標、同提示詞、同模型、全新 context、淨室）夠緊。

**修正確實生效的 8 項**：

| # | 證據 |
|---|---|
| 5 | Gate 表 16 列標 `NOT REACHED` 並具名停在哪一層。round-1 得自創 `NOT EXECUTED` |
| 1 | header 出現 `changed_unit_granularity: module`，並註明「individual functions and branches inside a module are not individually mapped」。round-1 靜默填了路徑級命令、無任何揭露 |
| 19 | 明寫「only the first three rows are measurements from this final run」，診斷一律標 `Diagnostics, not final-entrypoint results` |
| 4（分層） | gate 被拆成 `run-rust-tests` / `run-node-tests`、`run-rust-types` / `run-node-types`、`run-rust-lint` / `run-node-lint`、`run-rust-coverage` / `run-node-coverage` — 正是新增的每生態系加後綴規則。並依跨生態系規則主動去找 JS 的 mutation 工具 |
| 4（跨語言） | **這次成功了**：`cargo llvm-cov show-env --sh --target x86_64-unknown-linux-gnu --coverage-target-only` → 重建 NAPI callee → 在該環境下跑完 41 個 Node caller 測試 → 併成單一 Rust LCOV。round-1 的第一版 collector 完全沒觀測到 NAPI 執行路徑。**這是最強的單項訊號** |
| 7 | 實作了行分類檢查器，`executable_without_coverage_mapping` 是會失敗的獨立桶，並附我規定的合成 zero-hit 負向控制 |
| 9 | RED 標 `NOT EVIDENCE`，9/9 新增 Node 測試檔在 base 因缺 package/binding 失敗 |
| 21 | 負向控制超出參考文件原本那三條：新增 `coverage-zero-hit rc 1`、`source-untracked-product rc 1`、`source-shallow-history rc 1`、`orchestration-status rc 7` |

**尚未修的 C 類如預期繼續發生**：缺陷 2（reproducibility 無降級狀態）→ 執行者又自創了一個 `NOT CERTIFIED`。這反而是個乾淨的對照：自創行為跟著「未修的缺陷」跑。

### 我的修正引入的兩個新缺陷

#### 26.【High】source-state 白名單過窄，擋掉 skill 自己的安裝目錄

- **成因**：缺陷 6 的修正把白名單定義成「entry-point 目錄與 `artifact_root`，其餘皆非」。但 skill 自身安裝在 `.agents/skills/verification-gate/`，既非 entry point 亦非 artifact root，於是成為 untracked non-verifier path。
- **後果**：最終 gate 在第 3 層 `source-state-pre` 就停，後面 16 層全部 `NOT REACHED`。round-1 的執行者自創白名單含 `.agents/*`，反而過得去。
- **範圍不只本專案**：任何倉庫裡未追蹤的 agent 工具目錄（`.agents/`、`.claude/`、`.codex/`）都會觸發。
- **建議**：白名單改為三類 —（a）entry-point 目錄（b）`artifact_root`（c）**不屬於變更集的 agent/工具設定目錄**，第三類須在 EVIDENCE 逐字列出並說明它不影響被驗證的原始碼。

#### 27.【Medium】RED 的替代方案在「不得修改產品碼」下不可用

- **成因**：缺陷 9 的修正規定，RED 不可得時改用「對 HEAD 逐測試投一次性 throwaway mutant」證明斷言能力。但那需要改產品碼，而「不得修改產品程式碼」是驗證委託的標準限制。
- **證據**：執行者原文 —「skill 建議 per-test throwaway HEAD mutations，而使用者明確禁止修改產品碼；skill 沒說隔離的 mutation 工具算不算適當替代」。它拒絕執行該替代方案。
- **建議**：明訂在隔離副本（worktree／`cargo-mutants` 那類工具自建的臨時樹）中執行的 mutant 不算修改產品碼，並說明該替代方案在此形式下的宣稱強度。

### Round 2 新發現的缺陷（不在 round-1 的 21 項內）

#### 28.【Medium】spec 之間相互矛盾時無優先序規則

- 執行者撞到：spec 0001 說保留既有 TypeScript 實作，spec 0005 明確要求刪除 `src/` 與舊 CLI，兩份都 `status: done`。skill 只說「取得 intent」，沒有多份 spec 衝突時的裁決規則。
- 處理：自行採用「較晚且明確的 0005 為 0001 的細化」，並記為詮釋而非規則。

#### 29.【Medium】API 相容性層沒有 baseline／快照定義

- Tier 3 要求 API compatibility 檢查，但 skill 與專案都沒有定義公開 API 的基準快照或破壞性變更政策；base commit 根本沒有 `packages/gslm` 的型別面可比。
- 附帶產出一個真實失敗：以 TypeScript consumer fixture 檢查現行 `index.d.ts`，在 `index.d.ts:182` 失敗（`SheetsClientOptions` 不存在）。

#### 30.【Medium】授權（license）檢查沒有政策來源

- `references/layers.md` 要求 license check，但沒說政策從哪來。`cargo-deny` 預設政策拒絕所有授權**含 MIT**，結果 227 個依賴全被拒。
- 執行者拒絕自行發明政策，記為診斷失敗與政策缺口，不當成漏洞也不當成通過。
- 建議：明訂沒有 repo 授權政策時該層記為 `UNAVAILABLE`，並禁止把工具預設政策當成專案政策。

#### 31.【Low】Rust 測試順序隨機化的替代方案無演算法與宣稱邊界

- reference 允許 nightly 不可得時替代，但沒規定替代怎麼做、能宣稱到哪。
- 處理：Rust suite 跑兩次、Node 測試檔以兩個確定性偽亂序（seed 480272 / 480273）跑，標 `SUBSTITUTED` 並註明無法證明 binary 內任意測試順序獨立性。

### 附帶產出的真實情報（全部是診斷，未進 Gate 表）

這些是這個變更集第一次被這些層測量。**不是 gate 結果，不可當結論**：

- **mutation（Rust，限變更 diff）**：413 個 mutants — 296 caught、**69 missed**、48 unviable、0 timeout。存活 69 個。
- **gitleaks**：1 筆 — `private-key`，位於 `crates/gslm-sheets/tests/fixtures/service-account.json:5`。看起來是測試 fixture，但需要人確認那是拋棄式金鑰而非真憑證。
- **cargo audit**：掃了 275 個 crate。
- **cargo deny licenses**：227 個依賴被預設政策拒絕（見缺陷 30，是政策缺口不是實質問題）。
- **公開 API**：`index.d.ts:182` — `SheetsClientOptions` 不存在，TypeScript consumer fixture 失敗。

### 下一步

1. 修缺陷 26（白名單過窄）與 27（RED 替代方案不可用）— 這兩項是我改出來的，且 26 讓 gate 在第 3 層就死。
2. codex 週額度要到 8/31 才恢復；round 3 得等，或換執行者（會改變對照條件，須註明）。
3. round 3 才有機會第一次讓完整 19 層走完 entry point。
