[Русская версия](README.ru.md)

# REBGE

A verifiable reconstruction of Beyond Good & Evil 20th Anniversary Edition in Rust/Bevy.
This is an independent implementation based on reverse engineering, not recovered developer source code.

## Goal

Reconstruct source code that builds and plays as close to the original game as possible.
Accuracy comes first. Porting to another engine can come later.

## Requirements

- Windows x64; this is the currently verified platform.
- Stable Rust with Cargo and the MSVC toolchain.
- Visual Studio Build Tools with **Desktop development with C++** and a Windows SDK.
- A working graphics driver. The current build has been verified with Vulkan.
- The separate runtime asset pack; assets are not included in the source repository.
- Internet access for the first Cargo dependency download, or an existing local cache.
- Python 3.10+ for export and validation tools. Python packages are listed in
  `requirements.txt`; Python is not required just to run the compiled preview.

Ghidra, the original game, and game automation dependencies are needed for their
respective reverse-engineering workflows, not for launching an existing runtime pack.

## Quick start

1. Open PowerShell in the project root and check `rustc --version` and `cargo --version`.
2. Obtain the separately supplied runtime pack and place its contents under
   `asset-packs/stage43-runtime/`. Check that
   `asset-packs/stage43-runtime/scenes/sally-hangar/scene.json` exists.
   A source-only checkout cannot generate the pack without the extracted asset library.
3. Build and launch:

   ```powershell
   cargo build --locked --manifest-path bevy/Cargo.toml
   .\run-hangar.cmd
   ```

4. For Python tools, install their dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   python tools/assets/export_runtime_pack.py --check-pack asset-packs/stage43-runtime
   ```

If the pack is elsewhere, set `$env:REBGE_ASSETS` to its absolute directory before
launching. A missing pack requires supplying assets; rebuilding code will not create it.
An MSVC linker error usually means the C++ Build Tools or Windows SDK are missing.

## Progress and milestones

Current checkpoint: **4.3 complete for the tested slice** (October 10, 2026).
Jade is playable in the hangar: animation playback, skinning, walking, running,
starting, stopping, and turns. All 89 tests passed, including private fixtures.
The source is organized by system, with separate tests and a standalone asset pack.
Full-game reconstruction and full native pose/physics parity are still incomplete.

| Milestone | Status |
|---|---|
| 1. Resource access and localization | Complete |
| 2. Hangar geometry and assets | Static scene complete |
| 3. First runnable Bevy build | Complete |
| 4.1–4.2. Character data and animation foundations | Complete for the selected slice |
| 4.3. Movement and animation transitions | Complete for the tested slice |
| Repository preparation and separate asset pack | Complete |

## Roadmap

- **4.4:** movement physics, collisions, contacts, and gravity.
- **4.5:** original camera behavior, limits, and obstacle handling.
- **4.6:** integrate and compare the complete playable hangar slice.
- **5:** interactions, dialogue, AI, combat, objectives, audio, and scene transitions.
- **6:** expand game coverage, verify saves/loading, and prepare the runtime.
- **Later:** consider a port to another engine after reconstruction.

See [detailed stages](docs/STAGES.md).

## README TODO

- [ ] Add a Ghidra section: setup, local MCP connection, and native-code analysis workflow.

## Project layout

| Directory | Purpose |
|---|---|
| `bevy/src/animation/` | Reconstructed numerical algorithms |
| `bevy/src/input/` | Input, selectors, predicates, and adapters |
| `bevy/src/world/animation/` | Data, controllers, poses, stepping, ECS, and telemetry |
| `bevy/src/{app,assets,camera,world,ui,debug}/` | Other runtime systems |
| `bevy/tests/unit/<system>/` | Tests organized by system |
| `bevy/tests/fixtures/` | Small numerical fixtures |
| `tools/`, `docs/` | Reverse engineering, export, measurements, formats, and evidence |
| `AGENTS.md`, `.agents/skills/` | Agent instructions and skills |

Assets, raw recordings, the Ghidra database, and installed third-party binaries are
separate local dependencies excluded by `.gitignore`. See [repository contents](docs/REPOSITORY_LAYOUT.md).

## Build and test

Verified environment: Windows x64, stable Rust, and MSVC C++ Build Tools with the Windows SDK.
The project uses Bevy 0.19; dependency versions are pinned in `bevy/Cargo.lock`.
Run from the project root:

```powershell
cargo build --locked --manifest-path bevy/Cargo.toml
cargo test --locked --manifest-path bevy/Cargo.toml
```

Use `--offline` when dependencies are already cached. Private fixture tests require
local `assets/` and `reports/` data. To run the full checkpoint suite of 89 tests:

```powershell
cargo test --offline --manifest-path bevy/Cargo.toml -- --include-ignored
```

See [test layout and dependencies](docs/TESTING.md).

## Assets and launch

Runtime assets are supplied separately as a pack containing `manifest.json`, `scenes/`,
and `textures/`. Launchers use `asset-packs/stage43-runtime/` by default. To select a pack:

```powershell
$env:REBGE_ASSETS = (Resolve-Path ./asset-packs/stage43-runtime).Path
.\run-hangar.cmd
```

`run-preview.cmd` opens the diagnostic scene from the same pack. To launch directly:

```powershell
.\bevy\target\debug\rebge.exe --assets "$env:REBGE_ASSETS" --scene scenes/sally-hangar/scene.json
```

For a validation screenshot, use `./bevy/Run-Rebge.ps1 -Assets <directory> -Capture`.
An existing runtime pack does not require the original game or Ghidra to run.

Controls: WASD/left stick to move, Shift/R2 to run, right stick/mouse to control the camera,
R to reset the scene, and P to pause. This is a playable preview, not the complete game.

## Export an asset pack

Requires Python 3.10+ and its standard library. The full local asset library must already exist:

```powershell
python tools/assets/export_runtime_pack.py --source assets --output asset-packs/stage43-runtime
python tools/assets/export_runtime_pack.py --check-pack asset-packs/stage43-runtime
```

The exporter includes only dependencies of the hangar and controlled scenes and records
source and payload SHA256 hashes. Source assets remain in place. See [pack format](docs/RUNTIME_ASSET_PACK.md).

## Reverse engineering and agents

Start with the [mechanism index](docs/REVERSE_INDEX.md) and [stages](docs/STAGES.md).
Detailed project documentation is currently in Russian.

Workflow: audit native code → form a hypothesis → test the original → compare paired
measurements → implement a fix. Only one agent may control game input at a time;
after input, release controls and return focus to Codex/ChatGPT.

Global plugins are installed separately; project skills live in `.agents/skills/`.
For original-game readers and exporters, install Python dependencies with:

```powershell
python -m pip install -r requirements.txt
```

Historical probes may need paths adjusted for the local game installation; consult
their help and project documentation. Repository creation is handled by the user; preparation
does not initialize Git, create commits, or publish files.
