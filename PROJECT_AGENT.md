# Field Robotics Lab agent

Publish one new project per run to the selected GitHub repository. Rotate through UAV, automation, and robotics, following the last topic in the project index. Build a prototype around a concrete problem and a testable idea. Read the index before selecting an idea and check for similar problems and methods. Choose a project with a different engineering contribution from earlier entries.

## Build and verify

- Put the project in `projects/YYYY-MM-DD-short-slug/`, using the scheduled date in `America/New_York`. If the project for the scheduled date already exists, report its link.
- Include runnable source code, a small demo with synthetic or redistributable example data, and a project image such as a rendered simulation, screenshot, or output plot. Render data and diagrams from the actual demo when feasible.
- Write a README with the problem, the design decision, copy-paste run commands, a verified result or example output, and the prototype's limitations. Give image links descriptive alt text.
- Keep demos self-contained and use offline analysis or simulation for UAV projects. Use new code and keep required assets in the project folder.
- Run the README commands and check the expected result and image links before publishing.

## Publish

Add one row to the lab's project index. Commit the validated project and the index together to the repository's default branch through GitHub. Base the commit on the latest branch head and publish by fast-forward. If the branch moves, reread the index and rebuild on top of the updated head, checking again for the scheduled date. Verify the new commit is reachable from the default branch and report the project link, change, and test result. If validation or publishing fails, leave a concise failure report.

Schedule the agent to run every three days in `America/New_York`.
