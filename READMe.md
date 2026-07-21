# MFT Scanner
--backend/core/mft_scanner.py
## Purpose

This module is responsible for reading the NTFS Master File Table (MFT) from a drive.

It acts as the entry point of the storage scanning pipeline. Instead of recursively walking the filesystem (which is much slower), it retrieves file metadata directly from the MFT for extremely fast scanning.

## Responsibilities

- Read active NTFS entries.
- Measure scan duration.
- Return raw MFT records without modifying them.

This module intentionally performs **no filtering, classification, or analysis**.

## Inputs

- Drive letter (Example: `C:`)

## Outputs

Returns:

- MFT entries
- Scan duration (seconds)

## Workflow

Drive Letter
      │
      ▼
scan_mft()
      │
      ▼
mftparser.ScanVolume(...)
      │
      ▼
Raw MFT Entries
      │
      ▼
Caller

## Dependencies

Uses

- time
- mftparser

Used By

- main.py
- Any future indexing pipeline

## Design Philosophy

Single Responsibility Principle.

This module only reads metadata.

Everything else (classification, filtering, indexing, AI analysis, folder aggregation) belongs to higher layers.

## Performance Notes

Reading directly from the MFT is significantly faster than recursively traversing the filesystem.

This makes large drives (millions of files) scannable within only a few seconds.

## Future Improvements

- Progress callback support
- Scan cancellation
- Multi-drive support
- Scan statistics
- Error handling for unsupported filesystems (FAT/exFAT)

# Storage Scope Classifier

--backend/core/storage_scope.py

## Purpose

This module classifies every file into a logical storage category.

Instead of relying on file extensions, it classifies files according to **where they are stored**.

This allows the application to distinguish between:

- User-owned data
- Technical/System storage
- Everything else

## Categories

### USER_DATA

Files stored inside user folders such as:

- Desktop
- Documents
- Downloads
- Pictures
- Videos
- Music

These are considered personal files.

---

### TECHNICAL

Technical locations including:

- AppData
- ProgramData
- Windows Temp
- Recycle Bin

These folders mainly contain caches, temporary files, application data, and operating system storage.

---

### OTHER

Anything that does not belong to either category.

Examples:

- Custom drives
- Development folders
- Game folders
- Unknown locations

## Responsibilities

- Detect user profile.
- Build known storage locations.
- Normalize paths.
- Compare paths safely.
- Return storage category.

## Inputs

- Absolute file path

## Outputs

Returns one of:

- USER_DATA
- TECHNICAL
- OTHER

## Workflow

Absolute Path
      │
      ▼
Normalize Path
      │
      ▼
Check User Folders
      │
      ├── Yes → USER_DATA
      │
      ▼
Check Technical Folders
      │
      ├── Yes → TECHNICAL
      │
      ▼
OTHER

## Dependencies

Uses

- os
- Enum

Used By

- Folder Analyzer
- Cleanup Classifier
- AI Pipeline
- Future rule engine

## Design Decisions

Classification is based on storage location instead of file extension.

This is far more reliable because:

- `.jpg` inside Downloads is personal.
- `.jpg` inside AppData is usually application cache.

Location provides better semantic meaning than extension.

## Limitations

Current implementation uses predefined folders.

It does not yet recognise:

- Steam libraries
- OneDrive
- Dropbox
- Google Drive
- User-created media folders

## Future Improvements

- Configurable folders
- Multiple Windows users
- Linux/macOS support
- User-defined storage categories

# Size Resolver

-- backend/core/size_resolver.py

## Purpose

This module resolves the actual size of a file while keeping scanning extremely fast.

It trusts the MFT whenever possible and falls back to the filesystem only when necessary.

## Problem It Solves

Some MFT records report a file size of 0 bytes even though the real file contains data.

Examples include:

- Certain executables
- Blend files
- Archives
- Locked files

Without correction, folder sizes become inaccurate.

## Strategy

Primary

Use MFT size.

Fallback

If MFT reports zero bytes:

- Query the filesystem.
- Replace zero size with actual size.

## Responsibilities

- Trust valid MFT sizes.
- Repair incorrect zero-byte entries.
- Track statistics.
- Handle inaccessible files safely.

## Inputs

- Full file path
- MFT-reported size

## Outputs

- Correct file size

## Workflow

Receive File
      │
      ▼
Is MFT Size > 0 ?
      │
 ┌────┴────┐
 │         │
Yes        No
 │         │
 ▼         ▼
Return   os.path.getsize()
 │         │
 └────┬────┘
      ▼
Return Final Size

## Statistics

Tracks:

- MFT size usage
- Fallback attempts
- Successfully repaired files
- Actual empty files
- Failed lookups

These metrics help benchmark scanning performance.

## Dependencies

Uses

- os

Used By

- Folder Analyzer
- Size aggregation pipeline

## Design Philosophy

Filesystem metadata calls are expensive.

Therefore:

- Use the MFT whenever possible.
- Touch the filesystem only when absolutely necessary.

This hybrid approach provides both speed and accuracy.

## Future Improvements

- Parallel fallback resolution
- Caching
- Junction awareness
- Symbolic link handling
- Optional checksum verification

# folder_analyzer.py

-- folder_analyzer.py --

## Purpose

This module converts **file-level information** into **folder-level statistics**.

The SQLite `files` table stores one row per file, but the UI needs folder-level information such as:

- Folder Size
- Total Files
- Parent Folder
- Direct Files
- Recursive Size

This module builds that folder index.

---

## Responsibilities

- Read every indexed file.
- Group files by their parent folder.
- Calculate direct folder statistics.
- Propagate those values upward to every parent folder.
- Store the final folder index inside SQLite.

---

## Inputs

SQLite connection containing the `files` table.

Expected columns:

- path
- size

---

## Outputs

Populates the `folders` table with:

- path
- parent_path
- direct_size
- total_size
- direct_file_count
- total_file_count

Returns:

- Total discovered folders
- Execution time

---

## Workflow

SQLite (files)
        │
        ▼
Read every file
        │
        ▼
Group by parent folder
        │
        ▼
Calculate direct statistics
        │
        ▼
Walk upward through parent hierarchy
        │
        ▼
Aggregate recursive totals
        │
        ▼
Insert into folders table

---

## Important Design Decision

The module performs aggregation **once**.

