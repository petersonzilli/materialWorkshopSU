---
name: briefing-intake
description: Assess whether a campaign briefing is complete and supported by company context before message strategy begins.
---

# Briefing Intake

Use this skill before message strategy. It assesses whether the briefing is sufficiently supported to proceed. It does not create strategy, copy, audience evaluations, channel adaptations, or rule validations.

## Required context

Identify the company and campaign. Read the campaign briefing and every relevant file in the company's `configurations/` directory, including:

```text
companies/<company>/campaigns/<campaign>/briefing.md
companies/<company>/configurations/company.md
companies/<company>/configurations/brand.md
companies/<company>/configurations/products.md
companies/<company>/configurations/rules.md
companies/<company>/configurations/audience-context.md
```

If a required source is missing, unreadable, or ambiguous, record that limitation and request human direction when it blocks a safe decision. Do not infer company or product facts.

## Select applicable configuration

- Treat `company.md`, `brand.md`, and sections marked **general** in `rules.md` as applying to every campaign for that company.
- In `products.md`, `audience-context.md`, and product-specific sections of `rules.md`, activate only a profile whose named product or offer is selected by the campaign briefing. An unrelated profile is not a required campaign input and must not create a conflict or constraint for this campaign.
- The briefing must identify at least one product/service or offer. A campaign may have no promotion when it clearly promotes an identified product/service.
- If the campaign selects a product or offer without a matching configuration profile, use only facts, terms, and requirements explicitly supplied for that campaign in the briefing. Do not borrow facts or rules from another profile. Ask a human when material information or applicable requirements are missing, or when the briefing conflicts with a matching profile.

## Assess the briefing

Confirm that it identifies at least one product/service or offer, the supplied target segment, requested objective, and supported product benefits. Record the channel, call to action, offer conditions, timing, constraints, source material, and assumptions when they affect later work.

Compare material briefing statements with the general company configuration and only the matching product, audience, and rule profiles, especially claims about:

- Product features, benefits, eligibility, price, availability, coverage, and offer conditions.
- Target definition, campaign objective, required disclosures, and prohibited messages.
- Channel and call to action, including whether requested elements are supported by the supplied context.

Separate supported facts from assumptions, unsupported claims, and unresolved questions. A gap or conflict is material when proceeding could make copy misleading, unsupported, unsafe, or impossible to evaluate against the applicable rules. Do not silently choose between conflicting sources. Keep non-material assumptions only when clearly labeled and when no one could mistake them for confirmed product, customer, eligibility, or campaign facts.

## Write an additive intake record

Do not edit `briefing.md`. Write `briefing-intake.md` in the campaign directory when no intake exists. If one already exists, preserve it and write `briefing-intake-reassessment-NN.md` using the next sequential number; explain what changed and which record is being reassessed.

Include:

- Company, campaign, and briefing/configuration sources reviewed.
- A concise account of the product, supplied segment, benefits, objective, channel, call to action, material conditions, and constraints.
- Confirmed facts later work may rely on.
- Assumptions, missing information, unsupported claims, and conflicts, each with evidence and materiality.
- The precise human question for each blocking issue.
- One decision: **Briefing ready** or **Human decision required**.
- The next allowed action: begin message strategy, or pause for the human decision.

State that the intake assesses the briefing and does not replace it or create new product facts.

## Decision rules

Choose **Briefing ready** only when the minimum inputs are present, material claims and conditions are supported, and no unresolved material gap or conflict blocks strategy work. Choose **Human decision required** when a material input is missing, a claim is unsupported, sources conflict, or necessary context cannot be read. Name the specific information or resolution needed.

After writing, reopen the intake record and verify that it contains the decision and supporting evidence. Stop at this decision boundary; do not create downstream marketing artifacts.

## Source attribution

Use source-attributed language: supplied briefing, recorded conditions, and user-provided direction. Describe what the sources state and what each review found. Never infer organizational endorsement of example data, user decisions, or generated content. Human input records information or direction for this run; ask for any facts that remain missing. All outputs remain drafts for human review. Include the demonstration notice specified by the loop prompt outside campaign copy fields.
