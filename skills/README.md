# Active Marketing Workflow Skills

This directory contains the reusable skills used by the application's Ralph prompts. Skills are shared across companies; company and brand context is general, while product, audience, offer, and channel facts belong in the selected company's configuration and campaign briefing.

Company configurations distinguish general sections from named product, offer, and audience profiles. General company/brand guidance and rules apply to every campaign. Activate a named profile only when the briefing selects that product or offer. A campaign must identify a product/service or offer; a promotion is optional when the product/service itself is clear. For a product or offer without a catalog profile, use only campaign facts and requirements explicitly recorded in its briefing and ask a human about material gaps. Never borrow facts, eligibility, audience criteria, or rules from an unrelated profile.

Each skill has one bounded responsibility. It reads supplied context, writes an additive campaign artifact, and records the decision and next step. Campaign files are the persistent working memory for later Ralph sessions. A fresh session must use the saved records rather than relying on chat history.

## Workflow

| Skill | Responsibility | Typical artifact |
| --- | --- | --- |
| `briefing-intake` | Check whether the briefing is complete and supported by company context. | `briefing-intake.md` |
| `message-strategy` | Connect confirmed product benefits to a relevant customer benefit and credible hook. | `message-strategy.md` |
| `master-copy` | Create or revise the central campaign message. | `master-copy.md` and additive revisions |
| `audience-review` | Review master copy through qualitative synthetic perspectives and triage findings. | `audience-review-NN.md`, `audience-diagnosis-NN.md` |
| `channel-adaptation` | Adapt audience-ready copy to the requested channel. | `channel-copy.md` and additive revisions |
| `rules-review` | Validate channel copy and create a human-review package when ready. | `rules-validation-NN.md`, `human-review-package.md` |

The audience/master-copy loop covers intake, strategy, master-copy generation, and qualitative review. A correctable Critical or Material finding sends the next attempt back through a new master-copy revision and review. When audience review is ready, work advances to the rules/channel loop. A safe channel correction gets a new copy revision and full rules revalidation. A material change to the central message returns to audience review; unresolved facts, conflicts, or decisions outside the agent's authority request human input.

## Qualitative persona policy

Personas are synthetic perspectives used to explore possible interpretations of copy. They are not customer research and do not represent a measured population. The active workflow uses no persona weights, population shares, weighted scores, or population-level aggregation. Findings are triaged as Critical, Material, or Minor using the evidence and definitions in `audience-review/SKILL.md`.

## Persistent records and human review

Skills preserve earlier artifacts. Reassessments and corrections use the next sequential filename so reviewers can trace what changed and why. Required facts are never invented to make work advance. When a decision requires human input, the relevant skill records the blocker, evidence, and specific action needed.

`rules-review` can only mark copy ready for human review. The application does not approve, send, or publish campaigns.
