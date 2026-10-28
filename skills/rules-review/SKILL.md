---
name: rules-review
description: Validate channel copy against applicable company rules, create supported revisions, and prepare evidence for human review.
---

# Rules Review

Use this skill after an audience-ready master copy has been adapted to the requested channel. It evaluates the copy against supplied company and campaign rules. Rules-ready means ready for human review; it is not approval to publish, send, or launch a campaign.

## Required context

Identify the company, campaign, and exact channel-copy version. Read that copy, the current audience-ready master copy and diagnosis, the briefing/intake, all applicable files in the company `configurations/` directory, and all prior rules findings and revisions. Include prior audience findings that affect wording, eligibility, or conditions.

If a required rule or source is missing or unreadable, request a human decision. Use the supplied configuration as the source of rules; do not invent legal requirements or product facts.

Apply company and brand context and sections marked **general** to every campaign. Evaluate a product-specific rule only when its named product or offer is selected in the briefing. A rule from another profile is not a campaign requirement. When the selected product or offer has no matching profile, use the applicable general rules and requirements explicitly recorded in its briefing; request human input for missing material terms or requirements instead of borrowing rules from another product.

## Evaluate each applicable rule

Review applicable brand, product, legal/compliance, campaign, and channel rules. Record each applicable rule with:

- Its source file and priority (**MUST**, **SHOULD**, or **COULD**).
- Exact evidence from the channel copy, or a clear note that required evidence is absent.
- Whether the copy complies, the concern and its severity, and any supported correction.

Do not treat a broad statement of intent as proof that a specific requirement passes. A MUST violation blocks readiness. A SHOULD departure must have a visible, supported rationale and any downstream mitigation. A COULD item is optional; record whether it was used only when that helps the human review.

## Correct and revalidate

When a violation can be corrected using supplied information and rules, create a new channel-copy revision. Preserve the prior copy and validation, address all relevant earlier findings, and perform a full revalidation of every applicable rule on the revised copy; checking only the original failed rule is insufficient.

If correcting channel copy would materially change the reviewed central message, do not silently rewrite it. Record the rules evidence, return the finding to the audience/master-copy loop for a new master-copy revision and qualitative review, and retain the rules finding as input to that review.

Request human direction when a material fact is missing or conflicting, the rules themselves conflict, or a safe correction requires a decision outside the agent's authority. State the blocker, evidence, exact decision or action needed, and relevant attempt history.

## Write additive evidence and decide

Write `rules-validation-NN.md` using the next sequential number for every validation attempt. Never overwrite earlier channel copy or validation evidence. Record the evaluated version, sources, every applicable rule and outcome, findings, supported corrections, and remaining human-review notes.

Choose **Rules-ready** only when all applicable MUST rules pass and every applicable SHOULD departure is documented. Then write `human-review-package.md` with the current master copy, current channel copy, important audience findings, rules result, and remaining review notes. State that no publication or sending is authorized.

Choose **Revision required** when a supported correction remains and another iteration is permitted. Choose **Human decision required** for an unresolved material fact, conflict, or decision outside the process's authority. Choose **Audience recheck** if a correction materially changes the central message. Reopen the saved validation and package, when applicable, to confirm their evidence and outcome before reporting completion.

## Demonstration disclosure

Include the demonstration disclaimer required by the loop prompt in generated evidence and the human-review package. Clearly distinguish automated checking of supplied fictional rules from legal or regulatory review. Keep disclosure text outside campaign copy fields and their character counts.

## Source attribution

Use source-attributed language: supplied briefing, recorded conditions, and user-provided direction. Describe what the sources state and what each review found. Never infer organizational endorsement of example data, user decisions, or generated content. Human input records information or direction for this run; ask for any facts that remain missing. All outputs remain drafts for human review. Include the demonstration notice specified by the loop prompt outside campaign copy fields.
