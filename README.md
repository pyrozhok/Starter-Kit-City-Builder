# Design-to-UI agent for a game engine

Agents that build game UI from a mockup and check the result against it, write tests and review PRs.
They work in a Godot 4.7 city builder, a fork of Kenney's Starter Kit City Builder.
An eval grades every run, and every mistake it finds becomes a rule in the skill.

<p align="center"><img src="docs/media/main-menu.gif" width="720"
alt="Main menu built by the agent: live city behind, hover, New Game"/></p>

<p align="center">Main menu built by an agent from a figcraft mockup.</p>

## TL;DR

- **generate-ui** built the main menu from a mockup in 16 minutes, from the approved plan to the final screenshot, my review of the first draft included. It took 1 fix iteration of 3. 28/31 layers are within ±2px. The other 3 are expected: one comes from Godot's line height, and two from a text cut from the run. Where the mockup contradicted itself, the agent asked me instead of guessing.
- **review-pr**: 4 runs on 2 PRs, graded by me as the PR author. False findings didn't go down: 3 of 4 runs had one. Two other numbers changed. Findings checked against the code before reporting went from 1/9 to 8/9, and wrong fixes went from 1 to 0. Recall isn't measured yet.
- **Setup**: Claude Code with Opus 5.5 and mattpocock-skills 1.3.1. The skills, the MCP server, the menu and the evals were built in one day: 64 commits on 2026-11-21.

| Mockup ([`design/main_menu.png`](design/main_menu.png)) | Result, iteration 1 (`godot.screenshot`) |
|---|---|
| <img src="design/main_menu.png" width="420"/> | <img src="evals/generate-ui/001/iter1_main_save.png" width="420"/> |

## Requirements

