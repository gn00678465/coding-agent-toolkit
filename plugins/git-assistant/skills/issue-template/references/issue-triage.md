# 自動化分流工作流範本 (`issue-triage.yml`)

目標路徑：`.github/workflows/issue-triage.yml`

> 部署此 workflow 前，請確認對應的 `area:*` 標籤已於儲存庫建立（或由具有 `issues: write` 權限的 `addLabels` 自動附加）。

```yaml
name: Issue Triage Automation

on:
  issues:
    types: [opened]

permissions:
  issues: write

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - name: Auto-assign labels based on Affected Area
        uses: actions/github-script@v7
        with:
          script: |
            const body = context.payload.issue.body || '';
            const match = body.match(/### (?:受影響的模組區域 \(Affected Area\)|Affected Area)\s+([^\r\n]+)/);
            if (!match || !match[1]) return;
            const selectedArea = match[1].trim();
            const labelMap = {
              '核心引擎 (Core / Runtime)': 'area:core',
              'Core / Runtime': 'area:core',
              '命令列工具 (CLI / Tooling)': 'area:cli',
              'CLI / Tooling': 'area:cli',
              '介面與元件 (UI / Components)': 'area:ui',
              'UI / Components': 'area:ui',
              '建置與設定 (Build / Config)': 'area:build',
              'Build / Config': 'area:build',
              '文件與型別 (Docs / Types)': 'documentation',
              'Docs / Types': 'documentation'
            };
            const targetLabel = labelMap[selectedArea];
            if (targetLabel) {
              await github.rest.issues.addLabels({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.payload.issue.number,
                labels: [targetLabel]
              });
            }
```
