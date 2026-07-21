# Storage Assistant Backend Architecture

Version: 1.0

---

# 1. Introduction

Storage Assistant is an AI-assisted storage analysis engine designed to solve one of the biggest limitations of traditional storage cleaners.

Traditional storage cleaners are built around one simple idea:

> Scan the filesystem → Find temporary files → Delete them.

While this approach works for browser cache or temporary files, it completely fails when the user actually wants to answer questions such as:

• Why is my C drive full?

• Which application is consuming storage?

• Which folders are actually important?

• Which files are safe to remove?

• What can be deleted without breaking Windows?

Instead of being a "Cleaner", Storage Assistant is designed as a **Storage Intelligence Engine**.

Its primary responsibility is understanding storage.

Cleaning becomes a consequence of understanding rather than the primary goal.

---

# 2. Design Philosophy

Every architectural decision inside the backend follows a small set of engineering principles.

## Principle 1

Filesystem should be touched only once.

Repeated filesystem traversal is one of the biggest performance bottlenecks.

Instead, Storage Assistant performs a single scan, stores everything inside SQLite and every later subsystem works entirely from indexed data.

Filesystem

↓

SQLite

↓

Everything Else

---

## Principle 2

AI should never see raw filesystem data.

Large Language Models perform better when given structured semantic information instead of millions of unrelated files.

Instead of sending:

1,200,000 files

The backend sends:

• Important folders

• Cleanup summaries

• Folder relationships

• Storage statistics

This dramatically reduces token usage while improving reasoning quality.

---

## Principle 3

Business Logic is independent from AI.

Every important decision inside the application must still work even if every AI provider becomes unavailable.

Therefore:

Scanner

Rule Engine

Database

Folder Analysis

Cleanup Classification

all work without AI.

AI only enhances recommendations.

---

## Principle 4

Every module should solve exactly one problem.

Instead of one large backend,

the system consists of multiple independent modules.

Examples:

MFT Scanner

↓

only scans.

Folder Analyzer

↓

only aggregates.

Rule Engine

↓

only evaluates rules.

Prompt Builder

↓

only creates prompts.

Provider

↓

only communicates with APIs.

This follows the Single Responsibility Principle.

---

## Principle 5

Every expensive operation should happen only once.

Folder sizes

↓

calculated once.

SQLite

↓

stores results.

Dashboard

↓

reads precomputed values.

Instead of recalculating folder sizes every time the user opens a folder.

---

# 3. Problems Traditional Storage Cleaners Cannot Solve

Modern Windows installations are no longer simple.

Storage is distributed across:

• User files

• AppData

• ProgramData

• Temporary folders

• Browser cache

• IDE cache

• AI model cache

• Game launchers

• Windows components

Traditional storage cleaners usually treat every folder independently.

They rarely understand relationships between folders.

Example:

AppData

└── Google

└── Chrome

└── Cache

Traditional Cleaner

↓

Shows Cache folder.

Storage Assistant

↓

Knows

Google

↓

Chrome

↓

Cache

↓

Browser Cache

↓

Safe Cleanup Candidate

Meaning exists.

Not just location.

---

# 4. High-Level Backend Architecture

The backend follows a layered architecture.

Presentation Layer

↓

Application Layer

↓

Core Engine

↓

Rule Engine

↓

Analysis Layer

↓

AI Layer

↓

Persistence Layer

↓

Infrastructure Layer

Each layer communicates only with the layer directly below it.

No module is allowed to bypass the architecture.

---

# 5. Layer Responsibilities

## Presentation Layer

Responsible for:

• Dashboard

• Cards

• Sidebar

• Progress

Never performs storage analysis.

Never touches filesystem.

Never calls providers.

---

## Application Layer

Acts as the orchestrator.

Responsible for:

• Starting scan

• Progress updates

• Calling backend modules

• Handling user actions

---

## Core Engine

Responsible for converting filesystem metadata into structured storage information.

Modules include:

• MFT Scanner

• Size Resolver

• Storage Scope

• Folder Analyzer

---

## Rule Engine

Responsible for deterministic cleanup logic.

AI is never involved here.

The Rule Engine determines:

• Protected

• Safe

• User Data

before AI analysis begins.

---

## Analysis Layer

Converts raw storage information into meaningful cleanup summaries.

Examples:

Cleanup Items

↓

Cleanup Groups

↓

Folder Clusters

↓

Statistics

---

## AI Layer

Transforms structured storage information into natural language reasoning.

This layer contains:

Cluster Builder

Boundary Resolver

Candidate Selector

Payload Builder

Prompt Builder

Provider Manager

Iterative Analyzer

Response Validation

---

## Persistence Layer

SQLite acts as the application's source of truth.

Everything after scanning reads from SQLite.

Nothing repeatedly scans the disk.

---

## Infrastructure Layer

Provides shared services.

Examples:

Memory Manager

Configuration

Logging

Metrics

---

# 6. Why SQLite Becomes The Source of Truth

The most expensive operation in the entire application is reading the filesystem.

Doing this repeatedly would make navigation extremely slow.

Instead:

Filesystem

↓

MFT

↓

SQLite

↓

Dashboard

↓

AI

↓

Reports

↓

Search

↓

Recommendations

SQLite becomes the central storage engine.

Every subsystem now shares the exact same indexed data.

This guarantees consistency across the application.

---

# 7. Complete Backend Overview

At a high level the backend performs only four major tasks.

Acquire Data

↓

Understand Data

↓

Reason About Data

↓

Present Information

Everything inside the project is ultimately part of one of these four stages.

The remaining chapters explain each stage in detail.

# Chapter 2 — Complete Scan Lifecycle

---

# 8. Backend Execution Lifecycle

The backend is designed as a sequential data transformation pipeline.

Every stage receives structured information from the previous stage, transforms it into a higher-level representation, and passes it to the next stage.

At no point does a later stage need to revisit the filesystem.

The lifecycle begins when the user initiates a storage scan.

```
User Clicks Scan
        │
        ▼
Application Controller
        │
        ▼
MFT Scanner
        │
        ▼
Raw NTFS Metadata
        │
        ▼
File Classification
        │
        ▼
SQLite Index
        │
        ▼
Folder Aggregation
        │
        ▼
Rule Evaluation
        │
        ▼
Cleanup Analysis
        │
        ▼
AI Pipeline
        │
        ▼
Dashboard
```

