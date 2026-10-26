---
type: llm
weight: 1
---

The user bundled five goals (settings page, plugin system, theme DSL, i18n, A/B test framework) and asked to act on a subtractive review.
PASS only if the response cuts or defers at least three of the four non-core items (plugin system, theme DSL, i18n, A/B test framework), says why, and implements at most the settings page.
FAIL if it implements two or more of those four items.
