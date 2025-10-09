# New Flow Branch Overview

## Backend graph engine
- The queue-based graph engine composes dedicated subsystems for runtime state, command handling, traversal, and worker orchestration, instantiating components such as `GraphStateManager`, `ResponseStreamCoordinator`, `EventManager`, and `WorkerPool` when it boots a workflow execution.【F:api/core/workflow/graph_engine/graph_engine.py†L1-L207】
- Execution runs through a generator that starts subsystems, streams events, and emits rich completion states (success, partial success, abort, or failure) before shutting everything down cleanly.【F:api/core/workflow/graph_engine/graph_engine.py†L229-L339】
- The Redis-backed command channel enables distributed abort commands by draining and decoding serialized entries from a queue that supports TTL-based expiry.【F:api/core/workflow/graph_engine/command_channels/redis_channel.py†L1-L114】
- `CommandProcessor` polls command channels, dispatching to registered handlers while isolating failures, which keeps control-plane logic modular.【F:api/core/workflow/graph_engine/command_processing/command_processor.py†L1-L79】
- A simplified worker pool now unifies scaling logic, creating or retiring workers based on queue depth, worker activity, and configurable thresholds so the engine adapts to load automatically.【F:api/core/workflow/graph_engine/worker_management/worker_pool.py†L1-L291】

## Frontend workflow canvas
- The client-side `Workflow` component wires React Flow with project-specific nodes, edges, and controls, synchronizing canvas size, keyboard shortcuts, tool fetching, and viewport persistence while reacting to shared event bus updates.【F:web/app/components/workflow/index.tsx†L1-L433】
- React Flow configuration disables default hotkeys, toggles interactions based on read-only state, and applies custom connection lines and backgrounds to match the new canvas experience.【F:web/app/components/workflow/index.tsx†L381-L424】
- The default export wraps the canvas with providers for history, dataset details, and hook stores so undo/redo and context data remain scoped per workflow.【F:web/app/components/workflow/index.tsx†L436-L474】
- Workflow history is backed by a Zustand + Zundo store that snapshots node/edge state, resets selections when rewinding, and exposes shortcut toggles for undo/redo integration.【F:web/app/components/workflow/workflow-history-store.tsx†L1-L125】

## Docker build troubleshooting
- To rebuild just the retriever service when a full multi-service compose build fails, run:
  ```bash
  docker compose -f docker/docker-compose.yaml -f docker/docker-compose.v2.yaml build retriever
  ```
