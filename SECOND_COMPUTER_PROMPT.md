# Prompt for the second computer

Copy the prompt below into Codex on the second Windows computer only after the latest changes have been pushed to GitHub.

```text
You are working on my second Windows computer. The current workspace should be
the existing folder for the GreenLight greenhouse simulation project.

Goal:
Safely synchronize the latest Greenlight-simulation repository from GitHub,
read the project rules, install the required dependencies, run the tests, and
start the simulator.

GitHub repository:
https://github.com/benbenbeatit912002/Greenlight-simulation.git

Cost restrictions:
- You may use all tokens included in my existing Codex or ChatGPT plan.
- Do not purchase or enable additional credits, Fast mode, or paid add-ons.
- Do not use the OpenAI API, an API key, or any usage-billed AI service.
- If the included plan quota is exhausted, stop and tell me. Do not purchase
  credits or switch to API billing.
- Built-in Codex subagents or reviewers are allowed, with at most two review
  rounds per task.

Safety rules:
- Do not delete, reset, or overwrite existing local files.
- Do not use `git reset --hard` or discard local changes with checkout.
- Modify only the Greenlight-simulation project.
- The user's GreenLight practice repositories, GreenLight-Gym2 practice
  repositories, GreenLight 2 research directories, thesis files, paper data,
  experiments, and results are protected research material.
- You may read or import specific source-code files from the protected
  GreenLight code repositories when required for compatibility or full-model
  execution. This is the only permitted access outside Greenlight-simulation.
- Never modify, delete, move, rename, format, patch, stage, commit, check out,
  install into, test inside, or create cache or bytecode files in a protected
  code repository.
- Never read or modify thesis manuscripts, paper drafts, datasets, experiment
  outputs, results, notes, or other non-source research artifacts unless I ask
  for that exact file.
- Keep every virtual environment, downloaded dependency, cache, log, output,
  and generated file inside Greenlight-simulation. Set
  `PYTHONDONTWRITEBYTECODE=1` and launch Python with `-B` before importing any
  protected source code.
- Do not run broad recursive commands from a parent folder containing protected
  research. Read only the exact source paths required by this simulator.
- Open only Greenlight-simulation as the workspace root. If the current
  workspace is a parent folder that also contains protected research, stop and
  ask me to reopen Codex directly on the simulation repository.
- For every completed user request, follow AGENTS.md and create an English HTML
  work log.

Perform these steps in order:

1. Resolve and display only the current folder:
   Resolve-Path .

   Confirm that it is the dedicated Greenlight-simulation folder and is not a
   protected research folder or a shared parent containing protected research.
   Do not list the parent directory. When safe, run:
   git status -sb
   git remote -v

2. If this folder is already a Git repository:
   - Confirm that `origin` is the GitHub URL shown above.
   - If local uncommitted changes exist, do not overwrite them. Report them to
     me before continuing.
   - If the working tree is safe, run:
     git fetch origin
     git pull --ff-only origin main

3. If this folder is not a Git repository:
   - If it is empty, run:
     git clone https://github.com/benbenbeatit912002/Greenlight-simulation.git .
   - If it already contains files, do not delete or overwrite them. Stop and
     propose a safe migration plan.

4. After pull or clone completes, read these files completely:
   - AGENTS.md
   - README.md
   - SECOND_COMPUTER_PROMPT.md
   - the latest HTML file in worklogs/

5. Check for Python 3.12, uv, and the local project environment without writing
   outside this repository. Install only free and open-source dependencies into
   this repository's `.venv`. If `.venv` does not exist, run in PowerShell:
   $env:PYTHONDONTWRITEBYTECODE = '1'
   $env:UV_CACHE_DIR = "$PWD\.uv-cache"
   uv sync --extra greenlight --python 3.12

6. Run the tests:
   & '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_*.py' -v

7. Start the simulator:
   $env:PYTHONDONTWRITEBYTECODE = '1'
   & '.\.venv\Scripts\python.exe' -B .\server.py --engine auto

8. Verify that http://127.0.0.1:4173/ opens and report whether it is using the
   full GreenLight 2 model or the browser approximation model.

9. The simulator may read/import the exact sibling GreenLight-Gym2 source path,
   but it must not write there. Do not run installers, formatters, tests, Git
   mutations, or broad searches in that repository. If full-model startup would
   require any write outside Greenlight-simulation, stop and report the safety
   conflict instead of continuing.

10. For every non-trivial change, use this bounded workflow:
    - The primary Codex agent implements the change.
    - A read-only reviewer agent inspects it and gives recommendations.
    - The primary agent evaluates and applies justified recommendations.
    - Perform no more than one follow-up review.
    - Run the relevant tests and update the English HTML work log.

Continue until the simulator starts successfully or you reach a genuine safety
blocker that requires my decision.
```