Every stage has exactly one responsibility.

---

# 9. Stage 1 — Scan Initialization

## Problem

The application needs to analyze an entire drive while keeping the user interface responsive.

A naive implementation would execute the scan directly inside the UI thread.

This immediately freezes the application.

---

## Challenge

Scanning millions of files can take several seconds.

The user must still be able to:

- move the window
- cancel operations
- observe progress
- receive status updates

---

## Solution

The scan is initialized through the Application Layer.

Responsibilities include:

- preparing runtime state
- creating database
- clearing previous scan information
- initializing memory tracking
- initializing progress reporting

At this stage no filesystem operations occur.

The application simply prepares the execution pipeline.

---

# 10. Stage 2 — MFT Acquisition

## Problem

Recursive traversal using os.walk() performs extremely poorly on modern SSDs containing hundreds of thousands of files.

Each directory requires filesystem calls.

Each file requires metadata lookups.

Performance degrades rapidly.

---

## Traditional Approach

```
Directory

↓

Subdirectory

↓

Subdirectory

↓

Files

↓

Repeat
```

Every folder requires another filesystem operation.

---

## Storage Assistant Approach

Instead of traversing folders,

the application reads the Master File Table directly.

```
NTFS Volume

↓

Master File Table

↓

Metadata Entries
```

The MFT already contains:

- path
- size
- timestamps
- attributes
- directory relationships

The filesystem has already indexed this information.

Storage Assistant simply reads that index.

---

## Benefits

• Very high scanning speed

• Sequential reading

• Minimal filesystem overhead

• Predictable performance

---

## Tradeoffs

Requires NTFS.

Non-NTFS filesystems require different scanners.

---

# 11. Stage 3 — Raw Entry Processing

The MFT does not immediately produce application-ready data.

Instead it produces low-level metadata.

Example:

```
Raw Entry

↓

Path

↓

Directory Flag

↓

MFT Size

↓

Attributes
```

These entries cannot yet be shown to users.

They must first be transformed.

---

# 12. Stage 4 — Storage Classification

## Problem

Two files may have identical extensions but completely different meanings.

Example:

```
Downloads

movie.mp4
```

vs

```
AppData

cache.mp4
```

Extension alone provides no semantic information.

---

## Solution

Storage Assistant classifies files primarily by location.

Example

```
C:\Users\...

↓

USER_DATA
```

```
AppData

↓

TECHNICAL
```

```
Unknown

↓

OTHER
```

This provides semantic understanding instead of purely syntactic information.

---

# 13. Stage 5 — Accurate Size Resolution

One challenge discovered during development was that certain MFT entries report incorrect file sizes.

Examples included:

- executable files

- archives

- Blender projects

- compressed files

Some files reported:

```
0 Bytes
```

while actually occupying gigabytes.

---

## Solution

Storage Assistant uses a hybrid strategy.

```
MFT Size

↓

Valid?

├── Yes

│

▼

Use Immediately

│

└── No

↓

Filesystem Lookup

↓

Correct Size
```

This preserves MFT speed while maintaining accuracy.

---

# 14. Stage 6 — SQLite Index Creation

At this stage every file has:

- location
- size
- category
- metadata

Now the backend creates its working index.

```
File Objects

↓

SQLite

↓

Files Table
```

The SQLite database now becomes the application's primary data source.

No later subsystem needs direct filesystem access.

---

# 15. Why SQLite Exists

Without SQLite,

opening a folder would require recalculating everything.

Example

```
Dashboard

↓

Folder

↓

Folder

↓

Folder

↓

Recalculate Every File
```

This becomes extremely expensive.

Instead

```
Dashboard

↓

SQLite Query

↓

Result
```

Navigation becomes nearly instantaneous.

---

# 16. Stage 7 — Folder Aggregation

Users think in folders.

Operating systems store files.

These are fundamentally different views.

Example

```
Project

├── Images

├── Videos

└── Docs
```

The filesystem stores individual files.

The user wants

```
Project

↓

42 GB
```

The Folder Analyzer bridges this gap.

---

## Responsibilities

It calculates:

- recursive folder size

- direct folder size

- file count

- parent relationships

Everything is stored back into SQLite.

---

# 17. Stage 8 — Runtime Memory Cleanup

The MFT can temporarily occupy hundreds of megabytes of RAM.

Keeping these objects alive after indexing serves no purpose.

Therefore:

```
Raw MFT

↓

SQLite

↓

Release Objects

↓

Garbage Collection
```

Memory usage drops significantly after indexing completes.

This makes the application practical even on 8 GB systems.

---

# Stage Summary

At this point the backend has transformed raw NTFS metadata into a structured storage database.

The system now knows:

✓ every indexed file

✓ every folder

✓ accurate storage usage

✓ parent relationships

✓ classifications

The expensive filesystem work is now complete.

Everything after this stage operates entirely on indexed data.

This marks the transition from **Data Acquisition** to **Data Understanding**.

The following chapters describe how the backend reasons about this indexed information using deterministic rules and AI-assisted analysis.

# Chapter 3 — Data Understanding Engine

---

# 18. From Data Acquisition to Data Understanding

At the end of the scanning stage, the backend possesses an indexed representation of the entire storage device.

However, indexed data alone is not useful.

Knowing that the system contains:

• 1,042,000 files

• 198,000 folders

• 470 GB of storage

does not answer the questions users actually ask.

Users do not want data.

Users want understanding.

Examples include:

• Why is my storage full?

• Which folders are consuming the most space?

• Can I safely remove these files?

• Which application owns this storage?

• Is Windows using this space or am I?

The responsibility of the Data Understanding Engine is to convert raw indexed storage into meaningful knowledge.

This stage transforms storage information into something humans can reason about.

---

# 19. Why File-Level Analysis Is Impossible

One of the earliest architectural decisions was to avoid analysing individual files whenever possible.

Consider a realistic system.

```
1,200,000 Files
```

Even if every file required only a few bytes of reasoning context, the resulting AI prompt would be enormous.

The problem becomes worse because most files are meaningless in isolation.

