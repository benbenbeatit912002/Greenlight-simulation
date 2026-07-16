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
- Sibling GreenLight-Gym2 repositories may be inspected read-only but must not
  be modified.
- For every completed user request, follow AGENTS.md and create an English HTML
  work log.

Perform these steps in order:

1. Confirm the current folder and run:
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

5. Check for Python 3.12, uv, and the local project environment. Install only
   the free and open-source dependencies required to run this project. If
   `.venv` does not exist, run in PowerShell:
   $env:UV_CACHE_DIR = "$PWD\.uv-cache"
   uv sync --extra greenlight --python 3.12

6. Run the tests:
   & '.\.venv\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_*.py' -v

7. Start the simulator:
   & '.\.venv\Scripts\python.exe' -B .\server.py --engine auto

8. Verify that http://127.0.0.1:4173/ opens and report whether it is using:
   - the full GreenLight 2 model; or
   - the browser approximation model.

9. If the full model cannot start, diagnose missing sibling GreenLight-Gym2
   source code or free dependencies. Do not modify the sibling repository and
   do not use paid services.

10. For every non-trivial change, use this bounded workflow:
    - The primary Codex agent implements the change.
    - A read-only reviewer agent inspects it and gives recommendations.
    - The primary agent evaluates and applies justified recommendations.
    - Perform no more than one follow-up review.
    - Run the relevant tests and update the English HTML work log.

Continue until the simulator starts successfully or you reach a genuine safety
blocker that requires my decision.
```

