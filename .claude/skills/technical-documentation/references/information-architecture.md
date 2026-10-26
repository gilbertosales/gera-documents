# Information Architecture

## Choose the Right Home

Before writing, decide where the content belongs. Information architecture matters as much as sentence quality.

Use this placement model:

| Information type | Better home | Expected lifespan |
|---|---|---|
| Quick conversation, status, and one-off questions | Chat or comments | Minutes to days |
| Research notes or decisions in progress | Issue tracker, design document, or project workspace | Days to weeks |
| Repository-specific setup, behavior, and operations | Repository documentation | Months to years |
| Cross-team concepts, policies, workflows, and shared systems | Central documentation hub or knowledge base | Months to years |

The placement decision should be obvious to future readers. They should not need to guess which tool, space, repository, or page contains the trusted answer.

## Create or Extend

Before creating a new page, ask:

1. Does a page already answer this question?
2. Does a page already cover the same workflow, system, or decision?
3. Would adding this content to an existing page make that page more complete?
4. Would a new page create a competing source of truth?

Extend an existing page when it is already the canonical home or when readers would expect to find the answer there.

Create a new page when:

- The document has a distinct reader or job.
- The existing page would become too broad or difficult to scan.
- The content has a different lifecycle or owner.
- The new page can be linked clearly from a parent page.

Do not leave orphaned pages. Every durable page should be reachable through navigation, not only search.

## Build One Hierarchy

A documentation set is a system, not a pile of pages.

Build one hierarchy and maintain it:

- Group related content together.
- Put setup near setup.
- Put troubleshooting near troubleshooting.
- Put architecture near architecture.
- Put policies near policies.
- Choose one canonical home when a topic could live in more than one place.
- Link from secondary locations instead of duplicating the content.

One maintained hierarchy gives readers confidence. Multiple competing hierarchies create hesitation, duplication, and drift.

## Order Navigation Intentionally

Navigation communicates before a reader opens any page. Choose an order on purpose.

Useful ordering patterns:

- Most important first.
- Most frequently used first.
- Chronological order.
- Dependency order, where one thing must exist before the next.

Do not leave ordering accidental. Accidental order makes the system feel arbitrary.

## Limit Depth or Breadth

Hierarchies usually work best in one of two shapes:

- Flat: fewer levels, more options per level.
- Deep: more levels, fewer options per level.

Flat hierarchies work well when the domain is simple and the top-level choices are obvious.

Deep hierarchies work well when the subject is complex but each click remains a clear, unambiguous choice.

Avoid a hierarchy that is both broad and deep. That gives readers too many choices at every step.

## Make the Structure Scalable

A useful hierarchy works today and still works after the content grows.

When designing or reviewing navigation, ask:

- Where will future topics go?
- Will this category still make sense when it has more content?
- Are there top-level buckets that can absorb related pages over time?
- Is this exception likely to become a pattern?

Scalability matters because documentation is a living system, not a one-time artifact.