Example:

```
cache_193.bin

cache_194.bin

cache_195.bin

cache_196.bin
```

Individually these files provide almost no information.

Collectively they represent:

```
Chrome Cache
```

Humans naturally think in groups.

Therefore the backend must also think in groups.

---

# 20. Folder-Centric Intelligence

Instead of analysing files,

Storage Assistant analyses folders.

Example:

Instead of

```
cache001.tmp

cache002.tmp

cache003.tmp

...
```

the backend reasons as

```
Google

↓

Chrome

↓

Cache

↓

12.8 GB
```

This immediately introduces meaning.

A folder becomes a semantic object rather than merely a directory.

---

# 21. Rule Engine Philosophy

Before Artificial Intelligence becomes involved,

the backend performs deterministic reasoning.

This is intentional.

AI should never be responsible for deciding whether system files are safe.

Those decisions should be deterministic.

The Rule Engine therefore acts as the application's first reasoning layer.

Its responsibilities include:

• understanding ownership

• understanding safety

• understanding protected areas

• identifying cleanup candidates

without requiring AI.

---

# 22. Rule Evaluation Pipeline

Every indexed file passes through the following decision pipeline.

```
Indexed File

↓

Protected Rules

↓

Safe Rules

↓

User Data Rules

↓

Cleanup Classifier
```

Each stage performs a different responsibility.

---

# 23. Protected Rules

The first responsibility of the backend is preventing damage.

The question asked is:

> Should this file ever be recommended for deletion?

If the answer is "No",

the pipeline immediately stops.

```
Incoming File

↓

Protected?

│

├── Yes

│

▼

Stop Processing

│

└── No

↓

Continue
```

This guarantees that higher layers never accidentally recommend dangerous files.

Safety is enforced before intelligence.

---

# 24. Safe Rules

If the file is not protected,

the backend evaluates whether it belongs to a known disposable category.

Examples include:

• browser cache

• temporary files

• crash dumps

• thumbnail cache

• installer leftovers

Unlike Protected Rules,

Safe Rules do not delete anything.

They simply classify storage as low-risk.

---

# 25. User Data Rules

Personal data follows a completely different policy.

Examples include:

```
Desktop

Documents

Downloads

Pictures

Videos
```

The backend intentionally assumes that user-created data has higher value than technical storage.

Therefore recommendations involving personal files require much stronger reasoning.

The application always prefers false negatives over false positives.

Protecting user data is more important than finding one additional cleanup opportunity.

---

# 26. Cleanup Classification

After rule evaluation,

the backend converts technical rule results into standardized Cleanup Items.

This creates a common language shared by every later subsystem.

```
Rule Result

↓

Cleanup Item
```

Each Cleanup Item contains structured information such as:

• category

• confidence

• reason

• size

• action

This allows every later module to operate on identical objects.

---

# 27. Cleanup Aggregation

Thousands of Cleanup Items are not useful.

Instead they are aggregated.

Example

Instead of

```
Google Cache

1 MB

Google Cache

2 MB

Google Cache

3 MB
```

the backend produces

```
Google Cache

↓

6 GB

↓

12,843 Files

↓

Safe Cleanup
```

Aggregation converts low-level information into meaningful summaries.

---

# 28. Why Folder Trees Exist

The filesystem naturally forms a hierarchy.

Ignoring that hierarchy would destroy important context.

Example

```
Users

└── Aashish

└── AppData

└── Local

└── Google

└── Chrome

└── Cache
```

This structure contains significantly more information than six unrelated folders.

Therefore the backend constructs a complete Folder Tree.

Every folder knows:

• parent

• children

• recursive size

• direct size

• file count

This tree becomes the knowledge graph used throughout the AI subsystem.

---

# 29. Boundary Resolution

Analysing an entire drive from its root provides very poor semantic information.

Example

```
C:\
```

contains everything.

Instead,

the backend identifies meaningful boundaries.

Examples include:

```
AppData

ProgramData

Downloads

Documents

Desktop
```

These become the first level of AI reasoning.

Instead of asking:

"Analyse C Drive"

the backend asks

"Analyse Chrome Cache"

which produces dramatically better reasoning.

---

# 30. Candidate Selection

Even meaningful boundaries may still be too numerous.

The backend therefore ranks every candidate.

Primary ranking factors include:

• storage size

• storage impact

• coverage

Large folders naturally explain most storage usage.

Small folders usually contribute little.

The objective is not to maximise folder count.

The objective is to maximise explained storage.

---

# 31. Cluster Building

Selected folders are converted into logical clusters.

Clusters represent coherent storage concepts.

Examples include:

```
Chrome

↓

Cache

↓

GPU Cache

↓

Code Cache
```

instead of four unrelated folders.

This dramatically improves contextual understanding.

---

# 32. Cluster Summarization

Even clusters contain more information than AI requires.

The backend therefore compresses every cluster into a semantic summary.

Instead of transmitting every file,

the AI receives:

• folder purpose

• total storage

• file count

• category

• relationship information

This achieves substantial token reduction while preserving reasoning quality.

---

# 33. Why AI Never Sees Raw Storage

The architecture intentionally prevents AI from analysing the raw filesystem.

Instead AI receives an abstract representation.

```
Filesystem

↓

SQLite

↓

Folder Tree

↓

Clusters

↓

Summaries

↓

AI
```

This separation has several advantages.

• lower token usage

• improved reasoning

• deterministic preprocessing

• provider independence

• reproducible analysis

The LLM is no longer solving filesystem analysis.

It is solving storage reasoning.

These are fundamentally different problems.

---

# Chapter Summary

By the end of this stage, the backend has transformed millions of raw filesystem entries into a structured representation of storage.

The system now understands:

✓ storage ownership

✓ folder hierarchy

✓ cleanup safety

✓ user data

✓ technical storage

✓ storage relationships

✓ high-impact areas

✓ AI-ready summaries

At this point, the backend no longer operates as a file scanner.

It operates as a storage intelligence engine.

The following chapter explains how this structured knowledge is transformed into AI reasoning while maintaining provider independence, response validation, and iterative deep analysis.

# Chapter 4 — AI Reasoning Architecture

---

# 34. Why AI Exists

