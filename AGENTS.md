# GreenLight Simulation Project Instructions

## Scope

- Work only inside this `greenlight-2-simulator` repository unless the user explicitly expands the scope.
- Treat every GreenLight practice repository, every GreenLight-Gym2 practice repository, and every GreenLight 2 research or thesis directory outside this repository as protected research material.
- Source files in protected GreenLight code repositories may be read or imported when necessary for compatibility or scientific-model execution. This is the only permitted external access.
- Never modify, delete, move, rename, format, patch, stage, commit, check out, install into, test inside, or create cache or bytecode files in protected code repositories.
- Never read or modify thesis manuscripts, paper drafts, datasets, experiment outputs, results, notes, or other non-source research artifacts unless the user explicitly requests that exact file.
- Keep every virtual environment, dependency, cache, log, output, and generated file inside this repository. Use `PYTHONDONTWRITEBYTECODE=1` and Python `-B` whenever protected source code is imported.
- Do not run broad recursive commands from a parent directory that contains protected research material. Read only the specific source paths required by the simulator.
- If a requested task would require writing to protected research material, stop and report the conflict instead of attempting the write.
- Open this repository itself as the workspace root. Do not open a common parent directory that also contains protected research projects.
- Preserve unrelated user changes already present in the worktree.

## Cost and model usage

- Do not use the OpenAI API, request an API key, or call another usage-billed external AI service for this project.
- Built-in Codex subagents may be used for review because they do not require a separate API key or create a separate OpenAI API bill. They may still count against the user's existing Codex or ChatGPT plan usage.
- Keep review loops bounded: one initial review and at most one follow-up review.

## Codex and reviewer workflow

For non-trivial code changes:

1. The primary Codex agent inspects and implements the requested change.
2. Spawn a reviewer subagent after the initial implementation.
3. Tell the reviewer to remain read-only and provide concrete recommendations about correctness, model behavior, UI, accessibility, security, and tests.
4. The primary agent evaluates every recommendation and applies only justified changes.
5. Run relevant tests before completion.
6. Record reviewer recommendations and the primary agent's decisions in the HTML work log.

Documentation-only changes and very small mechanical edits may skip the reviewer, but the reason must be recorded in the work log.

## HTML work logs

- Before completing every user request handled for this repository, create one standalone UTF-8 HTML work log in `worklogs/`.
- Write the work-log index and every work-log entry in English, even when the conversation is in another language.
- Use a sortable filename such as `YYYY-MM-DD-NNN-short-title.html`. Increment `NNN` for multiple logs on the same date.
- Update `worklogs/index.html` with a link to the newest log.
- Each log must include:
  - date and task title;
  - a concise summary of the user's request;
  - decisions and assumptions;
  - actions taken and files changed;
  - reviewer recommendations and disposition, or why review was skipped;
  - validation and test results;
  - Git status when relevant.
- Summarize the work rather than storing hidden chain-of-thought or a verbatim private transcript.
- Never record API keys, credentials, tokens, private environment values, or other secrets.
- If a request only asks a question and changes no code, still create a brief log and state that no project files were modified except the log itself.
