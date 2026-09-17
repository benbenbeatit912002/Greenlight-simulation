# Security Policy

## Supported code

Security fixes are applied to the latest code on the default branch. Older commits, local experiments, and unmerged branches are not maintained as supported releases.

## Report a vulnerability

Please do not publish credentials, private greenhouse data, protected research paths, exploit details, or other sensitive information in a public issue.

Use GitHub's **Report a vulnerability** option on the repository Security page when it is available:

<https://github.com/benbenbeatit912002/Greenlight-simulation/security/advisories/new>

If private vulnerability reporting is unavailable, use the repository's **Security contact request** issue form. It is intentionally limited to a general affected area and confirmations; do not include vulnerability details. The repository owner can then establish a private contact channel.

Include, when safe:

- the affected commit or version;
- the affected component and engine;
- the conditions required to reproduce the problem;
- the potential impact;
- a minimal proof of concept with secrets and personal paths removed; and
- any suggested mitigation.

The maintainer will acknowledge a usable report, assess severity and scope, and coordinate a fix before public disclosure where practical. No response-time guarantee is currently offered.

## Scope and security boundaries

- The server is designed for local loopback use at `127.0.0.1`; exposing it to an untrusted network is unsupported.
- The application is not a production greenhouse controller, safety alarm, or authorization system.
- The optional GreenLight-Gym2 source path is imported read-only. The simulator must not install into, modify, test inside, or create bytecode/cache files in that external repository.
- Keep `.venv`, dependency caches, logs, outputs, and generated files inside this repository.
- Never commit API keys, GitHub tokens, greenhouse credentials, private sensor data, thesis files, experiment results, or unpublished research artifacts.
- Model inaccuracy and unsafe agronomic interpretation are tracked as model-quality issues unless they also create a software security impact.
