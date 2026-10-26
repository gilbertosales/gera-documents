---
name: technical-documentation
description: Write, edit, review, restructure, or plan technical documentation for engineers and technical readers, including READMEs, setup guides, API docs, runbooks, troubleshooting pages, onboarding guides, architecture overviews, release notes, contributor guides, design documents, and knowledge-base pages. Use when the user asks to document a system, module, workflow, decision, or process; turn notes into a durable document; improve or rewrite an existing doc; review documentation quality; decide where documentation belongs; organize a documentation hierarchy; or keep docs from going stale. Prefer this skill whenever the output is prose that helps technical readers complete work.
---

# Technical Documentation

Produce documentation that gives readers accurate information fast.

That is the standard. If a document is hard to find, hard to scan, vague, stale, duplicated, or padded with unnecessary words, it fails even when the content is technically correct.

## Core Rule

Write for readers who are trying to leave.

Technical readers scan. They look for exact answers, commands, file paths, prerequisites, warnings, examples, and validation steps. They stop reading as soon as they find enough information to continue. If they lose trust once, they may stop trusting the whole documentation set.

Every documentation decision should serve two goals:

1. Keep the information accurate.
2. Make the information fast to find and use.

Read `references/principles.md` when the task involves documentation strategy, stale docs, duplicated knowledge, or the role of docs in a workflow.

## Workflow

Follow this sequence for new docs, rewrites, and reviews:

1. Define the intended reader.
2. State the one question or job the document answers.
3. Choose the canonical home for the content.
4. Check whether an existing page should be updated instead of creating a new one.
5. Sketch headings before writing paragraphs.
6. Draft the complete answer.
7. Revise for accuracy, hierarchy, scan speed, specificity, and concision.
8. Remove duplication and move durable answers out of conversations.
9. Validate anything readers will copy, click, or trust.
10. Publish or return the document in the place and format the user requested.

If you cannot state the reader and the document's job, ask a concise clarifying question before drafting. If the user supplied an existing document, infer the reader and job from the document first.

## Place Content Correctly

Before adding content, decide where it belongs. A clear sentence in the wrong place is still hard to use.

Use durable documentation for durable knowledge. Do not leave reusable answers buried only in chat threads, comments, tickets, code review discussions, meeting notes, or email chains.

Prefer one maintained hierarchy over multiple competing ones. If a topic could reasonably live in more than one place, choose one canonical home and link to it from elsewhere.

Read `references/information-architecture.md` when the user asks where documentation belongs, how to organize pages, whether to create or extend a page, or how to fix a messy documentation structure.

## Shape Pages for Scanning

Lead with the answer, outcome, or purpose. Put prerequisites near the top. Use headings, lists, tables, commands, examples, and validation steps where they reduce reader effort.

For procedural pages, use this default shape unless the content clearly needs a different one:

1. Purpose
2. Prerequisites
3. Steps
4. Verification
5. Troubleshooting
6. Related links

Do not force every page into one template. Architecture overviews, runbooks, onboarding guides, troubleshooting pages, and decision records have different needs. Keep the structure predictable enough that readers know where to look.

## Revise Sentences for Speed

Apply these rules on the revision pass:

- Say something once in one canonical place, then link to it.
- Cut filler such as `please`, `simply`, `just`, `in order to`, `you can`, and `this document will explain`.
- Replace vague references with exact names, paths, commands, versions, permissions, and page titles.
- Use one term consistently for each concept.
- Prefer lists when items are parallel, sequential, option-based, or easy to scan.
- Chunk distinct ideas under useful headings.
- Start action-oriented headings and list items with verbs.
- Prefer active voice, simple language, and direct phrasing.
- Avoid noun strings and unnecessary formality.
- Keep examples neutral unless the document is about a specific vendor, product, or organization.

Read `references/writing-rules.md` when rewriting prose, reviewing paragraph quality, or converting rough notes into polished documentation.

## Output Expectations

Default to Markdown unless the user asks for another format.

When writing or rewriting a document:

- Preserve accurate technical details from the source.
- Preserve existing anchors or headings when they are likely to have inbound links, unless changing them is necessary.
- Lead with the useful answer instead of a long introduction.
- Put prerequisites, assumptions, and constraints before the reader needs them.
- Use copy-pasteable commands and paths when possible.
- Include verification or troubleshooting steps when readers need to know whether the task worked.
- Avoid placeholders unless the reader must supply the value.
- Remove empty sections, stale statements, duplicate explanations, dead links, and template leftovers.

When reviewing a document:

- Report accuracy, structure, findability, duplication, and scan-speed issues before style nits.
- Give concrete fixes or replacement wording for high-impact problems.
- Flag claims, commands, links, paths, versions, or screenshots that need validation.

Before finalizing any substantial documentation output, use `references/checklist.md`.

## Reference Material

Load references only when the task needs them:

- `references/principles.md`: reader model, trust, accuracy, durable knowledge, stale content, and one source of truth.
- `references/information-architecture.md`: canonical homes, hierarchy design, page placement, ordering, and scalability.
- `references/writing-rules.md`: sentence-level and page-level rewrite rules with neutral examples.
- `references/checklist.md`: pre-publish and review checklist.
