# Front-app — HackUPC 2026

Cross-platform desktop application that visualises warehouse layouts in interactive 3D. Built with Tauri (Rust shell) + React + Three.js.

## Stack

| Layer | Technology |
|---|---|
| Desktop shell | Tauri v2 (Rust) |
| UI framework | React 18 + TypeScript |
| 3D rendering | Three.js via `@react-three/fiber` + `@react-three/drei` |
| Build tool | Vite |
| Backend sidecar | Python FastAPI binary (auto-launched by Tauri) |

## Architecture

```
src/
├── app/            # Root component and routing
├── application/    # React hooks (useBays, useWarehouse, useObstacles)
├── domain/         # Models and services (bay, warehouse, obstacle)
├── infrastructure/ # WebSocket client and data repositories
├── presentation/   # 3D components (BayMesh, Scene3D…) and UI panels
└── shared/         # Constants, math utils, color maps
```

The Tauri Rust layer (`src-tauri/src/lib.rs`) launches the Python backend as a sidecar process on startup and bridges its WebSocket messages to the React frontend as Tauri events.

## Run in development

```bash
cd front-app
npm install
npm run tauri dev
```

> The backend must be compiled first — see [backend/README.md](../backend/README.md).

## Build for production

```bash
npm run tauri build
```

Packages are generated in `src-tauri/target/release/bundle/`:

| File | Platform |
|---|---|
| `HackUPC 2026_x.x.x_amd64.deb` | Ubuntu / Debian |
| `HackUPC 2026-x.x.x.x86_64.rpm` | Fedora / RedHat |

## Install (Linux)

Install the prerequisite:

```bash
sudo apt install libwebkit2gtk-4.1-0
```

Then install the package:

```bash
sudo dpkg -i 'HackUPC.2026_0.1.0_amd64.deb'
```

Launch with `hackupc-2026` or from the applications menu.