- Godot 4.7 and [uv](https://docs.astral.sh/uv/).
- Claude Code with the plugin [mattpocock-skills](https://github.com/mattpocock/skills). The evals ran with version 1.3.1 (`49dd158`). The plugin updates itself, so later runs may use a newer version.
  - Install: `/plugin install mattpocock-skills@claude-plugins-official`. `.claude/settings.json` enables it, so Claude Code also offers to install it when you trust the folder.
  - `review-pr` calls its `code-review` and `write-test` calls its `tdd`. Without the plugin both skills stop and ask you to install it.
  - The project skills add what the plugin can't know about Godot and this game: the build and test gates, a Godot checklist, the screenshot-and-compare loop, and the rules that came out of the evals.

## generate-ui: main menu from a mockup

The mockup was made in figcraft, a Figma-like design tool with an MCP server. `tools/design/figcraft.py` reads its layer tree, so the agent can compare its screenshot with the mockup layer by layer.

```mermaid
flowchart LR
  A["mockup<br/>(figcraft)"] --> B["map.json<br/>layer → node"] --> C["build scenes"] --> D["godot.screenshot<br/>PNG + layout.json"] --> E["figcraft.py diff<br/>±2px"]
  E -- mismatches --> F["fix<br/>(≤3 iterations)"] --> D
  E -- done --> G["eval"]
```

- 28/31 layers fall within ±2px, and 32/33 theme values match exactly. It took 1 of 3 fix iterations.
- Of the 3 layers off by more than 2px, the eval lists all 3 as expected. One is 3px taller because Godot's line height is ascent + descent, and the skill now lists that mismatch as expected. The other two are a notification's text and time: the build shows "just now" where the mockup has "12 min ago", because relative times were cut from the run ([#3](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/3)).
- **The agent asked instead of guessing.** In the mockup's "no save" frame the disabled button icons had opacity 1.0, but the component's `State=Disabled` variant says 0.35. The agent built 0.35 and asked me which one was right. The answer was the component.
- You can check the geometry without figcraft or Godot. The repo has the mockups, every screenshot and the iteration-1 `.layout.json` files. With uv alone, `uv run --script tools/design/figcraft.py diff design/main_menu.figcraft MainMenu evals/generate-ui/001/iter1_main_save.layout.json design/main_menu.map.json` gives 28/31.
- Figma isn't supported yet. Step 1 of generate-ui needs an adapter that writes the same `design/<name>.map.json`, for example through the Figma MCP ([#8](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/8)).

Details: [`evals/generate-ui/001-main-menu.md`](evals/generate-ui/001-main-menu.md).

## review-pr evals, graded by the PR author

| Run | PR | Findings | Correct | False | Wrong fixes | Verified before reporting |
|---|---|---|---|---|---|---|
| [001](evals/review-pr/001-pr1.md) | #1 | 9 | 7 | 1 | 1 | 1/9 |
| [002](evals/review-pr/002-pr1.md) ⚠ | #1 | 7 | 6 | 0 | 0 | 7/7 |
| [003](evals/review-pr/003-pr1.md) | #1 | 5 | 4 | 1 | 0 | 4/5 |
| [004](evals/review-pr/004-pr4.md) | #4 | 9 | 8 | 1 | 0 | 8/9 |

Findings: reported by the agent; Correct / False: as graded; Wrong fixes: correct findings with a wrong proposed fix; Verified: findings the agent checked against the code before reporting.

⚠ 002 reviewed only 6 new commits, not the full PR, so it isn't directly comparable with the other runs.

Since 001, findings checked before reporting went from 1/9 to 8/9 and wrong fixes from 1 to 0. False findings stayed at one per run: 001, 003 and 004 each had one, and each one became a rule in the skill.

### From a false finding to a rule

In run 004, finding #6 said a cleanup line would leak if the assert before it failed, and proposed moving it to `after_each`. That's false: a failed GUT assert doesn't stop the test. The agent had read the test code but never checked how GUT behaves. Commit `5297b37` added this to step 5 of [`review-pr`](.claude/skills/review-pr/SKILL.md):

> GUT asserts don't abort the test: the lines after a failed assert still run. Don't suggest moving cleanup out of a test body on that ground.

### Limits

- Runs 001–003 all reviewed PR #1, and the rules added after them came from that PR. Only 004 tests the skill on a PR it wasn't tuned on.
- Precision is graded, recall isn't: nobody counted the bugs the agent missed.
- Next: a set of PRs with planted bugs, rerun after every rule change, to measure both.

## How it's built

```mermaid
flowchart LR
  A["mattpocock-skills<br/>code-review, tdd, …"] --> B["project skills<br/>review-pr, generate-ui, write-test"]
  B --> C["godot MCP<br/>build, run_tests, screenshot, scene_tree"]
  B -. reads .-> D["AGENTS.md, GLOSSARY.md"]
```

Skills live in [`.claude/skills/`](.claude/skills), the MCP server in [`tools/mcp/godot_mcp.py`](tools/mcp/godot_mcp.py) and the evals in [`evals/`](evals).

### What carries over to another engine

The skills run the engine only through the MCP tools: `build`, `run_tests`, `screenshot` (a PNG plus a `.layout.json` with every visible Control's rect), and `scene_tree` / `find_scenes`. The layout diff compares mockup rects with `.layout.json` and knows nothing about Godot. To port the workflow, reimplement those tools for the new engine and rewrite the Godot-specific rules in the skills (scene text, mouse filters, GUT).

<details>
<summary>Links and setup</summary>

- PRs: [#1 Agent skills](https://github.com/pyrozhok/Starter-Kit-City-Builder/pull/1) and [#4 generate-ui + main menu](https://github.com/pyrozhok/Starter-Kit-City-Builder/pull/4).
- Roadmap:
  - [#2 pytest suite for the MCP server](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/2)
  - [#3 rotating tips and relative notification times](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/3)
  - [#5 Options and Credits screens](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/5)
  - [#6 save slots and Load screen](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/6)
  - [#8 Figma input for generate-ui](https://github.com/pyrozhok/Starter-Kit-City-Builder/issues/8)
- Run it in Claude Code:
  1. Install everything under [Requirements](#requirements). [`.mcp.json`](.mcp.json) starts the server with `uv run --script tools/mcp/godot_mcp.py`. It runs `godot` by default; to run another binary, set `GODOT_BIN` in your environment before starting Claude Code. The binary must be Godot 4.7: any other version rewrites `*.import` on every build.
  2. Check that `/mcp` lists `godot` as connected. Then try `/review-pr <n>`, or ask for UI from a mockup (generate-ui) or for a test (write-test).
- MCP tools of the `godot` server ([`tools/mcp/godot_mcp.py`](tools/mcp/godot_mcp.py)):
  - `build`: reimport assets and compile all project scripts (optionally `export_preset`).
  - `run_tests`: run the GUT suite in `tests/` (filter by `script` or `test_name`).
  - `find_scenes` / `scene_tree`: search scenes by node name, type or script; dump a scene's node tree.
  - `screenshot`: render a scene in windowed Godot at an exact size (optional `state`, `hover`) and save a PNG plus a `.layout.json` of every visible Control's rect.
- Tests: [GUT](https://github.com/bitwes/Gut) 9.7.1 in `addons/gut`. From the CLI: `godot --headless -s res://addons/gut/gut_cmdln.gd -gconfig=res://.gutconfig.json -gexit`.
- `docs/agents/` refers to the plugin's `/triage`, `/domain-modeling` and `/grill-with-docs`.
- Rules for agents: [`AGENTS.md`](AGENTS.md).

</details>

---

## Original starter kit (Kenney)

<p align="center"><img src="icon.png"/></p>

This package includes a basic template for a 3D city builder in Godot 4.7. Includes features like;

- Building and removing structures
- Smooth camera controls
- Dynamic MeshLibrary creation
- Saving/loading
- Sprites and 3D Models _(CC0 licensed)_

### Screenshot

<p align="center"><img src="screenshots/screenshot.png"/></p>

### Controls

| Key | Command |
| --- | --- |
| <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> | Move camera |
| <kbd>F</kbd> | Camera to center |
| <kbd>Middle mouse button</kbd> | Hold to rotate camera |
| <kbd>Scroll wheel</kbd> | Zoom |
| <kbd>Left mouse button</kbd> | Place building |
| <kbd>DEL</kbd> | Remove building |
| <kbd>Right mouse button</kbd> | Rotate building |
| <kbd>Q</kbd> <kbd>E</kbd>  | Toggle between buildings |
| <kbd>F1</kbd> | Save |
| <kbd>F2</kbd> | Load |

### Instructions

#### 1. How to add more buildings?

Duplicate one of the existing resources in the 'structures' folder, adjust the properties in the inspector. Select the 'Builder' node in the scene and add your new resources to the 'Structures' array.

#### 2. How to adjust building models?

Select the resource of the building you'd like to change in the 'structures' folder, adjust the model in the inspector.

#### 3. How to save and load cities?

Pressing F1 during gameplay will save the current city to disk, F2 will load it from the same location. The file is saved as 'map.res' in the user folder (see below). You can adjust this in the 'action_save' and 'action_load' functions found in the 'builder.gd' script.

User data folder:

> Windows: `%APPDATA%/Godot/app_userdata/Starter Kit City Builder/`

> Linux: `~/.local/share/godot/app_userdata/Starter Kit City Builder/`

> MacOS: `~/Library/Application Support/Godot/app_userdata/Starter Kit City Builder/`

#### 4. How to include city data in the project and load this?

You'll find a sample map in the 'sample map' folder, to load this during gameplay press F3. You can find the function that handles this as 'action_load_resources' found in the 'builder.gd' script.

### License

MIT License

Copyright (c) 2026 Kenney

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Assets included in this package (2D sprites, 3D models and sound effects) are [CC0 licensed](https://creativecommons.org/publicdomain/zero/1.0/)
