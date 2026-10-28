---
name: message-strategy
description: Connect confirmed product benefits to a supported customer benefit and credible message hook without generating copy.
---

# Message Strategy

Use this skill after the current briefing-intake record says **Briefing ready**. It defines the customer value and message direction for the master copy. It does not write headlines, creative copy, channel copy, personas, or validation findings.

## Required context

Identify the company and campaign. Read the current briefing and intake record with applicable company, brand, product, rules, and audience context. Read any current campaign artifact that changes the current message direction.

If the intake is not ready, a required source is absent or unreadable, or supplied context conflicts materially, request a human decision instead of inferring missing product, audience, or campaign facts.

Apply company and brand context and sections marked **general** to every campaign. Use a product, offer, audience, or rule profile only when its named product or offer is selected in the briefing. For a different selected product/offer, rely only on facts explicitly recorded in its briefing or matching configuration; never import details from another profile.

## Develop the strategy

Distinguish:

- **Source-supported information:** explicitly recorded in the campaign briefing or company configuration.
- **Inferences:** explain how a confirmed fact may matter to the supplied target in this campaign.
- **Assumptions:** unconfirmed, non-material working premises that are clearly labeled.
- **Unresolved questions or conflicts:** require human direction when they affect a defensible strategy.

Explain why a confirmed product benefit is relevant to the supplied target. State one concrete customer benefit and one credible hook that gives the target a reason to pay attention. A customer benefit expresses value to the person; it is more than a restatement of a feature.

Do not introduce product or campaign facts, guarantees, price, offer, availability, eligibility, coverage, suitability, urgency, scarcity, financial outcomes, or family outcomes that are absent from supplied context. Respect the company voice and rules. Do not use pressure, fear, guilt, or stereotypes. If materially different strategies are plausible and the choice changes the campaign's meaning, explain the trade-offs and ask a human to choose.

## Write an additive strategy record

Do not edit the briefing or intake. Write `message-strategy.md` when no strategy exists. If one exists, preserve it and create `message-strategy-reassessment-NN.md` using the next sequential number; explain what changed and which earlier strategy is being reassessed.

Include:

- Company, campaign, and sources reviewed.
- The intake decision and confirmed facts used.
- Relevant inferences, labeled assumptions, and unresolved questions or conflicts.
- The customer benefit and hook, or why they cannot safely be established.
- One decision: **Message strategy ready** or **Human decision required**.
- The next allowed action: create the master copy, or pause for a human decision.

State that the strategy record is not customer-facing copy and does not create product facts. Reopen the saved record to verify the decision and source basis, then stop at this boundary.

## Source attribution

Use source-attributed language: supplied briefing, recorded conditions, and user-provided direction. Describe what the sources state and what each review found. Never infer organizational endorsement of example data, user decisions, or generated content. Human input records information or direction for this run; ask for any facts that remain missing. All outputs remain drafts for human review. Include the demonstration notice specified by the loop prompt outside campaign copy fields.