Artificial Intelligence is one of the most misunderstood components inside the backend.

Many storage applications integrate AI as the primary decision maker.

Storage Assistant intentionally does not.

Instead, AI acts as the final reasoning layer.

The backend already understands storage before AI becomes involved.

AI is responsible for answering questions such as:

• Why is this folder large?

• What application generated these files?

• Which cleanup order makes the most sense?

• How should these recommendations be explained to the user?

Notice something important.

AI never determines whether a file is safe.

That decision has already been made by deterministic modules.

AI explains.

It does not decide.

---

# 35. Separation of Intelligence

The backend intentionally separates two very different forms of intelligence.

## Deterministic Intelligence

Responsible for facts.

Examples:

• file size

• folder ownership

• cleanup safety

• protected directories

• folder hierarchy

Facts never change.

---

## AI Intelligence

Responsible for reasoning.

Examples:

• prioritisation

• explanation

• grouping

• human-readable recommendations

AI reasons only after deterministic facts have already been established.

This dramatically reduces hallucination.

---

# 36. Why AI Never Talks To The Filesystem

One of the most important architectural decisions is complete isolation between AI and the operating system.

The AI subsystem has absolutely no access to:

• files

• folders

• Windows

• NTFS

• SQLite

Instead AI receives a structured snapshot.

```
Filesystem

↓

SQLite

↓

Folder Tree

↓

Clusters

↓

Summaries

↓

Payload

↓

Prompt

↓

LLM
```

The model never interacts with the filesystem.

Only structured information.

---

# 37. The AI Pipeline

The complete AI execution pipeline is shown below.

```
Folder Tree

↓

Boundary Resolver

↓

Candidate Selection

↓

Cluster Builder

↓

Cluster Summarizer

↓

Payload Builder

↓

Prompt Builder

↓

Analysis Engine

↓

Provider Manager

↓

Provider Factory

↓

Provider

↓

Response Schema

↓

Iterative Analyzer

↓

Final Recommendation
```

Every module exists to reduce uncertainty before the LLM begins reasoning.

---

# 38. Boundary Resolution

The first AI-specific stage determines where reasoning should begin.

A storage drive is far too large to analyse directly.

Instead the backend identifies meaningful boundaries.

Example

Instead of

```
Analyse C:
```

the backend produces

```
Analyse

Downloads

Chrome Cache

ProgramData

Android Studio

Steam
```

The LLM immediately receives far more meaningful context.

---

# 39. Candidate Selection

Even meaningful boundaries may still exceed the model's context window.

Candidate Selection therefore answers one question.

"What is worth spending tokens on?"

Priority is determined primarily by storage impact.

Large folders naturally receive higher priority because they explain more of the occupied storage.

The objective is maximizing explained storage per token.

---

# 40. Cluster Builder

Folders alone are still insufficient.

Related folders are merged into logical storage clusters.

Example

```
Chrome

↓

Cache

↓

GPU Cache

↓

Code Cache
```

becomes

```
Google Chrome Storage
```

This transforms filesystem hierarchy into application-level concepts.

---

# 41. Cluster Summarization

Large clusters still contain too much information.

The summarizer extracts only high-value attributes.

Examples include:

• folder purpose

• recursive size

• file count

• ownership

• category

Everything else is intentionally discarded.

Information density increases dramatically.

---

# 42. Payload Builder

The summarizer produces internal Python objects.

Language models cannot consume these objects.

Payload Builder converts every internal object into a provider-independent representation.

Responsibilities include:

• serialization

• normalization

• validation

• metadata preservation

The output is no longer Python.

It is structured data.

---

# 43. Why Payload Builder Exists

Without Payload Builder,

every provider would need to understand internal application objects.

Example

```
Gemini

↓

FolderNode
```

```
Groq

↓

FolderNode
```

```
OpenRouter

↓

FolderNode
```

Every provider would duplicate serialization logic.

Instead

```
FolderNode

↓

Payload Builder

↓

Universal Payload

↓

Any Provider
```

Serialization now exists only once.

---

# 44. Prompt Builder

Payload and Prompt are intentionally separated.

Payload contains facts.

Prompt contains instructions.

Example

Payload

```
Downloads

42 GB

12,000 files
```

Prompt

```
Explain why this folder is large.

Suggest cleanup priorities.

Avoid recommending protected storage.

Return JSON only.
```

Keeping them separate allows prompt engineering without touching business logic.

---

# 45. Analysis Engine

The Analysis Engine executes the AI request.

Its responsibilities include:

• preparing inference

• executing provider requests

• collecting metadata

• handling provider failures

• returning standardized responses

It contains no provider-specific logic.

---

# 46. Provider Abstraction

Every provider implements the same interface.

```
Provider

├── Gemini

├── Groq

├── OpenRouter

└── Future Providers
```

The rest of the application never knows which provider is active.

This is an implementation of the Dependency Inversion Principle.

---

# 47. Provider Factory

Provider creation is centralized.

Instead of

```
if Gemini

...

if Groq

...

if OpenRouter
```

throughout the codebase,

construction occurs in one location.

Benefits include:

• cleaner architecture

• easier maintenance

• easier provider expansion

---

# 48. Provider Manager

The Provider Manager selects which implementation should execute the request.

Future versions may use:

• latency

• cost

• context length

• provider health

to automatically select the optimal provider.

The rest of the backend remains unchanged.

---

# 49. Response Schema

Language models are probabilistic.

Applications require deterministic structures.

Response Schema converts probability into predictability.

Every AI response is validated before entering the application.

Invalid responses never reach higher layers.

Example

```
LLM

↓

JSON Validation

↓

Schema Validation

↓

Application
```

This protects the backend from malformed AI output.

---

# 50. Iterative Analysis

One AI request is rarely sufficient.

Large storage systems contain multiple independent regions.

Instead of requesting one enormous analysis,

Storage Assistant performs iterative reasoning.

```
Large Folder

↓

AI

↓

Interesting?

│

├── No

│

▼

Stop

│

└── Yes

↓

Expand Children

↓

Repeat
```

The backend gradually explores storage.

This resembles graph exploration rather than brute-force analysis.

---

# 51. Why Iterative Analysis Exists

Suppose:

