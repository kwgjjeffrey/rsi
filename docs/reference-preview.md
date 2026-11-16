# Evidence references

Assessment citations open their existing project files inside the workbench. Markdown uses the existing renderer; JSON is formatted and scripts are read-only text. Nested Markdown file links resolve relative to that document. Missing or oversized files show the actual read error; no file is executed.

The current project's canonical data root is returned by the workspace endpoint. The browser maps absolute citations to project-relative paths and calls the existing `read` operation on demand. The runtime remains the authority for canonical path containment and file size checks, including symlinks. References outside that project remain plain text.

Component selection: Omni's common display/navigation components do not provide a file preview. Reuse the workbench's installed shadcn Button and Base UI Dialog, including nested dialog focus/Escape behavior. No new overlay implementation or input state is introduced.

Consumer distribution uses the verified Release archive on the `distribution` branch, including its compiled runtime. Source remains on `main`; npx skills follows the consumer branch for installation and updates.
