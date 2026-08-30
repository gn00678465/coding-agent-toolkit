# 研究筆記：AGENTS.md 的 Progressive Disclosure 重構

- **來源文章**：Matt Pocock (AI Hero), [A Complete Guide to AGENTS.md](https://www.aihero.dev/a-complete-guide-to-agents-md)
- **主要規範來源**：[agents.md](https://agents.md/)（AGENTS.md 官方 spec / convention 網站）
- **延伸引用**：Kyle (HumanLayer), [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)（文章內唯一引用的外部連結）
- **檢索備註**：以 WebSearch 確認 aihero.dev 上並無獨立的「progressive disclosure」或「contradictions」子頁面；該篇文章本身即涵蓋完整論述，未拆分成多篇。
- **檔案位置說明**：本 repo 的 `docs/` 目前是扁平結構（僅有 `docs/advisor-orchestration-issues.md`），沒有既有的 `docs/research/` 慣例。依任務指示仍建立 `docs/research/` 子目錄並存放本檔案；若之後要統一慣例，可考慮把既有的 `advisor-orchestration-issues.md` 一併移入。

---

## 1. 文章核心論點：AGENTS.md 為什麼會肥大、肥大的代價

### 1.1 AGENTS.md 是什麼

文章開頭定義：AGENTS.md 是「a markdown file you check into Git that customizes how AI coding agents behave in your repository」（一個你 check into Git、用來客製化 AI coding agent 在你 repo 中行為的 markdown 檔案）。它座落在對話歷史的最上方，緊接在 system prompt 之下，作為 agent 基礎指令與你實際程式碼庫之間的一層設定（來源：aihero.dev 正文）。

其內容通常混雜兩種範疇：
- **個人範疇**（personal scope）：commit style、個人偏好的 coding pattern
- **專案範疇**（project scope）：專案目的、package manager、架構決策

（來源：aihero.dev 正文）

### 1.2 肥大成因：「自然的回饋迴圈」

文章指出一個造成檔案不斷膨脹的「natural feedback loop」（自然回饋迴圈）：

1. Agent 的行為讓你失望
2. 你新增一條規則試圖防止再次發生
3. 這個過程持續數個月
4. 結果：「an unmaintainable mess that actually hurts agent performance」（一個無法維護、實際上反而傷害 agent 表現的爛攤子）

除此之外，另一個肥大來源是**自動產生的內容**——這些內容會把「useful for most scenarios」（對大部分情境有用）但其實更適合以 progressive disclosure 方式延遲揭露的東西，全部塞進同一個檔案裡（來源：aihero.dev 正文）。

（對照 agents.md 官方定義：AGENTS.md 的初衷是把「README 給人看」與「agent 需要的額外、有時很細節的 context」分開，讓兩者各自保持精簡與聚焦——這也反向解釋了：一旦把太多「有時用得到」的細節塞進 AGENTS.md，就違背了它原本要與 README 分工、保持聚焦的設計初衷。）

### 1.3 肥大的代價

**(a) Instruction budget（指令預算）問題——這是核心的成本論證**

文章引用 Kyle（HumanLayer）的說法作為量化依據：

> "Frontier thinking LLMs can follow ~150-200 instructions with reasonable consistency. Smaller models can attend to fewer instructions than larger models, and non-thinking models can attend to fewer instructions than thinking models."

（前沿的 thinking 模型大約能以合理的一致性遵循 150–200 條指令；較小的模型能關注的指令數比大模型少，非 thinking 模型能關注的指令數也比 thinking 模型少。）

由此延伸出的具體影響：
- 「Every token in your AGENTS.md file gets loaded on **every single request**, regardless of whether it's relevant」——AGENTS.md 裡的每個 token，不論是否與當前任務相關，都會在**每一次請求**中被載入（context window 污染的直接來源）
- 檔案小 → 「More tokens available for task-specific instructions」（更多 token 空間留給該次任務真正需要的指令）
- 檔案大 → 「Fewer tokens for the actual work; agent gets confused」（能用在實際工作上的 token 變少，agent 容易混亂）→ 這正對應題目要求提到的「agent 遵循度下降」

**(b) 過時文件「毒化」context**

文章警告：「stale information actively *poisons* the context」（過時的資訊會主動「毒化」context），並舉例：如果 AGENTS.md 寫著「authentication logic lives in `src/auth/handlers.ts`」，但該檔案已被搬移或重新命名，agent 會「confidently look in the wrong place」（自信滿滿地找錯地方）。這說明肥大檔案不只是「佔用量」的問題，內容過時本身就是主動誤導。

**(c) 指令衝突（矛盾）**

雖然文章未用長篇幅單獨論證「衝突」的代價，但它把「Find contradictions」列為重構的**第一步**，隱含的邏輯是：長期靠「回饋迴圈」一條條加規則、缺乏整體審視，必然會累積出彼此矛盾的指令（例如某處說「用 `npm run test`」、另一處說「用 `vitest run`」），而矛盾指令會讓 agent 無所適從，比單純「內容太多」更嚴重地拖垮遵循度。

---

## 2. Progressive Disclosure 原則：定義與運作方式

**定義**（來源：aihero.dev 正文）：Progressive disclosure 意指「give the agent only what it needs right now, and point it to other resources when needed」——只給 agent 當下需要的東西，需要時再指向其他資源。

WebSearch 找到的補充措辭（explainx.ai 對該文章的轉述）也一致：「The ideal AGENTS.md is small, focused, and points elsewhere... with everything else living in progressive disclosure: separate files, nested AGENTS.md files, or skills.」

**運作機制**：

1. **Root AGENTS.md 保持極簡**：只放對「每一個任務」都相關的內容。
2. **用 Markdown 連結指向分類文件**：例如把 TypeScript 慣例從 root 移出，root 只留一行「For TypeScript conventions, see docs/TYPESCRIPT.md」。
3. **Agent 按需讀取**：好處是——
   - 「TypeScript rules only load when the agent writes TypeScript」（只有在寫 TypeScript 時才載入 TS 規則）
   - 「Other tasks (CSS debugging, dependency management) don't waste tokens」（其他任務不會浪費 token 去讀不相關的規則）
   - 「File stays focused and portable across model changes」（檔案保持聚焦，且在換模型時仍可攜）
4. **可以形成巢狀階層（nested hierarchies）**，例如：
   ```
   docs/
   ├── TYPESCRIPT.md（內部再連結到 TESTING.md）
   ├── TESTING.md（內部再連結到特定的 test runner 說明）
   └── BUILD.md（內部再連結到 esbuild 設定）
   ```
5. **Monorepo 情境**：多個 AGENTS.md 可以在不同層級並存、合併：

   | 層級 | 內容 |
   |------|------|
   | Root | monorepo 目的、如何在各 package 間導覽、共用工具 |
   | Package | 該 package 的目的、技術棧、該 package 專屬慣例 |

   Root 範例：「This is a monorepo containing web services and CLI tools.」
   Package 範例：「This package is a Node.js GraphQL API using Prisma.」

（對照 agents.md 官方站的說法：對於 monorepo，官方建議可用「nested AGENTS.md files for subprojects」，且 agent 會「automatically read the nearest file in the directory tree」——也就是自動讀取目錄樹中「最近」的那個 AGENTS.md。這是 progressive disclosure 在 monorepo 場景下的具體落地機制，兩篇來源在此互相印證。）

---

## 3. 什麼屬於 Root AGENTS.md、什麼該抽出去、什麼該刪除

### 3.1 Root AGENTS.md 的「絕對最小值」（來源：aihero.dev 正文）

- **One-sentence project description**（一句話專案描述）——文章指出這其實是扮演 role-based prompt 的角色。範例：「This is a React component library for accessible data visualization.」
- **Package manager**（若不是 npm 才需要標明）
- **非標準的 build/typecheck commands**（只有「非標準」時才需要寫，標準做法不必贅述）
- 文章原話：「That's honestly it. Everything else should go elsewhere.」（老實說就這樣，其他一切都該放到別處去。）

判斷標準（decision framework，來源：aihero.dev 正文，整理為表格）：

| 位置 | 適用時機 |
|------|----------|
| Root AGENTS.md | 與 repo 中**每一個**任務都相關 |
| 獨立檔案 | 只與**單一領域**相關（TypeScript、testing 等） |
| 巢狀文件 | 可依階層組織、逐層深入 |

換句話說，判斷一條指令該不該留在 root 的核心測試是：**「這件事是否跟每一次任務都相關？」** 若答案是否，它就該被抽出去，變成一個由 root 連結出去的獨立檔案。

### 3.2 該分組抽出的內容

文章給的例子包括 TypeScript conventions、testing patterns 等，本質上任何「只在特定任務類型出現時才需要」的規則都屬於此類（API 設計規範、Git workflow 規則、特定框架慣例等），依主題各自成一個 markdown 檔案，並由 root 用連結指向它們。

### 3.3 該刪除的內容（判斷標準）

文章對應到重構 prompt 的第 5 步，列出三種該刪除的類型：
- **Redundant（多餘）**：agent 本來就已經知道的事（例如常識性的語言慣例）
- **Too vague to be actionable（太模糊、無法據以行動）**：無法轉化成具體行為的指令
- **Overly obvious（過度顯而易見）**：例如「write clean code」這種空話

這三個判準的共通邏輯是：**如果一條指令不會改變 agent 的具體行為，它就是純粹的 token 成本，沒有對應的效益**，因此應該刪除而非「找個地方放」。

---

## 4. 對重構提示詞的逐步第一性原理分析

以下逐步分析題目給出的五步驟 prompt，說明每一步在解決什麼問題、為什麼順序如此安排，以及哪些步驟需要人類介入決策。

### Step 1 — Find contradictions（找出矛盾）

- **解決的問題**：對應第 1.3(c) 節分析的「指令衝突」代價。矛盾指令是所有問題中最危險的一種——內容過多只是「稀釋」agent 的注意力，但矛盾指令會讓 agent 無論選哪一個都可能「違反」另一條規則，直接損害正確性與可預測性。
- **為什麼放在第一步**：這是唯一一個**無法由 agent 單方面自動解決**的問題——衝突意味著存在兩個互斥的人類意圖，agent 沒有立場替使用者決定「保留哪一個」。若不先處理，後續的分類、抽取步驟可能會把兩條互相矛盾的規則「乾淨地」分別歸檔到不同檔案裡，反而讓衝突更隱蔽、更難被日後的人類發現（因為它們不再相鄰、不再顯眼）。所以必須在檔案結構被打散之前，趁矛盾雙方還「並列可見」時解決。
- **需要人類決策**：**是**。Prompt 明確要求「For each contradiction, ask me which version I want to keep」——這是全流程中唯一強制要求暫停、詢問使用者的步驟，因為「該遵循哪個規則」是屬於專案所有者的價值判斷，不是 agent 能夠代為決定的技術問題。

### Step 2 — Identify the essentials（識別本質）

- **解決的問題**：對應第 3.1 節的「絕對最小值」判準。這一步的目的是先確立「什麼東西無論如何都必須留在 root」，也就是先劃出 progressive disclosure 架構中「永遠會被載入」的那一小塊核心。
- **為什麼是第二步（在分組之前）**：必須先決定「什麼不需要被分組」，才能讓第 3 步的分組工作範圍是「扣除本質之後剩下的東西」，避免本質內容被誤歸進某個主題分類檔案（例如「package manager」不該被歸進 BUILD.md，而該留在 root，因為它跟每個任務都有關）。這一步其實就是在套用第 3.1 節那個「是否與每個任務相關」的測試，對每一條殘存指令（已排除衝突的）做一次分類。
- **需要人類決策**：不一定需要主動詢問，但因為判準本身帶有主觀性（例如「這條規則真的跟每個任務都相關嗎？」），agent 產出的分類結果理應讓使用者過目確認，只是 prompt 本身沒有像 Step 1 那樣強制要求逐條詢問。

### Step 3 — Group the rest（分組其餘內容）

- **解決的問題**：對應第 2 節 progressive disclosure 的核心機制——把「不屬於 root」的內容組織成可被「按需讀取」的單元。若不分組，抽出的內容就會是一堆零散指令，無法讓 agent 依任務類型精準地只載入相關部分。
- **為什麼在本質識別之後**：分組的輸入必須是「已排除 root 內容」的殘餘指令集合，否則會把本該留在 root 的東西也一併分類掉。同時，這一步也隱含建立了語意分類（TypeScript conventions、testing patterns、API design、Git workflow 等），這是後續建立檔案結構（Step 4）的前置作業——你必須先知道「有哪些類別」，才能決定「要建立哪些檔案」。
- **需要人類決策**：分類方式本質上是設計決策（例如「testing」要不要跟「TypeScript」合併），但 prompt 沒有要求逐一詢問，屬於 agent 可以先提案、使用者事後審閱調整的部分。

### Step 4 — Create the file structure（建立檔案結構）

- **解決的問題**：這一步是把前三步的分析結果**具體落地**成第 2 節描述的實際檔案結構——精簡的 root AGENTS.md + markdown 連結 + 各分類檔案 + docs/ 資料夾建議。對應 agents.md 官方站對 monorepo 的「nested AGENTS.md / 就近讀取」機制，以及 aihero.dev 文章給的巢狀範例（TYPESCRIPT.md → TESTING.md → BUILD.md）。
- **為什麼在分組之後**：唯有先完成矛盾排除、本質萃取、主題分組這三項「分析」工作，才有足夠資訊產出結構化「輸出」；若提前輸出檔案結構，等於是在資訊不完整（可能還有矛盾、還沒篩出本質）的情況下做架構決策，日後極可能要推翻重做。
- **需要人類決策**：檔案結構、命名慣例（例如要不要用 docs/ 而非其他資料夾）通常由使用者的專案慣例決定，agent 產出的是「建議」（suggested docs/ folder structure），隱含使用者仍可調整。

### Step 5 — Flag for deletion（標記待刪除）

- **解決的問題**：對應第 3.3 節的三個刪除判準（多餘、模糊、顯而易見）。這一步是最後的「減法」把關，確保重構後的檔案不只是把肥大內容「搬家」，而是真正降低了整體 instruction budget 的消耗。
- **為什麼放在最後**：必須先看過完整的分類與結構（Step 3、4）之後，才容易判斷「這條規則放進某個分類檔案裡後，是否仍然有存在意義」——很多冗餘或模糊的指令，只有在跟同類規則放在一起比較時才會顯得多餘或空洞。如果在一開始（例如跟 Step 1 合併）就做刪除判斷，缺乏分類後的上下文對照，容易誤刪或漏刪。另外，這一步本質上是「錦上添花」的最佳化，不影響結構是否正確，所以邏輯上放在架構已經確定之後執行最合理。
- **需要人類決策**：是「標記」（flag）而非直接刪除，用詞上刻意保守——意味著 agent 只提出建議清單，最終刪除與否仍由使用者確認，避免 agent 誤刪有價值但陳述方式不夠具體的規則。

### 整體順序的第一性原理總結

五步驟可以歸納成一個「先處理不確定性、再做結構決策、最後做效益最佳化」的順序：

1. **消除衝突**（人類決策，解決「規則互斥」的正確性風險）
2. **劃定不可分割的核心**（建立 progressive disclosure 架構的「always-loaded」基準線）
3. **對其餘內容做語意分群**（準備好可被按需載入的邏輯單元）
4. **把分析結果具體化為檔案系統結構**（真正實現「root 精簡 + 連結」的 progressive disclosure）
5. **做最後的減法把關**（確保搬遷後的內容仍然值得佔用 token 預算）

這個順序本質上遵守一個原則：**先解決「錯誤」（矛盾），再解決「結構」（分類與落地），最後解決「效率」（刪減冗餘）**——因為矛盾若不先解決會污染後續所有分類與結構決策；結構若不先確定，刪減判斷會缺乏上下文；而效率最佳化本來就該是流程的最後一道把關。

---

## 5. AGENTS.md 與 CLAUDE.md 的關係

- CLAUDE.md 是 **Claude Code 對 AGENTS.md 這個開放格式的工具專屬等價實作**。agents.md 官方站點列出多個工具（Aider、Gemini CLI、VS Code、Cursor、GitHub Copilot 等）如何識別/讀取 AGENTS.md，其設計目的正是要建立一個「工具中立」（tool-agnostic）的共通慣例，避免每個 agent 工具都要求維護一份專屬的設定檔。
- 本次任務所在的 repo（coding-agent-toolkit）使用者的全域設定中，`CLAUDE.md` 扮演的正是 AGENTS.md 所描述的角色：包含 skill 清單、行為規範等「agent 需要、但一般 README 不會寫」的內容——這與 agents.md 官方定義的「README 給人看、AGENTS.md（或其等價物）給 agent 看」完全對應。
- 因此，本文分析的所有 progressive disclosure 原則、肥大代價、重構方法論，**同樣適用於 CLAUDE.md**：CLAUDE.md 也會被每次請求載入、也會累積「回饋迴圈式」的規則、也一樣需要把非核心內容抽到獨立文件並用連結指向。實務上許多團隊會讓 `CLAUDE.md` 直接成為 `AGENTS.md` 的 symlink 或幾乎等價的內容，以便同時支援 Claude Code 與其他遵循 AGENTS.md 慣例的工具。

---

## 6. 引用來源總表

| Claim | 來源 |
|-------|------|
| AGENTS.md 定義、個人/專案範疇混雜 | aihero.dev 正文 |
| 「自然回饋迴圈」導致肥大 | aihero.dev 正文 |
| 自動產生內容導致肥大 | aihero.dev 正文 |
| 150–200 instructions 的 instruction budget 引用 | Kyle, HumanLayer — [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)（經 aihero.dev 引用） |
| 「每個 token 在每次請求都會被載入」 | aihero.dev 正文 |
| Stale 資訊「毒化」context 的範例 | aihero.dev 正文 |
| Root AGENTS.md 最小值（一句話描述、package manager、非標準指令） | aihero.dev 正文 |
| Progressive disclosure 定義與 TypeScript 範例 | aihero.dev 正文 |
| 巢狀階層範例（TYPESCRIPT.md/TESTING.md/BUILD.md） | aihero.dev 正文 |
| Monorepo 多層級 AGENTS.md 範例 | aihero.dev 正文 |
| 決策框架表格（root / 獨立檔案 / 巢狀文件） | aihero.dev 正文 |
| 重構 prompt 五步驟原文 | aihero.dev 正文（與本次任務給定的 prompt 一致） |
| AGENTS.md 官方定義、與 README 分工的設計初衷 | [agents.md](https://agents.md/) |
| 60,000+ 專案採用、標準 Markdown、無必填欄位 | agents.md |
| Monorepo 巢狀 AGENTS.md、就近讀取機制 | agents.md |
| Aider / Gemini CLI 需要額外設定才能讀取 AGENTS.md | agents.md |
| VS Code / Cursor / GitHub Copilot 原生支援 | agents.md |
| aihero.dev 未拆分獨立子頁面（progressive disclosure / contradictions 皆在同一篇） | WebSearch 檢索確認（未找到獨立子頁） |