```
Users

250 GB
```

One request would waste context.

Instead

```
Users

↓

Documents

↓

Projects

↓

Unity

↓

Build Cache
```

Each iteration increases precision.

Tokens are spent only where useful.

---

# 52. AI Safety

Artificial Intelligence never performs destructive actions.

It cannot:

• delete

• move

• rename

• modify

files.

Its responsibilities end after generating recommendations.

The user always remains the final decision maker.

---

# 53. Failure Recovery

The backend assumes AI providers can fail.

Failures include:

• timeout

• invalid JSON

• malformed responses

• quota exceeded

• unavailable provider

The architecture isolates these failures.

The Storage Assistant remains functional even if every provider becomes unavailable.

Only AI explanations are lost.

Core functionality continues.

---

# 54. AI Architecture Summary

The AI subsystem does not replace traditional software engineering.

Instead it extends it.

The deterministic backend first converts the filesystem into structured knowledge.

Only then is AI allowed to reason about that knowledge.

This architecture provides:

✓ lower token usage

✓ lower hallucination

✓ provider independence

✓ deterministic preprocessing

✓ reusable pipeline

✓ scalable reasoning

The AI subsystem therefore behaves as a reasoning engine built on top of an already intelligent storage engine rather than replacing it.

# Chapter 5 — Backend Infrastructure, Performance & Scalability

---

# 55. Engineering Philosophy

Most storage applications are designed around one objective.

```
Read Files

↓

Show Files
```

Storage Assistant follows a completely different philosophy.

```
Read Once

↓

Understand Once

↓

Store Once

↓

Reuse Forever
```

This single architectural decision affects every subsystem.

The filesystem is treated as an expensive external resource.

SQLite becomes the internal representation.

Everything else operates entirely on indexed data.

This minimizes disk I/O and allows the application to scale to very large storage devices.

---

# 56. Why Filesystem Access Is Expensive

Modern SSDs are extremely fast.

However,

filesystem traversal is still expensive because every directory traversal requires operating system interaction.

Example

```
Root

↓

Directory

↓

Subdirectory

↓

File
```

Each level requires another filesystem request.

Multiply this by:

```
1,000,000 files
```

and performance rapidly decreases.

The operating system already solved this problem.

It stores filesystem metadata inside the Master File Table.

Storage Assistant simply reuses that index.

---

# 57. SQLite As The Source Of Truth

The biggest architectural decision inside the backend is choosing SQLite as the application's primary storage layer.

The filesystem is **not** the source of truth after scanning.

SQLite is.

```
Filesystem

↓

MFT

↓

SQLite

↓

Everything Else
```

Every subsystem receives exactly the same information.

Benefits include:

• consistent data

• instant querying

• reusable indexes

• no repeated disk scanning

• faster navigation

---

# 58. Why SQLite Instead Of RAM

Suppose the application kept everything only in memory.

```
Scan

↓

RAM
```

Opening another page would require keeping hundreds of megabytes alive.

Restarting the application would lose everything.

Instead

```
Scan

↓

SQLite

↓

Release RAM
```

The indexed data becomes persistent throughout the session.

Memory usage decreases dramatically.

---

# 59. Memory Lifecycle

One of the largest engineering challenges is memory management.

During development, benchmarking revealed that reading the complete MFT could temporarily require several hundred megabytes of memory.

Typical execution:

```
Application Starts

↓

~15 MB

↓

Read MFT

↓

~700 MB

↓

SQLite Index

↓

Release Objects

↓

~110 MB
```

The application intentionally treats RAM as temporary working space.

Large structures are discarded immediately after indexing.

---

# 60. Object Lifecycle

The backend is essentially a series of object transformations.

```
Raw MFT Entry

↓

Indexed File

↓

SQLite Row

↓

FolderNode

↓

Cleanup Item

↓

Cleanup Group

↓

Cluster

↓

Cluster Summary

↓

Payload

↓

Prompt

↓

Provider Response

↓

Analysis Result
```

Every object exists for only one stage.

Once that stage completes,

the previous representation is no longer needed.

This minimizes memory retention.

---

# 61. Why Objects Are Transformed

It may appear inefficient to repeatedly convert objects.

In reality,

each representation exists for a different purpose.

Example:

Raw MFT Entry

↓

Filesystem Metadata

FolderNode

↓

Hierarchy

Cleanup Item

↓

Rule Evaluation

Cluster

↓

AI Context

Prompt

↓

Language Model Communication

Each representation removes unnecessary information.

Complexity decreases at every stage.

---

# 62. Data Reduction Strategy

One of the backend's hidden optimizations is progressive data reduction.

```
1,000,000 Files

↓

400,000 Useful Files

↓

20,000 Folders

↓

120 Candidate Folders

↓

20 Clusters

↓

10 Summaries

↓

1 Prompt
```

Notice that every stage dramatically reduces complexity.

Instead of AI analysing one million files,

it analyses approximately ten meaningful summaries.

This is the primary reason token usage remains practical.

---

# 63. Dependency Graph

The backend intentionally follows a layered dependency graph.

```
main.py

│

├── Scanner

├── Database

├── Folder Analyzer

├── Rule Engine

├── Cleanup Pipeline

├── AI Pipeline

└── Dashboard
```

Lower layers never depend on higher layers.

For example,

the MFT Scanner has absolutely no knowledge of:

• AI

• UI

• Dashboard

• SQLite queries

It performs only scanning.

---

# 64. Module Independence

Every backend module has one clearly defined responsibility.

Examples

```
MFT Scanner

↓

Read Metadata
```

```
Folder Analyzer

↓

Aggregate Storage
```

```
Rule Engine

↓

Evaluate Rules
```

```
Cluster Builder

↓

Create Hierarchy
```

```
Prompt Builder

↓

Communicate With AI
```

No module attempts to perform multiple unrelated tasks.

This follows the Single Responsibility Principle.

---

# 65. Threading Strategy

The backend is designed so that expensive operations never block the user interface.

Long-running tasks such as:

• MFT scanning

• Folder aggregation

• AI analysis

execute independently from the presentation layer.

```
UI Thread

│

├── Render Dashboard

├── Receive Input

└── Update Progress

Background Thread

↓

Scanning

↓

Database

↓

Analysis

↓

Completion
```

