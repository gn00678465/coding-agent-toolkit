# Final Review Report

<!-- Rendered from final-report.json. Field values come from the JSON; only checkboxes are edited by humans. -->
<!-- Voting never checks items. Re-rendering carries each RF id's checkbox state over unchanged. -->

- `command`: `report`
- `feature`: <!-- final-report.feature -->
- `scope_sha256`: <!-- final-report.scope_sha256 -->
- `model_weights`: <!-- resolved weights, e.g. gpt-6.1-sol: 1.5, claude-opus-5-5: 1.0 -->
- `missing_voters`: <!-- models with no complete vote, or none -->
- `report_flags`: <!-- single_vendor | intent_inferred | missing_voters | has_stand_ins, or none -->
- `report_language`: <!-- auto | en | zh-TW | ... -->
- `created_at`: <!-- ISO 8601 timestamp -->

## Intent

<!-- intent.statement; append "(inferred, not confirmed by the user)" when intent.status is inferred. -->

## Reviewers

<!-- One bullet per reviewers entry, then one per voters entry. -->

- Reviewer `<label>`: `<model_used>` (`<vendor>`, `<kind>`), <findings_count> findings, `status`: `<status>`
- Voter `<label>`: `<model_used>` (`<vendor>`, `<kind>`), `status`: `<status>`

## Act On

<!-- act_on items. Each: what it is, which models raised it, why it matters. -->

- [ ] `RF-001` <!-- title -->
  - `severity`: <!-- severity --> · `confidence`: <!-- tier --> (<!-- score -->)
  - `raised_by`: <!-- sources --> · `confirm`: <!-- models --> · `dispute`: <!-- models --> · `unsure`: <!-- models --> · `abstain`: <!-- models -->
  - `why_it_matters`: <!-- why_it_matters -->
  - `affected_files`: <!-- path:line_start-line_end -->
  - `suggested_fix`: <!-- suggested_fix -->
  - `suggested_tests`: <!-- suggested_tests -->
  - `status`: `open` · `status_label`: <!-- localized label -->

## Consider

<!-- consider items, same shape as Act On with `tradeoff` in place of `why_it_matters`. -->

## Noted

<!-- noted items as one checkbox line each: `RF-xxx` title (severity, confidence, raised by). -->

## Dismissed

<!-- dismissed items, one checkbox line each plus `dismiss_rationale` drawn from dispute evidence. -->

## Unvoted

<!-- unvoted items, one checkbox line each with the reason no eligible vote exists. -->

## Agreement Map

| Model A | Model B | Shared votes | Agreement |
| --- | --- | --- | --- |
| <!-- model_a --> | <!-- model_b --> | <!-- shared_votes --> | <!-- agreement_rate, or n/a when null --> |

- `same_vendor_agreement`: <!-- rate or n/a -->
- `cross_vendor_agreement`: <!-- rate or n/a -->

<!-- agreement_map.pattern: where models agreed and diverged, and what that pattern suggests. -->