The UI never recalculates folder sizes.

Instead it simply queries SQLite.

This keeps navigation extremely fast even on millions of files.

---

## Dependencies

Uses

- os
- time
- collections.defaultdict

Used By

- Scan pipeline
- Dashboard
- Folder explorer
- AI analysis

---

## Performance Notes

Complexity is approximately:

O(number_of_files × average_folder_depth)

Since folder depth is usually small on Windows, this scales well.

---

## Future Improvements

- Incremental updates
- Parallel aggregation
- Folder caching
- Ignore junction loops
- Progress callback

---

## Notes

This file is the bridge between **file indexing** and **folder browsing**.

Without it, every folder open would require recalculating thousands of files.

# rule_engine.py

## Purpose

This module is the deterministic decision engine for technical storage.

It decides whether a file should be considered for cleanup based on predefined rules.

Unlike AI, its behaviour is fully predictable.

---

## Responsibilities

- Load cleanup rules.
- Classify storage scope.
- Apply deterministic rules.
- Return structured cleanup decisions.

---

## Inputs

- File path
- File size

---

## Outputs

Returns:

```python
{
    "scope": "...",
    "rule_result": ...
}
```

---

## Workflow

Incoming File
        │
        ▼
StorageScopeClassifier
        │
        ├── USER_DATA
        │       │
        │       ▼
        │   Skip Rules
        │
        ├── TECHNICAL
        │       │
        │       ▼
        │   Execute Rulebook
        │
        └── OTHER
                │
                ▼
             Ignore

---

## Dependencies

Uses

- StorageScopeClassifier
- Rule definitions

Used By

- Cleanup pipeline
- Future recommendation engine

---

## Design Philosophy

Rules are intentionally executed **only** on technical storage.

Personal files are never automatically judged by deterministic cleanup rules.

This separation greatly reduces the chance of accidental deletion recommendations.

---

## Important Design Decision

The Rule Engine never decides *what the user should delete*.

It only determines whether a technical file matches known cleanup patterns.

Higher layers (classifier, AI, UI) decide how to present that information.

---

## Future Improvements

- Rule priorities
- Rule versioning
- Confidence scoring
- Plugin-based rules
- User-defined rules

# classifier.py

## Purpose

This module performs the first-stage classification of every indexed file.

It assigns each file to a broad storage category based purely on its location.

Unlike `storage_scope.py`, which separates storage into logical scopes (User, Technical, Other), this classifier provides more detailed technical categories.

---

## Categories

- USER_FILES
- USER_TEMP
- APPDATA
- WINDOWS_TEMP
- PROGRAM_DATA
- RECYCLE_BIN

---

## Responsibilities

- Normalize paths.
- Ignore directories.
- Detect known Windows storage locations.
- Return category labels.

---

## Inputs

- Path
- is_directory flag

---

## Outputs

Returns:

- Category string

or

- None

---

## Workflow

Receive Path
        │
        ▼
Ignore Directories
        │
        ▼
Normalize Path
        │
        ▼
Check Known Locations
        │
        ▼
Return Category

---

## Dependencies

Uses

- String path matching

Used By

- SQLite indexing
- Cleanup analysis
- Statistics generation

---

## Design Philosophy

This classifier intentionally avoids any expensive filesystem operations.

Classification depends entirely on path patterns, making it extremely fast.

---

## Relationship with Storage Scope

Storage Scope

USER_DATA
TECHNICAL
OTHER

↓

Detailed Classifier

USER_FILES
APPDATA
PROGRAM_DATA
WINDOWS_TEMP
RECYCLE_BIN
USER_TEMP

The scope classifier determines **which pipeline** a file enters.

The detailed classifier determines **which technical category** it belongs to.

---

## Future Improvements

- OneDrive detection
- Steam libraries
- Browser caches
- IDE caches
- Docker storage
- Android Studio
- WSL
- User-defined categories

# cleanup_classifier.py

## Purpose

This module converts deterministic Rule Engine results into a standardized cleanup object that the rest of the application can understand.

It does **not** make cleanup decisions.

Instead, it transforms Rule Engine output into a product-facing format.

---

## Responsibilities

- Validate Rule Engine output.
- Ignore invalid actions.
- Convert RuleResult into CleanupItem.
- Preserve all metadata required by later stages.

---

## Inputs

- File context
  - path
  - size

- RuleResult
  - action
  - category
  - rule_id
  - risk
  - confidence
  - reason

---

## Outputs

Returns a CleanupItem containing:

- path
- size
- action
- category
- rule_id
- risk
- confidence
- reason

Returns None if the RuleResult is invalid.

---

## Workflow

Rule Engine
      │
      ▼
Validate Action
      │
      ├── Invalid → Ignore
      │
      ▼
Create CleanupItem
      │
      ▼
Aggregation Layer

---

## Dependencies

Uses

- dataclasses

Used By

- Cleanup Aggregator
- Reporting
- AI Analysis
- UI

---

## Design Philosophy

This module intentionally contains **zero business rules**.

Rule Engine decides.

CleanupClassifier standardizes.

This separation keeps classification logic isolated from presentation logic.

---

## Future Improvements

- Additional metadata fields
- Cleanup priority
- User feedback score
- Historical cleanup information

---

## Notes

Think of this module as an adapter between the Rule Engine and the rest of the application.

# cleanup_aggregator.py

## Purpose

This module groups multiple CleanupItem objects into meaningful summaries.

Instead of showing thousands of individual files, it creates rule/category-based groups for reporting and UI.

---

## Responsibilities

- Collect CleanupItems.
- Group by:
  - Action
  - Category
  - Rule ID
- Calculate:
  - Total Files
  - Total Size
- Preserve risk, confidence, and reason.
- Return sorted summaries.

---

## Inputs

CleanupItem objects.

---

## Outputs

CleanupGroup objects containing:

- action
- category
- rule_id
- files
- size
- risk
- confidence
- reason

---

## Workflow

CleanupItem
      │
      ▼
Group by
(Action, Category, Rule)
      │
      ▼
Accumulate
Files + Size
      │
      ▼
Generate CleanupGroup
      │
      ▼
Sort by Size

---

## Dependencies

Uses

- defaultdict
- dataclasses

Used By

- Dashboard
- Reports
- AI Layer
- Cleanup Summary