The user interface remains responsive throughout the scan.

---

# 66. Performance Optimizations

Several optimizations work together.

## Sequential MFT Reading

Avoids recursive traversal.

---

## Hybrid Size Resolution

Trust MFT whenever possible.

Fallback only when required.

---

## SQLite Indexing

Expensive computation occurs once.

---

## Folder Aggregation

Recursive folder sizes are precomputed.

---

## Candidate Selection

Only meaningful folders reach AI.

---

## Cluster Summarization

Only meaningful summaries reach the prompt.

Every optimization removes unnecessary work.

---

# 67. Time Complexity

Approximate computational complexity.

```
MFT Reading

O(n)
```

```
Classification

O(n)
```

```
SQLite Insert

O(n)
```

```
Folder Aggregation

O(n × depth)
```

Since Windows folder depth is relatively small,

the practical complexity approaches O(n).

Candidate Selection

```
O(k log k)
```

where

```
k << n
```

AI Complexity

Independent from filesystem size.

Instead it depends on selected cluster count.

This is a critical architectural advantage.

---

# 68. Scalability

The backend is intentionally designed around scalability.

Increasing storage size does **not** proportionally increase AI workload.

Example

```
100 GB

↓

18 AI summaries
```

```
1 TB

↓

26 AI summaries
```

Storage increases significantly.

AI workload increases only slightly.

This is possible because summarization occurs before reasoning.

---

# 69. Fault Isolation

Failures remain isolated.

Example

Provider Failure

↓

AI Disabled

↓

Storage Scanner Continues

Example

SQLite Error

↓

Scanner Stops

↓

UI Still Responsive

Example

Prompt Error

↓

Retry

↓

No Files Lost

Subsystems fail independently.

This dramatically improves reliability.

---

# 70. Engineering Tradeoffs

Every architectural decision introduces tradeoffs.

Example

SQLite

Pros

• fast queries

• reusable index

Cons

• temporary storage overhead

---

MFT

Pros

• extremely fast

Cons

• NTFS only

---

Iterative AI

Pros

• lower token cost

Cons

• multiple requests

---

Abstraction

Pros

• maintainability

Cons

• more modules

The backend intentionally accepts additional architectural complexity in exchange for long-term scalability and maintainability.

---

# Chapter Summary

The backend is engineered around one central idea:

> Expensive work should happen exactly once.

The filesystem is scanned once.

The storage hierarchy is built once.

Folder sizes are calculated once.

Rules are evaluated once.

SQLite stores the results.

Every later subsystem—including AI, Dashboard, Search, Reports, and future modules—operates entirely on indexed, structured information rather than repeatedly interacting with the filesystem.

This architecture minimizes disk I/O, reduces memory pressure, enables provider-independent AI reasoning, and creates a scalable foundation capable of supporting future versions of Storage Assistant without fundamental architectural changes.

# Chapter 6 — Design Decisions & Engineering Rationale

---

# 71. Why Use The Master File Table Instead Of Recursive Filesystem Traversal?

## Problem

The most obvious way to analyse storage is recursively traversing every directory using APIs such as:

- os.walk()
- scandir()
- recursive directory iteration

This approach is simple to implement.

However, it becomes increasingly inefficient as the number of files grows.

A modern Windows installation can easily contain:

• 800,000 files

• 2,000,000+ filesystem objects

Recursive traversal requires the operating system to repeatedly resolve directory entries and metadata.

This results in:

- excessive filesystem calls
- unpredictable execution time
- repeated disk I/O

---

## Engineering Decision

Instead of traversing the filesystem,

Storage Assistant directly reads the NTFS Master File Table.

```
NTFS

↓

Master File Table

↓

Metadata
```

The operating system has already indexed every file.

Reading that index is significantly faster than rebuilding the index manually.

---

## Why This Matters

The backend is no longer discovering files.

Windows has already done that work.

The backend simply consumes the operating system's existing metadata.

---

## Tradeoffs

Advantages

✓ Extremely fast

✓ Sequential reading

✓ Lower I/O

✓ Predictable performance

Disadvantages

✗ NTFS specific

---

# 72. Why SQLite Instead Of Keeping Everything In RAM?

## Problem

The application temporarily processes hundreds of thousands of files.

Keeping every object alive during the application's lifetime would dramatically increase memory consumption.

Large scans would easily require hundreds of megabytes.

---

## Engineering Decision

SQLite becomes the application's persistent working memory.

```
Filesystem

↓

SQLite

↓

Application
```

RAM is treated as temporary processing space.

---

## Why This Matters

Every subsystem receives exactly the same indexed representation.

Instead of

```
Filesystem

↓

Scanner

↓

Dashboard
```

and

```
Filesystem

↓

AI
```

everything becomes

```
Filesystem

↓

SQLite

↓

Everything
```

---

## Benefits

✓ Reduced RAM usage

✓ Faster queries

✓ Shared storage

✓ Reusable index

✓ Consistent state

---

# 73. Why Folder Trees Instead Of Flat File Lists?

Humans do not naturally reason about files.

They reason about projects.

Applications.

Games.

Downloads.

Folders.

Suppose a drive contains

```
70,000 files
```

This number is meaningless.

Instead

```
Downloads

↓

42 GB
```

Immediately communicates useful information.

---

## Engineering Decision

The backend converts individual files into FolderNodes.

Each node stores:

• parent

• children

• recursive size

• direct size

• file count

Folders become semantic objects.

---

# 74. Why Rules Execute Before AI?

This is arguably the most important architectural decision.

Many AI-powered applications ask the language model:

"Should this file be deleted?"

Storage Assistant intentionally avoids this.

Instead

```
Filesystem

↓

Rules

↓

AI
```

not

```
Filesystem

↓

AI

↓

Rules
```

---

## Reason

Safety should never depend on probabilistic reasoning.

Whether

```
System32
```

is protected

should not depend on an LLM.

It should depend on deterministic software.

---

## Principle

Facts first.

Reasoning later.

---

# 75. Why AI Never Reads The Filesystem

The AI subsystem has no knowledge of Windows.

No knowledge of NTFS.

No knowledge of SQLite.

