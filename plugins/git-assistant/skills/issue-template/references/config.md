# 入口分流配置檔範本 (`config.yml`)

目標路徑：`.github/ISSUE_TEMPLATE/config.yml`

> - 僅將 Step 1 確認**已啟用**的管道列入 `contact_links`。
> - 若無任何有效外部連結，**完全省略 `contact_links` 區塊**，只寫單行 `blank_issues_enabled: false`（GitHub Schema 禁止 `contact_links: []` 空陣列）。

## 繁體中文版（預設）

```yaml
blank_issues_enabled: false
contact_links:
  - name: 💬 技術問答與使用求助 (Q&A & Discussions)
    url: https://github.com/OWNER/REPO/discussions
    about: 遇到設定疑問、使用方式不確定或想與社群交流？請前往 Discussions 提問，切勿建立 Bug Issue。
  - name: 🔒 資安漏洞私密通報 (Security Vulnerability)
    url: https://github.com/OWNER/REPO/security/advisories/new
    about: 若發現潛在的資安風險，請透過私密管道通報，請勿於公開 Issue 中揭露漏洞細節。
```

## English Version

```yaml
blank_issues_enabled: false
contact_links:
  - name: 💬 Q&A and Discussions
    url: https://github.com/OWNER/REPO/discussions
    about: Have a question about configuration or usage? Please ask in GitHub Discussions instead of opening a bug issue.
  - name: 🔒 Report a Security Vulnerability
    url: https://github.com/OWNER/REPO/security/advisories/new
    about: Please report potential security vulnerabilities privately via Security Advisories rather than in a public issue.
```
