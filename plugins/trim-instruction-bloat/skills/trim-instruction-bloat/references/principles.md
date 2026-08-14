# 原理與判準來源

本 skill 判準背後的第一性原理。主要來源：Matt Pocock (AI Hero) 的 [A Complete Guide to AGENTS.md](https://www.aihero.dev/a-complete-guide-to-agents-md) 與官方慣例網站 [agents.md](https://agents.md/)。

## 為什麼 AGENTS.md 會肥大

肥大來自一個「自然回饋迴圈」（natural feedback loop）：agent 的行為讓你失望 → 你加一條規則防止重演 → 持續數月 → 得到「an unmaintainable mess that actually hurts agent performance」。另一個來源是自動產生的內容，把「對大部分情境有用」但其實該延遲揭露的東西全部塞進同一個檔案。（來源：aihero.dev）

## 肥大的三種代價

### 1. Instruction budget（指令預算）

引用 Kyle（HumanLayer，[Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md)）：

> Frontier thinking LLMs can follow ~150-200 instructions with reasonable consistency. Smaller models can attend to fewer instructions than larger models, and non-thinking models can attend to fewer instructions than thinking models.

AGENTS.md 裡的每個 token 在**每一次請求**都會被載入，不論與當前任務是否相關。檔案越小，留給任務專屬指令的 token 越多；檔案越大，agent 越容易混亂、遵循度越低。這是「root 只留與每個任務都相關的內容」這條測試的直接依據。

### 2. Context 毒化（poisoning）

過時資訊會主動毒化 context，不只是佔空間。例：AGENTS.md 寫著「authentication logic lives in `src/auth/handlers.ts`」但該檔案已搬移，agent 會「confidently look in the wrong place」。這是 Step 1 要對照 repo 驗證路徑與命令、Step 5 把 Stale 列為刪除判準的依據。（來源：aihero.dev）

### 3. 指令衝突

靠回饋迴圈一條條累積規則、缺乏整體審視，必然產生互相矛盾的指令。矛盾比單純冗長更嚴重：agent 無論遵循哪一條都可能違反另一條，直接損害正確性與可預測性。這是 Step 2 放在最前面的依據——矛盾必須趁雙方還並列可見時解決，且裁決權屬於使用者。

## Progressive disclosure 的定義與機制

定義（aihero.dev）：「give the agent only what it needs right now, and point it to other resources when needed」——只給 agent 當下需要的東西，需要時再指向其他資源。

機制：root 極簡 + markdown 連結指向分類文件，agent 按需讀取。效果：

- TypeScript 規則只在寫 TypeScript 時載入
- 其他任務（CSS debug、依賴管理）不浪費 token 讀不相關規則
- 檔案保持聚焦，換模型時仍可攜

決策框架（aihero.dev）：

| 位置 | 適用時機 |
|------|----------|
| Root AGENTS.md | 與 repo 中**每一個**任務都相關 |
| 獨立檔案 | 只與單一領域相關（TypeScript、testing 等） |
| 巢狀文件 | 可依階層組織、逐層深入 |

Root 最小集的原文結論：「That's honestly it. Everything else should go elsewhere.」

## 巢狀階層與 monorepo

分類文件可以再形成巢狀階層：

```
docs/
├── TYPESCRIPT.md（內部再連結 TESTING.md）
├── TESTING.md（內部再連結特定 test runner 說明）
└── BUILD.md（內部再連結 esbuild 設定）
```

Monorepo 情境下，多個 AGENTS.md 可在不同層級並存：

| 層級 | 內容 |
|------|------|
| Root | monorepo 目的、如何在各 package 間導覽、共用工具 |
| Package | 該 package 的目的、技術棧、專屬慣例 |

agents.md 官方站印證此機制：agent 會自動讀取目錄樹中**最近**的 AGENTS.md（nearest file in the directory tree）。

## 五步驟順序的第一性原理

原始提示詞的順序遵守「**先解決錯誤（矛盾）→ 再解決結構（本質、分組、落地）→ 最後解決效率（刪減）**」：

1. **矛盾最先**：唯一無法由 agent 單方面解決的問題（兩個互斥的人類意圖），且拆散結構後矛盾更難被發現。
2. **本質在分組之前**：先劃出「永遠載入」的 root 基準線，分組的輸入才是「扣除本質後的殘餘」，避免 package manager 這類 root 內容被誤歸進 BUILD.md。
3. **分組在結構落地之前**：先知道有哪些類別，才能決定建立哪些檔案。
4. **刪除標記在分組之後**：冗餘與空洞要跟同類規則並列比較才顯現；且用「flag」而非直接刪除，保守地把最終裁決留給使用者。
5. **實際寫檔最後**：分析完整之前落地，架構決策極可能要推翻重做；覆寫使用者的檔案前必須取得確認。

## AGENTS.md 與 CLAUDE.md 的關係

CLAUDE.md 是 Claude Code 對 AGENTS.md 這個工具中立（tool-agnostic）開放慣例的等價實作。agents.md 官方站列出各工具的支援方式（VS Code／Cursor／Copilot 原生支援；Aider／Gemini CLI 需額外設定）。因此本 skill 的所有判準同樣適用於 CLAUDE.md：它同樣每次請求都被載入、同樣累積回饋迴圈式規則、同樣需要 progressive disclosure。實務上許多團隊讓 CLAUDE.md 成為 AGENTS.md 的 symlink、`@AGENTS.md` 匯入指標或等價內容。

兩檔並存且各自維護實質內容時，就是同一份事實存在兩份副本——違反 single source of truth，漂移（drift）只是時間問題：規則會先在其中一份被更新，另一份逐漸過時，最後兩檔對同一件事各說各話（等同於自製的跨檔矛盾）。這是 skill 在雙檔漂移情境下提案「主內容集中於 AGENTS.md + CLAUDE.md 只留指標」的依據：AGENTS.md 是工具中立的一份，指標檔沒有可漂移的內容。