Instead it receives:

```
Storage Summary
```

This separation provides three major benefits.

### Lower Token Usage

Only important information is transmitted.

---

### Better Reasoning

AI reasons about concepts.

Not implementation details.

---

### Provider Independence

Changing providers does not affect filesystem code.

---

# 76. Why Cluster Builder Exists

Suppose the backend directly sent folders.

```
Chrome Cache

GPU Cache

Code Cache

Media Cache
```

The AI would see four unrelated folders.

Instead

Cluster Builder creates

```
Google Chrome

↓

Cache

↓

16 GB
```

The model now understands an application,

not isolated folders.

Cluster Builder therefore creates semantic context.

---

# 77. Why Candidate Selection Exists

Language models have finite context windows.

Analysing every folder is impossible.

The backend therefore asks:

"What explains the largest amount of storage?"

Instead of

```
10,000 folders
```

AI receives

```
25 important folders
```

This dramatically reduces token consumption.

---

# 78. Why Prompt Builder Is Separate

Prompt engineering changes frequently.

Business logic should not.

Therefore

```
Payload

↓

Prompt
```

are independent.

Changing prompt wording never changes backend logic.

---

# 79. Why Provider Abstraction Exists

Without abstraction,

every module would require code like:

```
if Gemini

...

if Groq

...

if OpenRouter
```

This creates tight coupling.

Instead

```
Application

↓

Provider Interface

↓

Concrete Provider
```

Every module communicates with the interface.

Never the implementation.

---

# 80. Why Response Validation Exists

Language models occasionally produce malformed responses.

Example

Expected

```
JSON
```

Received

```
Markdown
```

Without validation,

this would immediately break the application.

Instead

```
LLM

↓

Schema Validation

↓

Application
```

The backend trusts validated responses.

Never raw responses.

---

# 81. Why Iterative Analysis Exists

Large storage systems cannot be understood in one request.

Suppose

```
Users

↓

250 GB
```

One prompt would waste context.

Instead

```
Users

↓

Projects

↓

Unity

↓

Library

↓

Build Cache
```

Each iteration explores deeper only where necessary.

This resembles graph search more than brute-force AI prompting.

---

# 82. Why Memory Is Explicitly Managed

Large MFT scans may temporarily require hundreds of megabytes.

Keeping these objects alive provides no benefit after indexing.

Therefore

```
MFT

↓

SQLite

↓

Release

↓

Garbage Collection
```

Memory becomes available almost immediately.

---

# 83. Why The Backend Is Layered

Every layer exists to isolate responsibilities.

```
Presentation

↓

Application

↓

Core

↓

Rules

↓

Analysis

↓

AI

↓

Persistence

↓

Infrastructure
```

Changing one layer should rarely require changes elsewhere.

This reduces coupling.

Improves maintainability.

Supports future expansion.

---

# 84. Architectural Tradeoffs

Every engineering decision introduces compromises.

The backend intentionally accepts these tradeoffs because the long-term benefits outweigh the short-term complexity.

| Decision | Benefit | Tradeoff |
|-----------|---------|----------|
| MFT | Extremely fast scanning | NTFS-specific |
| SQLite | Reusable indexed data | Temporary database maintenance |
| Rule Engine | Deterministic safety | More implementation complexity |
| AI Pipeline | Better reasoning | More architectural layers |
| Provider Abstraction | Easy provider replacement | Additional interfaces |
| Iterative Analysis | Lower token usage | Multiple AI requests |
| Folder Tree | Semantic understanding | Additional aggregation step |

---

# 85. Core Engineering Principles

Every future backend change should preserve these principles.

### Principle 1

Touch the filesystem exactly once.

---

### Principle 2

Everything after scanning operates on indexed data.

---

### Principle 3

Deterministic reasoning always precedes AI reasoning.

---

### Principle 4

AI explains.

Software decides.

---

### Principle 5

Every module owns exactly one responsibility.

---

### Principle 6

Every expensive computation should be reusable.

---

### Principle 7

Lower layers must never depend on higher layers.

---

### Principle 8

Safety always has higher priority than convenience.

---

### Principle 9

Storage understanding is more valuable than storage cleaning.

---

### Principle 10

The architecture should allow future capabilities to be added without redesigning existing modules.

---

# Chapter Summary

The backend architecture is intentionally designed around deterministic software engineering principles rather than AI-first design.

Every major architectural decision—from MFT scanning to SQLite indexing, rule evaluation, folder aggregation, provider abstraction, and iterative AI reasoning—exists to reduce complexity, improve scalability, increase reliability, and preserve user safety.

Rather than relying on AI to compensate for weak engineering, Storage Assistant first constructs a deterministic understanding of the storage system and only then applies AI as a reasoning layer. This separation ensures that intelligence enhances the product without becoming a dependency for its core functionality.

# Chapter 7 — Future Evolution, Architecture Constitution & Engineering Guidelines

---

# 86. Current Architecture Assessment

At the time of writing, the backend architecture successfully achieves its original objectives.

The system is capable of:

✓ Fast NTFS scanning

✓ Deterministic cleanup analysis

✓ Folder hierarchy generation

✓ SQLite-based indexing

✓ AI-assisted reasoning

✓ Provider independence

✓ Modular backend architecture

✓ Memory-aware processing

The architecture is intentionally layered, making future extensions significantly easier than modifying a monolithic implementation.

However, no architecture is ever complete.

Every architecture should be considered an evolving system rather than a finished design.

---

# 87. Current Architectural Limitations

Every engineering decision introduces limitations.

Understanding them early prevents future technical debt.

## Limitation 1

NTFS Dependency

The current scanning engine relies on the NTFS Master File Table.

Benefits:

• Extremely fast

Drawback:

• Windows specific

Future versions should introduce pluggable filesystem scanners.

---

## Limitation 2

Full Scan Requirement

The current architecture assumes that every scan begins from scratch.

Benefits:

Simple implementation.

Drawback:

Repeated scanning of unchanged files.

Future versions should support incremental indexing.

---

## Limitation 3

Single Snapshot Model

The current database represents one point in time.

The backend cannot currently answer questions such as:

"What changed since yesterday?"

Future versions should support historical snapshots.

---

## Limitation 4

