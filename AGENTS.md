# Development

Read docs/skill-authoring.md. Keep consumer SKILL.md and development AGENTS.md separate. Add actual business modules and verification before advertising capabilities. Installed tools must never import this checkout. The source and release repository is https://github.com/kwgjjeffrey/rsi for this distribution. Choose GitHub or GitLab per project/user instructions; do not hard-code GitLab as the universal publishing policy. For ongoing Skill engineering, use the independently installed Awesome Skill Maker release artifact and read its SKILL.md; never import its development checkout. Acquire verified artifacts from https://github.com/kwgjjeffrey/awesome-skill-maker/releases when unavailable.

## Local data hygiene

Keep `.data/` for operational runtime state and intentionally retained project assets: normalization scaffolds, datasets, sprint records, and replay evidence. Put development screenshots, temporary requests, diagnostic probes, test fixtures, validation outputs, and uncertain intermediate artifacts under `.trial/`. Never use the live `.data/` directory as a scratch or verification workspace. Promote artifacts into project data only when they are deliberately accepted as project records.
