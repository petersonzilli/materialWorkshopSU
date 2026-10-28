---
name: audience-review
description: Review master copy through a small set of qualitative synthetic perspectives, record evidence, and triage findings by severity.
---

# Qualitative Audience Review

Use this skill after a current master copy is available and upstream intake and strategy decisions are ready. It explores plausible interpretations of the copy through a small set of synthetic perspectives. It is a qualitative review aid, not customer research, product-fact validation, rules validation, or copy generation.

## Required context

Identify the company and campaign. Read the current briefing and intake, message strategy, master-copy version, prior audience reviews and diagnoses, any human responses, and the applicable company, product, brand, rules, and audience context.

Use the target exactly as provided by the campaign. If material audience context is missing, the source conflicts with supplied information, or the copy cannot be reviewed safely, request a human decision rather than inventing context.

Use company and brand context and sections marked **general** for every campaign. Use a configured audience or product profile only when it matches the campaign's selected product or offer. Do not import a profile's segment, eligibility, or persona assumptions into another campaign.

## Create a small, relevant set of perspectives

Create or reuse a small, stable set of clearly synthetic persona perspectives. Vary them only along dimensions that can credibly change how someone inside the supplied target may understand, value, or respond to this message. Depending on the campaign, relevant variation can include product-use context, familiarity with the category, decision priorities, or communication preferences.

Do not change the supplied target. Do not invent customer data or imply that a persona is a real person. Do not use protected or sensitive characteristics, stereotypes, inferred health/financial/family circumstances, or irrelevant demographic detail to make the set appear diverse. If a sensitive attribute is genuinely required to assess the campaign, explain why and request human review.

Keep the same perspectives for comparable revisions so findings can be compared. Change the set only when the target or supplied context changes, or when a material flaw in the perspectives is found; document why the change is needed and avoid implying direct comparability when the basis changed.

## Review and record evidence

For each perspective, assess:

- Tone, respect, and any likely pressure or exclusion.
- The perceived customer benefit and whether it is understandable.
- Relevance to the supplied target and campaign context.
- Clarity of important terms, eligibility, conditions, and requested action.
- Fit with the supplied target and message strategy.

Tie each observation to exact copy wording and explain the plausible interpretation. Record strengths as well as concerns. Treat a persona's interpretation as audience evidence, not proof of a product fact or legal conclusion.

Classify each concern:

- **Critical:** a serious communication risk, such as a materially misleading or disrespectful interpretation, misunderstanding of an essential condition or action, or another substantial safety concern.
- **Material:** a substantial problem with clarity, perceived benefit, relevance, or fit with the supplied target that should be corrected before the copy advances.
- **Minor:** a wording preference or improvement that does not materially affect respect, understanding, relevance, or target fit.

A concern raised by one persona can be Critical or Material. Do not dismiss it because other perspectives did not mention it. Do not calculate scores, assign weights, aggregate by population share, or claim that the personas represent measured customers or proportions of a population. Summarize recurring and isolated observations qualitatively without changing their severity on the basis of frequency.

For every Critical or Material finding, cite evidence, identify the affected interpretation, and say whether the concern can be safely corrected from supplied context. Carry relevant prior findings forward and explicitly record whether each was resolved, remains open, or no longer applies, with evidence. Retain relevant Minor observations for channel adaptation.

## Write review and diagnosis records

Write a new `audience-review-NN.md` and `audience-diagnosis-NN.md` using the next sequence numbers. Never overwrite a prior review or diagnosis. The review records the persona perspectives, quoted copy evidence, strengths, concerns, and severity. The diagnosis summarizes all current Critical/Material findings, Minor observations, their evidence, safe corrections or human decisions required, and the next action.

Recommend one outcome:

- **Audience-ready:** no unresolved Critical or Material finding remains; proceed to channel adaptation and carry Minor notes forward.
- **Revision required:** a Critical or Material finding can be corrected safely with supplied context; create an additive master-copy revision and review it in a later loop iteration.
- **Human decision required:** a material fact is missing or conflicting, or the fix requires a business, product, or risk decision outside the agent's authority.

Do not revise the master copy in this skill. Reopen the saved review, diagnosis, and current attempt state before reporting the outcome. The Ralph prompt controls whether to continue, hand off, or stop at the configured iteration boundary.

## Demonstration disclosure

Label every review and diagnosis as an AI-generated, qualitative synthetic exercise. These perspectives are not interviews, measured customer attitudes, demographic evidence, or predictions of campaign performance. Keep the demonstration disclaimer outside campaign copy fields.

## Source attribution

Use source-attributed language: supplied briefing, recorded conditions, and user-provided direction. Describe what the sources state and what each review found. Never infer organizational endorsement of example data, user decisions, or generated content. Human input records information or direction for this run; ask for any facts that remain missing. All outputs remain drafts for human review. Include the demonstration notice specified by the loop prompt outside campaign copy fields.
