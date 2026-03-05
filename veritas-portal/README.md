# Veritas Unified Portal (veritas-cli)

## 🏛️ The Entry Point for Veritas Suite
The `veritas` command is the central orchestrator for the entire Veritas Academic Research Suite. It provides a beautiful, high-fidelity human-centric interface to manage **Veritas-Core**, **Textus-Transparens (TT)**, and **GP-Viz**.

## 🚀 Key Features
- **Unified Dashboard**: `veritas status` gives you a live overview of all services.
- **Suite-Wide Health**: `veritas doctor` performs automated diagnostics on databases, models, and networking.
- **Interactive Research Chat**: `veritas core chat` provides a high-quality command-line dialogue window with RAG support.
- **Unified UI Standard**: All outputs follow the "TT Standard" (Rich tables, colored indicators, and cognitive hints).
- **Service Orchestration**: One-click startup for Docker containers and background daemons.

## 🛠️ Usage
Launch the portal by typing:
```cmd
veritas
```

### Main Commands:
- `veritas status [--live]`: View system health and resource usage.
- `veritas doctor`: Run automated diagnostics and repair hints.
- `veritas core ...`: Manage sessions, artifacts, personas, and chats.
- `veritas tt ...`: Launch and manage qualitative analysis projects.
- `veritas viz ...`: Control the 3D visualization engine and data ingestion.

## 🔧 Installation
Currently maintained at: `C:\Users\thene\projects\veritas-cli`.
Ensure the `.venv` is activated before manual script execution, or use the provided `veritas.bat` wrapper.
