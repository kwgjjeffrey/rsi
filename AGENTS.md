# Development

Read docs/skill-authoring.md. Keep consumer SKILL.md and development AGENTS.md separate. Add actual business modules and verification before advertising capabilities. Installed tools must never import this checkout. The source repository is https://git.corp.kuaishou.com/ks-ep/ea-zonghe/omni/rsi. GitLab is the canonical source remote. GitHub release tooling remains a legacy scaffold and is not a published installation channel. For ongoing Skill engineering, use the independently installed Awesome Skill Maker release artifact and read its SKILL.md; never import its development checkout. Acquire verified artifacts from https://github.com/kwgjjeffrey/awesome-skill-maker/releases when unavailable.

## Local data hygiene

Keep `.data/` for operational runtime state and intentionally retained project assets: normalization scaffolds, datasets, sprint records, and replay evidence. Put development screenshots, temporary requests, diagnostic probes, test fixtures, validation outputs, and uncertain intermediate artifacts under `.trial/`. Never use the live `.data/` directory as a scratch or verification workspace. Promote artifacts into project data only when they are deliberately accepted as project records.
