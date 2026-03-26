# 🧠 Minion 2.0 Skill Engineering Guide

Skills are the **High-Fidelity Blueprints** that drive the Minion 2.0 reasoning engine. They are written in Markdown (DSL), making them easy for humans to design and for the agent to execute.

## Anatomy of a Skill Blueprint

A skill file (located in `minion2/skills/`) consists of multiple **Phases**. Each phase is a logical stage in a research mission.

### 1. The Phase Header
Define a new stage with `# Phase: [Name]`.
- **Purpose**: Tracks mission progress in the dashboard's "Telemetry" view.

### 2. The Goal Statement
Define the objective with `## Goal: [Objective]`.
- **Logic**: The agent uses this as its primary constraint during the phase's reasoning loops.

### 3. The Toolkit
Specify available tools with `[tools]: tool1, tool2`.
- **Available Toolset**: `web_search`, `goto`, `remember_memory`, `calc`, `write_file`, `click`, `type`, `screenshot`, `list_dir`, `read_file`.

### 4. The Strategy
Provide guidance with `[strategy]: [Tactical instructions]`.
- **Hint**: Use this to set "Stealth" levels (e.g., "Use DuckDuckGo exclusively") or "Accuracy" standards (e.g., "Cross-reference across three sources").

---

## Example Blueprint: `research.md`

```markdown
# Phase: RECONNAISSANCE
## Goal: Identify primary contact points and social profiles.
[tools]: web_search, goto, remember_memory
[strategy]: Start with broad DuckDuckGo queries. Archive all relevant URLs and usernames using `remember_memory`. 

# Phase: DEEP_OSINT
## Goal: Extract specific contact information (emails, phones).
[tools]: web_search, goto, download_file, remember_memory
[strategy]: Navigate directly to professional profiles (LinkedIn, etc.). Look for "About" or "Contact" sections.

# Phase: REPORTING
## Goal: Compile final findings.
[tools]: write_file
[strategy]: Format the final response as a Markdown report starting with "FINAL REPORT: ".
```

## 🏗️ Execution Logic (Synaptic Transitions)

The Orchestrator moves between phases when a phase is "Manifested":
- **PHASE_COMPLETE**: When the agent explicitly outputs `PHASE_COMPLETE: [Summary]`, the engine instantly triggers the next phase defined in the blueprint.
- **Mission Termination**: Once the last phase is reached and completed, the engine persists the final result to the **Persistence Hub** and marks the mission as **Done**.

## 💡 Best Practices
- **Isolation**: Keep phases focused. Don't ask for a report in the "Reconnaissance" phase.
- **Memory**: Use `remember_memory` across phases to build a cumulative knowledge base for the agent.
- **Tool Discipline**: Limit the toolset in the `[tools]` section to prevent "Brain Bloat" (LLM hallucinations).