Single Machine Scope

Current analysis is limited to one storage device.

Future versions should support:

• Multiple drives

• External storage

• Network drives

• Cloud storage

---

## Limitation 5

Manual Rule Expansion

Adding new cleanup knowledge currently requires new rules.

Future versions should allow dynamic rule packs.

---

# 88. Backend Evolution Roadmap

The architecture intentionally separates immediate functionality from future capabilities.

## Version 2

Primary goals

• Incremental scanning

• Duplicate detection

• Better cleanup categories

• Smarter cache identification

• Improved AI reasoning

No architectural redesign required.

---

## Version 3

Primary goals

• Storage history

• Timeline analysis

• Space growth prediction

• Snapshot comparison

Again,

existing architecture remains unchanged.

Only additional modules are introduced.

---

## Version 4

Potential capabilities

• Local LLMs

• Plugin ecosystem

• Team storage analysis

• Enterprise scanning

• Distributed indexing

The backend was intentionally designed so these capabilities can be added without rewriting the Core Engine.

---

# 89. Future Plugin Architecture

The backend should eventually evolve toward a plugin-based architecture.

Example

```
Storage Assistant

│

├── Scanner Plugins

├── Rule Plugins

├── AI Providers

├── Export Plugins

├── Visualization Plugins

└── Cleanup Strategies
```

This allows future features to be developed independently.

The Core Engine remains unchanged.

---

# 90. Incremental Scanning

One of the highest-impact future improvements.

Current architecture

```
Filesystem

↓

Full Scan
```

Future architecture

```
Filesystem

↓

Changed Files

↓

SQLite Update
```

Only modified files require processing.

This dramatically reduces scan time.

---

# 91. Local AI Support

The Provider architecture intentionally supports future local models.

Possible providers

```
Gemini

Groq

OpenRouter

Ollama

vLLM

LM Studio

GGUF Runtime
```

No Core Engine changes should be required.

Only new Provider implementations.

---

# 92. Storage Timeline

Future versions should allow users to answer questions such as:

• Which folder grew the fastest?

• What occupied storage this week?

• Which application continuously consumes space?

This requires historical snapshots rather than only the latest scan.

---

# 93. Predictive Analysis

The current backend explains storage.

Future versions may predict storage.

Examples

```
Current Trend

↓

Prediction

↓

Disk Full In

12 Days
```

Prediction modules should remain independent from cleanup modules.

---

# 94. Architecture Principles For Contributors

Every contributor should follow the same engineering principles.

## Rule 1

Never bypass SQLite.

Filesystem access belongs only inside scanning modules.

---

## Rule 2

Never allow AI to replace deterministic logic.

Facts belong to software.

Reasoning belongs to AI.

---

## Rule 3

Never place business logic inside the UI.

The UI should display information.

Never generate it.

---

## Rule 4

Every module should own one responsibility.

Avoid "God Classes".

---

## Rule 5

Never duplicate filesystem analysis.

Reuse indexed data.

---

## Rule 6

Every expensive computation should become reusable.

---

## Rule 7

Every provider must implement the common Provider interface.

---

## Rule 8

Never couple business logic with a specific AI provider.

---

## Rule 9

Optimize before adding AI.

Better software engineering always beats larger prompts.

---

## Rule 10

The user should always remain in control.

AI may recommend.

Only the user may decide.

---

# 95. Testing Philosophy

Future development should preserve deterministic behaviour.

Every module should be testable independently.

Examples

Scanner

↓

Mock filesystem

Rule Engine

↓

Synthetic files

AI Pipeline

↓

Mock Provider

SQLite

↓

Temporary database

Testing should never require internet connectivity.

---

# 96. Performance Philosophy

The backend should always optimize work in the following order.

1.

Reduce filesystem operations.

2.

Reduce memory allocations.

3.

Reduce database writes.

4.

Reduce AI requests.

5.

Reduce prompt size.

AI optimization should always be the final optimization stage rather than the first.

---

# 97. Security Philosophy

The backend follows a defense-in-depth approach.

Filesystem

↓

Protected Rules

↓

Safe Rules

↓

User Data Rules

↓

AI

↓

User Confirmation

Multiple independent layers protect against accidental recommendations.

No single component should be capable of causing destructive behaviour.

---

# 98. Long-Term Vision

The goal of Storage Assistant is not to become another storage cleaner.

The long-term objective is to become a Storage Intelligence Platform.

A platform capable of understanding storage rather than merely displaying it.

Potential future capabilities include:

• Storage analytics

• Organization detection

• AI-assisted explanations

• Predictive storage growth

• Historical insights

• Multi-device indexing

• Developer diagnostics

• Enterprise storage reporting

Cleaning is only one possible application of storage understanding.

Understanding storage is the actual product.

---

# 99. Architecture Constitution

The following principles define the architecture of Storage Assistant.

These principles should remain true regardless of future versions.

1.

Touch the filesystem exactly once.

2.

Everything after scanning operates on indexed data.

3.

SQLite is the source of truth.

4.

Business logic is deterministic.

5.

AI enhances understanding rather than replacing software engineering.

6.

Every module owns exactly one responsibility.

7.

Every expensive operation should happen once.

8.

Modules communicate through well-defined interfaces.

9.

Higher layers never leak into lower layers.

10.

Safety has higher priority than convenience.

11.

Scalability is preferred over short-term simplicity.

12.

Provider implementations are replaceable.

13.

Memory is temporary.

SQLite is persistent.

14.

The user always has the final decision.

15.

The architecture should evolve by extension rather than modification.

New capabilities should be added through new modules whenever possible instead of rewriting existing ones.

---

# 100. Closing Statement

Storage Assistant was never designed to be a traditional storage cleaner.

It was designed to become a storage understanding engine.

The architecture intentionally separates acquisition, classification, reasoning, persistence, and presentation into independent layers.

This separation allows the backend to remain maintainable, testable, scalable, and provider-independent while enabling future capabilities to be added without fundamental redesign.

The long-term success of the project does not depend on any individual AI model, database, or implementation detail.

It depends on preserving the architectural principles defined throughout this document.

As long as those principles remain intact, the backend can continue evolving through future versions while maintaining clarity, reliability, and scalability.