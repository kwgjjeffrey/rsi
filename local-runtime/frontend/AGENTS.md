# Workbench development

Use the installed shadcn skill and official CLI for component generation. Keep shared business data in the runtime; browser code uses workspace dispatch and does not mutate records. Never embed a target project or fixture in UI source. View models preserve dataset/sprint/round boundaries and distinguish unknown scores from zero.

Build with npm ci and npm run build (Node 22+). vite-plugin-singlefile produces ../web/index.html, an ignored generated resource embedded by Rust. No extra dev server is needed for delivery. Run npm test, the Python runtime tests, and real browser checks for tree navigation, case detail, trajectories, Markdown and empty/error states.
