# Writing Rules

Use these rules during the revision pass. First make the document accurate and complete enough to be useful. Then revise for hierarchy, scan speed, specificity, and concision.

## Lead With the Answer

A page should reveal its value quickly, even to someone who reads only headings, lists, commands, and examples.

Lead with the answer, outcome, or purpose:

- If the page tells readers how to rotate a key, say that immediately.
- If it explains why a service has a particular design, state the design decision before giving history.
- If it compares options, show the recommendation near the top.

Put prerequisites early. Readers should not discover halfway through a procedure that they need access, a specific version, a feature flag, or a prepared environment.

## Use Predictable Page Shapes

For procedural pages, use this default structure when it fits:

1. Purpose
2. Prerequisites
3. Steps
4. Verification
5. Troubleshooting
6. Related links

Do not force every page into the same template. Give readers a recognizable pattern so they know where to look.

## Say It Once

Do not repeat the same explanation across multiple pages or multiple sections of the same page.

- Write the primary explanation once.
- Link back to it when needed.
- Avoid near-duplicate summaries that will drift over time.

## Cut Extra Words

Be concise. Extra words slow the reader down.

| Weak | Better |
|---|---|
| The application is using a feature flag service in order to run an A/B test. | The application uses a feature flag service to run an A/B test. |
| You will simply need to provide the end string. | Provide the end string. |
| This document will explain how to configure the worker. | Configure the worker as follows. |
| This is to ensure the application remains in a good and, more importantly, functional state. | This keeps the application functional. |

Common filler to remove:

- `please`
- `simply`
- `just`
- `in order to`
- `you can`
- `this document will explain`

## Be Specific

Specific writing is faster than vague writing.

Prefer:

- Exact file paths over "the config file".
- Exact versions over "recently" or "latest" unless the version is intentionally variable.
- Exact names over "the team" or "the service" when the exact name is known.
- Exact commands over paraphrases.
- Exact page titles over "the other doc".

Every vague phrase creates work for the reader.

## Use One Term for One Thing

Be consistent.

If a component is called `event processor`, do not also call it `worker`, `task runner`, and `background job` unless those names mean different things.

The same rule applies to links and headings:

- Link text should match the destination heading when possible.
- Section names should stay stable unless the meaning changes.

Consistency reduces hesitation.

## Prefer Lists Over Paragraphs

Lists are easier to scan than dense prose.

Use a list when:

- Items are parallel.
- Steps must be completed in order.
- You are naming options, requirements, causes, or outcomes.

Use paragraphs when the reader actually needs connected explanation. Do not turn everything into prose by default.

## Chunk Content Under Useful Headings

Every distinct idea deserves its own heading or subheading.

Good headings help readers:

- Skip irrelevant content.
- Build a mental map of the page.
- Return later and find the same section again.

Long unbroken text blocks are hard to scan, hard to maintain, and easy to abandon.

## Start Action Phrases With Verbs

Verb-led phrasing is easier to process because it tells the reader what action or concept matters.

Prefer:

- `Use and Contribute` over `Using and Contributing`
- `Format a change request` over `Change request format`
- `Set up the component` over `Component setup`
- `Include the component on your page` over `Including the component on your page`

This also helps avoid nominalizations: turning verbs into nouns when direct action would be clearer.

## Use Active Voice

Active voice is usually shorter and clearer.

Prefer:

- `Use the package manager to install packages.`
- `The deployment job creates the release tag.`
- `The service reads configuration from config.yaml.`

Avoid:

- `The package manager is used to install packages.`
- `The release tag is created by the deployment job.`
- `Configuration is read by the service from config.yaml.`

Passive voice hides who does what and usually adds words.

## Use Simple Language

Write the way engineers talk when they are being clear.

Prefer:

- `must` over `one must`
- `use` over `utilize`
- `before` over `prior to`
- `if` over `in the event that`

Simple language is not less technical. It is faster.

## Drop Politeness Padding

Instructional writing does not need conversational padding.

Prefer:

- `Install the version manager and use it to install the runtime.` over `Please install the version manager and then you can use it to install the runtime.`
- `Use the sidebar to navigate the documentation.` over `For navigating the documentation better please use the sidebar.`
- `Choose one of these options.` over `You can choose one of these options.`

Clarity matters more than courtesy formulas in a procedural document.

## Avoid Noun Strings

Long stacks of nouns force the reader to unpack the sentence.

Prefer:

- `the process for restoring a failed cache after deployment`

Instead of:

- `post-deployment cache restoration failure response process`

If a phrase sounds compressed or bureaucratic, rewrite it.

## Avoid Unnecessary Formality

Formal language often adds distance without adding precision.

Write as if explaining the work clearly to another engineer at a desk. Keep the tone direct, plain, and factual.