---

## Design Philosophy

Aggregation never changes cleanup decisions.

It only summarizes existing decisions.

This guarantees that reporting cannot accidentally modify Rule Engine behaviour.

---

## Performance Notes

Grouping uses dictionary lookups.

Time complexity is approximately O(n), making it suitable for very large datasets.

---

## Future Improvements

- Folder-level aggregation
- User-defined grouping
- Duplicate-aware summaries
- Time-based cleanup history

---

## Notes

This file converts raw cleanup data into information that humans can quickly understand.

# ai_analysis/pipeline.py

## Purpose

This module is the orchestration layer for the complete AI analysis system.

It coordinates every AI component without containing provider-specific logic or cleanup rules.

It is the single entry point for AI-assisted storage analysis.

---

## Responsibilities

- Accept initial analysis clusters.
- Configure batching strategy.
- Coordinate payload creation.
- Execute AI analysis.
- Manage provider selection.
- Handle iterative deep analysis.
- Return validated final results.

---

## High-Level Workflow

Initial Clusters
        │
        ▼
Cluster Summarizer
        │
        ▼
Payload Builder
        │
        ▼
AI Analysis Engine
        │
        ▼
Provider Manager
        │
        ▼
Selected Provider
(Groq / Gemini / OpenRouter)
        │
        ▼
Response Validation
        │
        ▼
Iterative Analyzer
        │
        ▼
Final Analysis Result

---

## Inputs

- Initial folder/file clusters.
- Provider settings.
- API key store.
- Pipeline configuration.

---

## Outputs

Returns an IterativeAnalysisResult containing validated AI recommendations.

---

## Configuration Responsibilities

The pipeline controls:

### Batching

- Deep batch size
- Shallow batch size
- Deep drill threshold

### Concurrency

- Maximum worker threads
- Continue-on-error behaviour

### Iterative Analysis

- Maximum recursive rounds
- Minimum child size
- Maximum child expansion

---

## Dependencies

Uses

- ClusterSummarizer
- PayloadBuilder
- AIAnalysisEngine
- IterativeAnalyzer
- ProviderFactory
- ProviderSettings

Used By

- Main application
- AI Analysis workflow

---

## Design Philosophy

This module is an orchestrator.

It does not:

- Decide cleanup rules.
- Build prompts.
- Parse AI responses.
- Call providers directly.

Instead, it coordinates specialized modules.

---

## Safety

The pipeline performs analysis only.

It never deletes, modifies, or moves files.

All AI output is advisory.

---

## Future Improvements

- Streaming analysis
- Resume interrupted analysis
- Adaptive provider routing
- Cost-aware provider selection
- Local model support
- Distributed execution

---

## Notes

This file is effectively the "conductor" of the AI subsystem.

Every AI component remains independent, allowing providers, prompts, payload builders, or analysis strategies to evolve without changing the orchestration layer.

# cluster_builder.py

## Purpose

This module converts millions of indexed files into a hierarchical folder tree that can be efficiently analysed by later AI stages.

Instead of working directly on a flat file list, the AI subsystem operates on FolderNode objects connected as a tree.

This module is responsible for building that structure.

---

## Responsibilities

- Create one folder tree per drive.
- Create FolderNode objects.
- Link parent-child relationships.
- Aggregate file counts and storage usage.
- Track global statistics.

---

## Inputs

Indexed files containing:

- Full path
- File size

---

## Outputs

Returns a FolderTree containing:

- Root nodes
- Folder hierarchy
- Recursive storage information
- File statistics

---

## Workflow

Indexed Files
      │
      ▼
Extract Parent Paths
      │
      ▼
Create FolderNodes
      │
      ▼
Link Parent / Child
      │
      ▼
Aggregate Statistics
      │
      ▼
FolderTree

---

## Design Philosophy

AI should never reason over millions of independent files.

Instead, it reasons over meaningful folder clusters.

This drastically reduces complexity.

---

## Dependencies

Uses

- FolderNode
- ntpath

Used By

- Boundary Resolver
- Candidate Selector
- AI Pipeline

---

## Performance Notes

Tree construction happens once.

Every later AI stage reuses the same hierarchy instead of rebuilding it.

---

## Future Improvements

- Incremental updates
- Junction detection
- Symbolic link awareness
- Parallel tree construction

---

## Notes

This module transforms raw storage data into a navigable knowledge graph for the AI subsystem.

# boundary_resolver.py

## Purpose

This module determines the most meaningful starting points for AI analysis.

