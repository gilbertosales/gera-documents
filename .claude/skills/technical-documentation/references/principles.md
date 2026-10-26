# Technical Documentation Principles

## The Standard

Technical documentation exists to give people accurate information fast.

Good documentation reduces the time between a reader having a question and the reader being able to do the work. The goal is not to create more pages. The goal is to create a trusted body of knowledge that people use before interrupting someone else.

## Reader Model

Write with the reader's behavior in mind:

- Readers scan instead of reading linearly.
- Readers satisfice: they stop as soon as they find enough information to move forward.
- Readers are trying to complete a task, unblock themselves, verify a detail, or make a decision.
- Readers leave when a page looks slow, vague, or unreliable.
- Readers may stop trusting a documentation set after one wrong or stale instruction.

Accuracy comes first because inaccurate documentation is worse than missing documentation. Missing information creates friction. Wrong information destroys trust.

Speed comes next because a correct document that is slow to use still pushes readers back toward asking people directly.

## Documentation as Durable Knowledge

Use conversations for conversation. Use durable documentation for durable knowledge.

Important answers should not live only in chat threads, page comments, tickets, code review discussions, meeting notes, or email chains. Those places are useful while people are discovering the answer. They are poor places to store the answer once it is known.

When a conversation produces reusable knowledge, move the knowledge into the document itself. If a ticket clarifies a process, update the relevant page. If a code review discussion explains why a configuration exists, add that explanation where future maintainers will look. If a chat answer resolves a common question, add it to the guide and send the link next time.

## Make Documentation Part of the Work

Documentation stays useful only when it changes with the system. Treat documentation like tests: part of the change, not a cleanup task to remember later.

When behavior changes, ask:

1. What document needs to change?
2. Does that document already exist?
3. If it does not exist, should it exist?

Add or update documentation when the information:

- Will be needed again.
- Is easy to forget.
- Matters beyond one person or one moment.
- Is already being asked about repeatedly.

Do not create a page just because a page can exist. A page that no one needs becomes clutter, and clutter slows down the entire documentation system.

The work is not finished when the implementation changes. The work is finished when future readers can understand and use the change without reconstructing it from conversations.

## Keep One Source of Truth

Duplicate documentation looks helpful at first because the same answer appears in several places. It creates uncertainty as soon as one copy changes and another does not.

Say something once in one canonical place. Link to it when other pages need the same information.

Duplicate content causes three common failures:

- Readers waste time deciding which version is correct.
- Writers update one copy and forget the others.
- Search results show several similar answers with different levels of freshness.

The solution is not to hide information. The solution is to make one page authoritative and make other pages point to it clearly.

## Remove What Gets in the Way

Good documentation is not only written. It is pruned.

Remove:

- Outdated content.
- Duplicate content.
- Empty sections.
- Stub pages that do not help current readers.
- Dead links.
- Misleading page titles.
- Navigation paths that lead nowhere.
- Long introductions that delay the answer.
- Sections that exist only because a template created them.
- Obsolete screenshots, diagrams, commands, or examples.

Remove outdated content first. It is the highest-cost problem because it damages trust. Fix it if it can be validated quickly. Remove it if it cannot. Redirect to the correct source if another page has replaced it.

Pruning is performance work. The less noise readers encounter, the more likely they are to trust and reuse the documentation.
