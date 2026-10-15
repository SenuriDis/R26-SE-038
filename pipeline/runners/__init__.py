"""
Scripts executed *inside* a component's own Python environment.

Components pin conflicting dependencies (C2 wants numpy 1.26.4, C3's env is
built on chromadb and needs a much newer numpy), and several of them import
themselves under the same top-level names (`src`, `utils`, `models`). Running
each one as a subprocess with its own interpreter keeps both problems out of
the orchestrator.

Each runner reads one JSON artifact and writes another. Nothing else crosses
the boundary.
"""