Rather than analysing an entire drive from the root (e.g. `C:\`), it identifies natural storage boundaries that represent logical groups of data.

---

## Responsibilities

- Detect important Windows storage boundaries.
- Skip overly broad container folders.
- Ensure every significant storage area is represented.
- Produce a balanced starting set for AI analysis.

---

## Typical Boundaries

Examples include:

- Local AppData
- Roaming AppData
- LocalLow
- ProgramData

The implementation discovers these dynamically instead of hardcoding usernames.

---

## Inputs

FolderTree

---

## Outputs

A list of FolderNode objects representing the initial AI analysis boundaries.

---

## Workflow

FolderTree
      │
      ▼
Locate Known Boundaries
      │
      ▼
Check Coverage
      │
      ▼
Descend Broad Containers
      │
      ▼
Generate Starting Nodes

---

## Design Philosophy

Large container folders (such as `C:\Users`) provide little semantic value.

AI performs better when analysis begins from meaningful storage regions rather than arbitrary filesystem roots.

---

## Dependencies

Uses

- FolderTree
- FolderNode

Used By

- Candidate Selector
- AI Pipeline

---

## Future Improvements

- Cloud storage boundaries
- Game launcher libraries
- Development environments
- User-defined boundaries

---

## Notes

This module defines **where AI should begin looking**, not **what AI should recommend**.

# candidate_selector.py

## Purpose

This module chooses which folder clusters deserve AI attention.

The complete folder tree may contain thousands of nodes, but only a limited number can be analysed efficiently.

This selector prioritizes the highest-impact candidates.

---

## Responsibilities

- Rank folders by storage impact.
- Apply minimum size thresholds.
- Respect coverage targets.
- Limit maximum candidate count.
- Produce a balanced analysis set.

---

## Inputs

FolderNode objects generated by the Boundary Resolver.

---

## Outputs

CandidateSelection containing:

- Selected folders
- Coverage percentage
- Selected size
- Available size
- Candidate counts

---

## Workflow

Boundary Nodes
      │
      ▼
Sort by Size
      │
      ▼
Apply Threshold
      │
      ▼
Measure Coverage
      │
      ▼
Stop at Target
      │
      ▼
CandidateSelection

---

## Selection Strategy

Priority is based on storage impact rather than folder count.

A few large folders usually explain most disk usage, making them significantly more valuable for AI analysis than hundreds of tiny folders.

---

## Dependencies

Uses

- FolderNode

Used By

- Payload Builder
- AI Pipeline

---

## Design Philosophy

AI context is expensive.

Instead of maximising the number of analysed folders, the goal is to maximise the amount of storage represented within a fixed token budget.

---

## Performance Notes

Selection is performed before any prompt generation, reducing unnecessary AI requests.

---

## Future Improvements

- Adaptive thresholds
- Historical importance scoring
- User-priority folders
- Cost-aware provider optimisation

---

## Notes

This module answers a single question:

**"Out of everything on the system, what is worth sending to the AI first?"**

# cluster_summarizer.py

## Purpose

This module compresses selected folder clusters into concise summaries before they are sent to the AI.

Instead of exposing every file inside a folder, it extracts only the information required for intelligent reasoning.

This significantly reduces token usage while preserving context.

---

## Responsibilities

- Summarize folder statistics.
- Calculate important metrics.
- Remove unnecessary detail.
- Produce compact AI-ready cluster summaries.

---

## Inputs

Selected FolderNode objects.

Each node may contain:

- Folder path
- Total size
- File count
- Child folders
- Classification metadata

---

## Outputs

ClusterSummary objects containing only the information required by the AI.

Typical information includes:

- Folder name
- Relative importance
- Storage usage
- Number of files
- High-level characteristics

---

## Workflow

Candidate Folders
        │
        ▼
Extract Statistics
        │
        ▼
Remove Low-Value Details
        │
        ▼
Generate Compact Summary
        │
        ▼
Payload Builder

---

## Dependencies

Uses

- FolderNode models
- Analysis models

Used By

- Payload Builder
- AI Pipeline

---

## Design Philosophy

The AI should understand *what exists*, not *every individual file*.

This module converts filesystem data into semantic summaries.

---

## Performance Notes

Runs entirely in memory.

No filesystem access.

No AI calls.

---

## Future Improvements

- Folder fingerprints
- Historical growth statistics
- Duplicate indicators
- Application ownership
- File-type distribution

---

## Notes

This module is responsible for reducing token consumption before prompt generation.

# payload_builder.py

## Purpose

This module converts internal analysis models into a provider-independent payload.

It creates the exact structured data that every AI provider will receive.

The payload contains only validated, serialized information.

---

## Responsibilities

- Convert summaries into JSON-compatible structures.
- Preserve important metadata.
- Remove unsupported objects.
- Keep provider input consistent.

---

## Inputs

- Cluster summaries
- Configuration
- Analysis metadata

---

## Outputs

Structured payload ready for:

- Gemini
- Groq
- OpenRouter
- Future providers

---

## Workflow

Cluster Summaries
        │
        ▼
Validate Objects
        │
        ▼
Serialize
        │
        ▼
Attach Metadata
        │
        ▼
Provider Payload

---

## Dependencies

Uses

- Analysis models
- JSON serialization

Used By

- Prompt Builder
- AI Pipeline

---

## Design Philosophy

Providers should never receive Python objects directly.

Every provider receives the same normalized payload.

This keeps provider implementations extremely simple.

---

## Performance Notes

Pure serialization.

No filesystem operations.

No prompt generation.

No API communication.

---

## Future Improvements

- Payload compression
- Versioned payload schema
- Binary serialization
- Streaming payload support

---

## Notes

Think of this module as the translation layer between the application and every AI provider.

# prompt_builder.py

## Purpose

This module converts the provider payload into the final prompt that will be sent to an LLM.

It defines how the AI should think about the storage data.

---

## Responsibilities

- Build system instructions.
- Insert payload.
- Define response expectations.
- Maintain prompt consistency.
- Keep prompts provider-independent.

---

## Inputs

Provider payload.

---

## Outputs

Final prompt containing:

- Instructions
- Storage information
- Expected response format
- Safety guidance

---

## Workflow

Structured Payload
        │
        ▼
Insert Instructions
        │
        ▼
Attach Storage Context
        │
        ▼
Define Output Rules
        │
        ▼
Final Prompt

---

## Dependencies

Uses

- Payload Builder
- Response Schema

Used By

- Analysis Engine
- Providers

---

## Design Philosophy

Prompt engineering should exist in one place.

Changing prompts should never require changing providers or business logic.

---

## Safety

The prompt clearly instructs the AI to:

- Analyse only.
- Never assume unknown information.
- Respect system files.
- Produce structured responses.

---

## Future Improvements

- Multiple prompt strategies
- Cost-aware prompts
- Fast vs Deep prompts
- Localization
- Model-specific prompt optimization

---

## Notes

This file defines the "language" used to communicate with every LLM.

# analysis_engine.py

## Purpose

This module executes AI analysis using the prepared prompt and the selected provider.

It is responsible for running the complete AI request lifecycle while remaining independent of any specific provider implementation.

Unlike the Pipeline, which coordinates the entire AI workflow, the Analysis Engine performs the actual inference step.

---

## Responsibilities

- Receive the final prompt.
- Select the configured provider.
- Send the request.
- Handle provider failures.
- Parse responses.
- Return validated analysis results.

---

## Inputs

- Final prompt
- Provider configuration
- Provider instance

---

## Outputs

Returns:

- Structured AI analysis
- Provider metadata
- Execution status

---

## Workflow

Prompt
    │
    ▼
Analysis Engine
    │
    ▼
Provider Manager
    │
    ▼
Selected Provider
    │
    ▼
LLM
    │
    ▼
Structured Response

---

## Dependencies

Uses

- Provider Manager
- Response Schema

Used By

- AI Pipeline
- Iterative Analyzer

---

## Design Philosophy

The Analysis Engine knows **how to execute** an AI request.

It does **not** know:

- How prompts are built.
- Which folders were selected.
- Which provider is available.
- How cleanup rules work.

This keeps AI execution isolated from business logic.

---

## Error Handling

Responsible for handling:

- Provider errors
- Timeout failures
- Invalid responses
- Parsing failures

without crashing the application.

---

## Future Improvements

- Automatic retries
- Streaming responses
- Cost tracking
- Token usage tracking
- Provider fallback

---

## Notes

This module is the execution layer of the AI subsystem.

# provider_manager.py

## Purpose

This module manages all available AI providers and selects the most appropriate one for execution.

It acts as the central routing layer between the application and every supported LLM provider.

---

## Responsibilities

- Track registered providers.
- Select active provider.
- Validate provider availability.
- Handle provider switching.
- Expose provider capabilities.

---

## Inputs

- Provider settings
- API configuration

---

## Outputs

Returns an initialized provider ready for inference.

---

## Workflow

Pipeline
    │
    ▼
Provider Manager
    │
    ├── Gemini
    ├── Groq
    ├── OpenRouter
    └── Future Providers
            │
            ▼
Selected Provider

---

## Dependencies

Uses

- Provider Factory
- Provider Settings

Used By

- Analysis Engine
- AI Pipeline

---

## Design Philosophy

The rest of the application should never know which provider is currently active.

Every module simply requests "an AI provider".

The manager decides which implementation to return.

---

## Future Improvements

- Provider ranking
- Health monitoring
- Automatic failover
- Cost-aware routing
- Latency-aware routing

---

## Notes

Think of this module as the traffic controller for all AI requests.

# provider_factory.py

## Purpose

This module creates concrete provider instances.

It hides provider construction details from the rest of the application.

---

## Responsibilities

- Instantiate providers.
- Pass required configuration.
- Validate provider names.
- Return initialized objects.

---

## Inputs

- Provider identifier
- Provider settings

---

## Outputs

Returns one of:

- GeminiProvider
- GroqProvider
- OpenRouterProvider

---

## Workflow

Provider Name
      │
      ▼
Factory
      │
      ├── Gemini
      ├── Groq
      └── OpenRouter
              │
              ▼
Provider Object

---

## Dependencies

Uses

- Gemini Provider
- Groq Provider
- OpenRouter Provider

Used By

- Provider Manager

---

## Design Philosophy

Object creation should exist in one place.

If a new provider is added, only the Factory needs modification.

Higher-level modules remain unchanged.

---

## Future Improvements

- Dynamic provider registration
- Plugin providers
- Local model support
- Custom providers

---

## Notes

This module implements the Factory Design Pattern for AI providers.

# iterative_analyzer.py

## Purpose

This module enables multi-stage AI analysis instead of relying on a single LLM request.

Rather than asking the AI to analyse an entire storage tree at once, the analysis progresses through multiple iterations, drilling deeper only into folders that require additional inspection.

---

## Responsibilities

- Receive initial AI recommendations.
- Decide whether deeper analysis is required.
- Expand selected folder clusters.
- Merge results across iterations.
- Stop when configured limits are reached.

---

## Inputs

- Initial analysis result
- Folder tree
- Pipeline configuration

---

## Outputs

Returns:

- Final IterativeAnalysisResult
- Combined recommendations
- Analysis metadata

---

## Workflow

Initial AI Analysis
        │
        ▼
Need More Detail?
        │
   ┌────┴────┐
   │         │
  No        Yes
   │         │
   ▼         ▼
 Finish   Expand Folder
               │
               ▼
        Generate New Payload
               │
               ▼
          AI Analysis
               │
               ▼
         Merge Results
               │
               ▼
           Repeat

---

## Design Philosophy

Instead of making one extremely expensive AI request, analysis becomes progressively deeper only where necessary.

This dramatically reduces token usage while improving recommendation quality.

---

## Dependencies

Uses

- Pipeline
- Cluster Builder
- Candidate Selector

Used By

- AI Pipeline

---

## Future Improvements

- Adaptive recursion depth
- Confidence-based expansion
- User-driven drill-down
- Cost-aware stopping

---

## Notes

This module implements progressive exploration rather than brute-force analysis.

# models.py

## Purpose

This module defines every shared data model used throughout the AI subsystem.

Instead of passing dictionaries between modules, strongly typed models are used to improve consistency and maintainability.

---

## Responsibilities

- Define analysis objects.
- Define folder models.
- Define cluster models.
- Define provider result models.
- Define pipeline models.

---

## Typical Models

Examples include:

- FolderNode
- ClusterSummary
- CandidateSelection
- AnalysisResult
- ProviderResponse
- ExecutionMetadata

---

## Inputs

Python objects.

---

## Outputs

Structured model instances shared across the project.

---

## Workflow

Raw Data
     │
     ▼
Model Objects
     │
     ▼
Shared Across Pipeline

---

## Dependencies

Uses

- dataclasses
- typing

Used By

Almost every AI module.

---

## Design Philosophy

Business objects should have a single source of truth.

Using shared models avoids:

- Dictionary key mismatches
- Missing fields
- Serialization inconsistencies

---

## Future Improvements

- Validation
- Versioned models
- Immutable models
- JSON schema generation

---

## Notes

This file acts as the contract between every AI component.

# response_schema.py

## Purpose

This module defines the exact structure that every AI response must follow.

Regardless of which provider generates the answer, the response is validated against a common schema before entering the application.

---

## Responsibilities

- Define expected response fields.
- Validate AI responses.
- Reject malformed outputs.
- Ensure compatibility across providers.

---

## Expected Information

Typical fields include:

- Recommendations
- Confidence
- Explanation
- Folder references
- Suggested actions

---

## Workflow

LLM Response
      │
      ▼
Schema Validation
      │
      ├── Invalid
      │      │
      │      ▼
      │   Reject / Retry
      │
      ▼
Valid Response
      │
      ▼
Application

---

## Dependencies

Uses

- JSON parsing
- Validation logic

Used By

- Analysis Engine
- Provider Manager
- Pipeline

---

## Design Philosophy

LLMs are probabilistic.

The application should never trust raw responses.

Everything must conform to a predictable schema before use.

---

## Safety

Prevents:

- Missing fields
- Invalid actions
- Unexpected formats
- Hallucinated structures

---

## Future Improvements

- Versioned schemas
- Automatic repair
- Partial validation
- Streaming validation

---

## Notes

This module separates AI creativity from application reliability.

# provider.py

## Purpose

This module defines the common interface that every AI provider must implement.

Instead of allowing Gemini, Groq, or OpenRouter to expose different APIs, the application communicates through a single abstract provider contract.

---

## Responsibilities

- Define the provider interface.
- Standardize inference methods.
- Standardize provider metadata.
- Ensure every provider behaves consistently.

---

## Inputs

Provider-specific prompt and configuration.

---

## Outputs

Standardized ProviderResponse.

---

## Workflow

Application
      │
      ▼
Provider Interface
      │
      ├── Gemini
      ├── Groq
      └── OpenRouter
             │
             ▼
      Standard Response

---

## Dependencies

Used By

- Provider Factory
- Provider Manager
- Analysis Engine

Implemented By

- GeminiProvider
- GroqProvider
- OpenRouterProvider

---

## Design Philosophy

The application depends on an abstraction, not on concrete providers.

This follows the Dependency Inversion Principle (SOLID).

---

## Future Improvements

- Streaming interface
- Local model interface
- Async execution
- Capability negotiation

---

## Notes

Every future provider should implement this interface before being registered in the factory.

# provider_settings.py

## Purpose

This module stores all provider-specific configuration in one place.

Instead of scattering model names, API limits, and provider options across the codebase, everything is centralized here.

---

## Responsibilities

- Store provider configuration.
- Store model identifiers.
- Store limits.
- Store timeout values.
- Store provider preferences.

---

## Inputs

Application configuration.

---

## Outputs

ProviderSettings objects.

---

## Workflow

Configuration
      │
      ▼
Provider Settings
      │
      ▼
Provider Manager
      │
      ▼
Selected Provider

---

## Dependencies

Used By

- Provider Manager
- Factory
- Analysis Engine

---

## Design Philosophy

Configuration should never be hardcoded inside provider implementations.

Keeping configuration centralized makes switching models much easier.

---

## Future Improvements

- Environment profiles
- Cost profiles
- Model capability flags
- Dynamic provider discovery

---

## Notes

This file separates "how providers work" from "which settings they use".

# execution_metrics.py

## Purpose

This module records performance metrics for every AI analysis session.

Its responsibility is observability—not business logic.

---

## Responsibilities

- Measure execution time.
- Track provider latency.
- Record token usage (where available).
- Track iteration count.
- Collect performance statistics.

---

## Inputs

Execution events generated throughout the AI pipeline.

---

## Outputs

ExecutionMetrics object containing:

- Total duration
- Provider time
- Iteration count
- Number of AI requests
- Token statistics (if available)

---

## Workflow

Pipeline Event
      │
      ▼
Metric Recorder
      │
      ▼
ExecutionMetrics
      │
      ▼
Reporting / Debugging

---

## Dependencies

Uses

- time
- dataclasses

Used By

- Pipeline
- Analysis Engine
- Iterative Analyzer

---

## Design Philosophy

Performance measurement should remain completely independent from analysis logic.

Removing metrics should never change application behaviour.

---

## Benefits

Provides visibility into:

- Slow providers
- Expensive prompts
- Excessive iterations
- Pipeline bottlenecks

---

## Future Improvements

- Memory usage tracking
- Cost estimation
- Per-stage timing
- Visualization support
- Historical benchmarking

---

## Notes

This module exists purely for diagnostics and optimization.

# direct_file_cluster.py

## Purpose

This module handles situations where folder-level analysis is not sufficient.

Instead of sending an entire folder hierarchy to the AI, it creates focused clusters of individual files that deserve direct analysis.

This is typically used for exceptional cases where file-level reasoning provides better recommendations than folder-level reasoning.

---

## Responsibilities

- Identify standalone high-value files.
- Build compact file clusters.
- Preserve file metadata.
- Reduce unnecessary context.

---

## Inputs

Indexed files containing:

- Path
- Size
- Category
- Classification

---

## Outputs

DirectFileCluster objects.

Each cluster represents a small collection of files suitable for direct AI analysis.

---

## Workflow

Indexed Files
      │
      ▼
Filter Candidates
      │
      ▼
Group Related Files
      │
      ▼
Create DirectFileCluster
      │
      ▼
Payload Builder

---

## Dependencies

Uses

- Analysis models

Used By

- AI Pipeline
- Iterative Analyzer

---

## Design Philosophy

Folders explain storage structure.

Individual files explain exceptional storage usage.

This module exists only for those exceptional cases.

---

## Future Improvements

- Duplicate file clustering
- Archive clustering
- Large media clustering
- Installer grouping

---

## Notes

This module complements Folder Clusters rather than replacing them.

# mock_provider.py

## Purpose

This module simulates an AI provider without requiring any external API.

It is primarily intended for development, testing, and debugging.

---

## Responsibilities

- Return predictable AI responses.
- Simulate provider behaviour.
- Enable offline testing.
- Verify pipeline correctness.

---

## Inputs

Prompt.

---

## Outputs

Mock ProviderResponse.

---

## Workflow

Prompt
    │
    ▼
Mock Provider
    │
    ▼
Predefined Response
    │
    ▼
Pipeline

---

## Dependencies

Implements

- Provider Interface

Used By

- Unit tests
- Development
- Offline debugging

---

## Design Philosophy

Testing should never depend on internet connectivity or API credits.

Every major pipeline component should be testable using deterministic responses.

---

## Future Improvements

- Configurable scenarios
- Error simulation
- Timeout simulation
- Invalid schema simulation

---

## Notes

This provider exists purely for development and should never be used in production.

# AI Providers (Gemini, Groq, OpenRouter)

## Purpose

These modules provide concrete implementations of the common Provider Interface.

Every provider converts the application's generic request into the provider's native API format and converts the provider's response back into the application's standard format.

---

## Responsibilities

Each provider is responsible only for:

- Authentication
- API communication
- Request formatting
- Response parsing
- Error translation

Providers are **not** responsible for:

- Prompt generation
- Payload creation
- Cleanup logic
- Folder analysis
- Business rules

---

## Common Workflow

Application Prompt
        │
        ▼
Provider Adapter
        │
        ▼
Provider API
        │
        ▼
Raw Response
        │
        ▼
Normalize Response
        │
        ▼
ProviderResponse

---

## Shared Design Philosophy

Every provider behaves like an adapter.

The rest of the application never knows:

- Which API endpoint was used.
- Which model generated the answer.
- How authentication works.

Only standardized ProviderResponse objects leave these modules.

---

# Gemini Provider

## Purpose

Communicates with Google's Gemini models.

Best suited for:

- Long-context reasoning
- Detailed storage explanations
- Complex folder analysis

---

## Strengths

- Large context window
- High-quality reasoning
- Reliable structured output

---

## Future Improvements

- Streaming
- Batch requests
- Automatic model selection

---

# Groq Provider

## Purpose

Communicates with Groq-hosted language models.

Designed for extremely fast inference.

---

## Strengths

- Very low latency
- Quick iterative analysis
- Fast UI responsiveness

---

## Future Improvements

- Model benchmarking
- Adaptive routing

---

# OpenRouter Provider

## Purpose

Provides access to multiple third-party models through a unified gateway.

Allows the application to switch between models without changing internal architecture.

---

## Strengths

- Multiple model options
- Vendor flexibility
- Easy experimentation

---

## Future Improvements

- Automatic model fallback
- Cost-aware routing
- Capability detection

---

## Overall Architecture

                 Provider Interface
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
     Gemini          Groq        OpenRouter
        │               │               │
        └───────────────┼───────────────┘
                        ▼
               Standard ProviderResponse

---

## Notes

Every future provider should follow the exact same contract so that the rest of the AI pipeline remains unchanged.

# base.py

## Purpose

This module defines the common rule interface used throughout the cleanup engine.

Every cleanup rule in the application inherits from this base implementation, ensuring a consistent contract across the rule system.

---

## Responsibilities

- Define the rule interface.
- Standardize rule execution.
- Define required outputs.
- Provide shared functionality for all rules.

---

## Inputs

Typically receives:

- File path
- File metadata
- Classification information

---

## Outputs

Returns a RuleResult containing:

- Action
- Confidence
- Reason
- Category
- Risk Level

---

## Workflow

Incoming File
      │
      ▼
Rule Interface
      │
      ▼
Concrete Rule
      │
      ▼
RuleResult

---

## Dependencies

Used By

- Protected Rules
- Safe Rules
- User Data Rules
- Rule Engine

---

## Design Philosophy

Every cleanup rule should behave identically from the Rule Engine's perspective.

The Rule Engine should never care which specific rule is executing.

---

## Future Improvements

- Rule priorities
- Rule metadata
- Rule versioning
- Rule statistics

---

## Notes

This file establishes the foundation of the application's rule system.

# protected_rules.py

## Purpose

This module prevents dangerous cleanup recommendations by identifying storage locations that should never be suggested for deletion.

It acts as the application's primary safety layer.

---

## Responsibilities

- Detect protected system locations.
- Block unsafe recommendations.
- Preserve operating system integrity.

---

## Protected Areas

Typical examples include:

- Windows
- System32
- Boot files
- Critical application folders
- Essential configuration directories

---

## Inputs

- File path
- Classification

---

## Outputs

Returns whether the file is protected.

If protected:

- Cleanup recommendation is blocked.

---

## Workflow

File
 │
 ▼
Protected Rule
 │
 ├── Protected
 │        │
 │        ▼
 │     Reject
 │
 ▼
Continue

---

## Dependencies

Uses

- Base Rule

Used By

- Rule Engine

---

## Design Philosophy

False negatives are preferable to false positives.

If there is uncertainty, the safer option is to avoid recommending deletion.

---

## Future Improvements

- Windows version awareness
- Dynamic protected locations
- Application-specific protection
- Registry integration

---

## Notes

This is arguably the most important safety component in the cleanup engine.

# safe_rules.py

## Purpose

This module identifies files and folders that are generally safe to remove.

Unlike Protected Rules, which prevent deletion, Safe Rules identify low-risk cleanup opportunities.

---

## Responsibilities

- Detect cache directories.
- Detect temporary files.
- Detect disposable storage.
- Assign cleanup confidence.

---

## Typical Targets

Examples include:

- Temporary folders
- Application caches
- Browser cache
- Installer leftovers
- Crash dumps
- Thumbnail cache

---

## Inputs

- File metadata
- Path
- Classification

---

## Outputs

RuleResult describing:

- Suggested action
- Confidence
- Risk
- Reason

---

## Workflow

Incoming File
      │
      ▼
Safe Rule Evaluation
      │
      ├── Safe
      │       │
      │       ▼
      │   Recommendation
      │
      ▼
Ignore

---

## Dependencies

Uses

- Base Rule

Used By

- Rule Engine

---

## Design Philosophy

Only well-understood disposable storage should receive automatic cleanup recommendations.

Everything else should require additional reasoning or user confirmation.

---

## Future Improvements

- Browser-specific caches
- IDE caches
- Package manager caches
- AI-generated confidence adjustment

---

## Notes

This module generates the majority of automatic cleanup opportunities within the application.

# user_data_rules.py

## Purpose

This module provides special handling for user-owned files.

Unlike Safe Rules, which identify disposable technical storage, User Data Rules ensure that personal files are treated conservatively and never become automatic cleanup candidates.

---

## Responsibilities

- Detect user-owned content.
- Identify personal storage locations.
- Prevent unsafe recommendations.
- Provide context for AI analysis.

---

## Typical User Locations

Examples include:

- Desktop
- Documents
- Downloads
- Pictures
- Videos
- Music

These folders are assumed to contain user-created or user-important data.

---

## Inputs

- File path
- Classification
- File metadata

---

## Outputs

RuleResult containing:

- User-data classification
- Risk level
- Recommendation policy

---

## Workflow

Incoming File
      │
      ▼
User Data Rules
      │
      ├── Personal Data
      │       │
      │       ▼
      │   Conservative Handling
      │
      ▼
Continue

---

## Dependencies

Uses

- Base Rule

Used By

- Rule Engine
- Cleanup Classifier
- AI Pipeline

---

## Design Philosophy

The application assumes that user data has significantly higher value than temporary system storage.

Recommendations involving user files should always require stronger evidence and clearer explanations.

---

## Future Improvements

- Detect project folders
- Recognize cloud-synced folders
- Learn user preferences
- Historical access patterns

---

## Notes

This module is a protection layer for user-owned content, not a cleanup engine.

# rules/classifier.py

## Purpose

This module determines which rule set should evaluate a file.

It acts as the dispatcher inside the Rule Engine.

Instead of embedding every rule into one large function, it routes files toward the appropriate rule family.

---

## Responsibilities

- Inspect file classification.
- Select rule category.
- Route execution.
- Return the selected rule pipeline.

---

## Inputs

- File path
- Storage classification
- Metadata

---

## Outputs

Selected rule set:

- Protected Rules
- Safe Rules
- User Data Rules

---

## Workflow

Incoming File
      │
      ▼
Storage Classification
      │
      ├── Protected
      │        │
      │        ▼
      │   Protected Rules
      │
      ├── Technical
      │        │
      │        ▼
      │    Safe Rules
      │
      ├── User Data
      │        │
      │        ▼
      │ User Data Rules
      │
      ▼
Rule Result

---

## Dependencies

Uses

- Protected Rules
- Safe Rules
- User Data Rules

Used By

- Rule Engine

---

## Design Philosophy

The Rule Engine should coordinate rule execution, not contain every rule itself.

Separating rule selection from rule implementation keeps the system modular and easier to extend.

---

## Future Improvements

- Priority-based routing
- Plugin rule packs
- Organization-specific rules
- Rule statistics

---

## Notes

This module is the router of the cleanup rule system.


# database/db.py

## Purpose

This module is the persistence layer of the application.

It owns the SQLite database and provides a single interface for storing and retrieving scan results.

The database serves as the application's working index, allowing expensive filesystem operations to happen once while enabling fast UI queries afterwards.

---

## Responsibilities

- Create database schema.
- Manage SQLite connections.
- Store indexed files.
- Store folder summaries.
- Execute queries.
- Support updates after scanning.

---

## Primary Data

The database typically maintains information such as:

### Files

- Path
- Size
- Category
- Classification
- Metadata

### Folders

- Folder path
- Recursive size
- Direct size
- File counts

---

## Inputs

Data generated by:

- MFT Scanner
- Folder Analyzer
- Classification Pipeline

---

## Outputs

Structured query results for:

- Dashboard
- Folder Explorer
- AI Pipeline
- Statistics

---

## Workflow

Scan Pipeline
      │
      ▼
SQLite Database
      │
      ├── Files Table
      ├── Folder Table
      └── Metadata
              │
              ▼
Dashboard / AI / Reports

---

## Dependencies

Uses

- sqlite3

Used By

- Folder Analyzer
- Dashboard
- AI Pipeline
- Main Application

---

## Design Philosophy

Scanning should be expensive.

Browsing should be cheap.

Once the filesystem has been indexed, every later component works from SQLite instead of repeatedly touching the disk.

---

## Performance Benefits

- Fast folder navigation
- Instant searching
- Efficient aggregation
- Reduced filesystem I/O
- Reusable scan results

---

## Future Improvements

- Incremental indexing
- Database migrations
- WAL optimization
- Compression
- Background maintenance

---

## Notes

This module is the backbone of the application's data layer.

Nearly every subsystem depends on the indexed data it provides rather than accessing the filesystem directly.

# memory.py

## Purpose

This module manages the application's runtime memory usage.

Its goal is to keep the Storage Assistant responsive even when processing millions of MFT entries by releasing unnecessary objects at the correct time.

Unlike the database layer, which persists data, this module focuses entirely on temporary in-memory resources.

---

## Responsibilities

- Monitor memory usage during scanning.
- Release large temporary objects.
- Trigger garbage collection when appropriate.
- Provide memory statistics for diagnostics.
- Prevent excessive RAM consumption.

---

## Inputs

Runtime objects such as:

- MFT entries
- Folder trees
- AI clusters
- Temporary analysis data

---

## Outputs

- Memory statistics
- Cleanup actions
- Optimized runtime state

---

## Workflow

Large Dataset
      │
      ▼
Processing Complete
      │
      ▼
Memory Manager
      │
      ├── Release Objects
      ├── Garbage Collection
      ├── Log Memory Usage
      └── Return Resources

---

## Dependencies

Uses

- gc
- psutil (if available)
- Runtime statistics

Used By

- Scan Pipeline
- AI Pipeline
- Main Application

---

## Design Philosophy

Large datasets should exist in memory only for as long as they are needed.

Once information has been persisted to SQLite, the original in-memory structures should be discarded to minimize RAM usage.

---

## Performance Benefits

- Lower peak RAM usage.
- Better responsiveness on 8–16 GB systems.
- Reduced risk of memory fragmentation.
- Improved stability during large scans.

---

## Future Improvements

- Adaptive cleanup thresholds.
- Background memory monitoring.
- Memory pressure detection.
- Automatic cache eviction.

---

## Notes

This module is responsible for keeping the application scalable on consumer hardware, especially during full-drive scans.

# settings.py

## Purpose

This module centralizes the application's configuration.

Instead of scattering constants throughout the codebase, all configurable values are maintained in a single location.

This ensures consistency across the application and simplifies future updates.

---

## Responsibilities

- Store application-wide configuration.
- Define scan behaviour.
- Configure AI defaults.
- Configure database settings.
- Define UI defaults.
- Expose reusable constants.

---

## Typical Configuration

### Scanner

- Scan limits
- Thread counts
- Size thresholds

### AI

- Default provider
- Batch sizes
- Iteration limits
- Timeout values

### Database

- Database location
- Cache settings

### UI

- Default sorting
- Refresh intervals
- Theme defaults

---

## Inputs

Configuration values provided by developers or future user preferences.

---

## Outputs

Centralized settings accessed by all application modules.

---

## Workflow

Application Startup
        │
        ▼
Load Settings
        │
        ▼
Distribute Configuration
        │
        ▼
Application Modules

---

## Dependencies

Used By

- Scanner
- Database
- AI Pipeline
- UI
- Main Application

---

## Design Philosophy

Configuration should be data, not code.

Changing behaviour should require modifying settings rather than altering implementation logic.

---

## Benefits

- Easier maintenance.
- Consistent defaults.
- Simpler experimentation.
- Better scalability.

---

## Future Improvements

- User-editable settings.
- Environment profiles.
- Configuration validation.
- Import/export settings.

---

## Notes

This module acts as the central configuration hub for the entire application.