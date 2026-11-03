import json
import re
from typing import List, Dict, Any, Optional

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None

from app.config import ANTHROPIC_API_KEY, OPENAI_API_KEY


class LLMService:
    """
    Advanced Architecture Synthesizer and Codebase Copilot.
    Generates deeply detailed, project-specific multi-layer system diagrams and sequence flows.
    """

    def __init__(self):
        self.anthropic_client = (
            anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            if (ANTHROPIC_API_KEY and anthropic)
            else None
        )
        self.openai_client = (
            openai.OpenAI(api_key=OPENAI_API_KEY)
            if (OPENAI_API_KEY and openai)
            else None
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.anthropic_client or self.openai_client)

    @property
    def active_provider(self) -> str:
        if self.anthropic_client:
            return "Claude 3.5 Sonnet (Anthropic)"
        if self.openai_client:
            return "GPT-4o (OpenAI)"
        return "Local Architectural Engine (Active)"

    def generate_architecture_overview(
        self,
        repo_name: str,
        modules: Dict[str, List[Dict[str, Any]]],
        total_loc: int,
        languages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates comprehensive multi-mode architecture overviews,
        dynamic subgraphs with actual file paths, and sequence execution traces.
        """
        all_files = [f for files in modules.values() for f in files]
        all_paths_lower = [f["path"].lower() for f in all_files]

        # 1. Project Type & Archetype Detection
        is_chrome_ext = any("manifest.json" in p or "popup.html" in p or "background.js" in p or "content.js" in p for p in all_paths_lower)
        is_fastapi = any("fastapi" in p or "main.py" in p or "uvicorn" in p for p in all_paths_lower)
        is_express = any("express" in p or "server.js" in p or "app.js" in p or "routes" in p for p in all_paths_lower) and any(".js" in p or ".ts" in p for p in all_paths_lower)
        is_react_next = any("next.config" in p or "pages" in p or "components" in p or ".tsx" in p or ".jsx" in p for p in all_paths_lower)
        is_django = any("manage.py" in p or "settings.py" in p or "urls.py" in p for p in all_paths_lower)

        top_langs = [l["language"] for l in languages[:4]]
        tech_stack = top_langs.copy()

        # Archetype 1: Chrome Extension (Manifest V3 / V2)
        if is_chrome_ext:
            tech_stack.extend(["Chrome Extension (MV3)", "DOM Messaging", "Chrome APIs"])
            if any(".ts" in p for p in all_paths_lower):
                tech_stack.append("TypeScript")

            popup_files = [f["path"] for f in all_files if "popup" in f["path"].lower()]
            bg_files = [f["path"] for f in all_files if "background" in f["path"].lower() or "service_worker" in f["path"].lower()]
            content_files = [f["path"] for f in all_files if "content" in f["path"].lower()]
            option_files = [f["path"] for f in all_files if "option" in f["path"].lower() or "setting" in f["path"].lower()]

            p_node = popup_files[0] if popup_files else "popup.html / popup.js"
            bg_node = bg_files[0] if bg_files else "background.js (Service Worker)"
            c_node = content_files[0] if content_files else "content.js (DOM Script)"

            flowchart = f"""graph TD
    subgraph BrowserUI ["🖥️ Browser & Tab Layer"]
        User(["👤 User Interaction"]) --> Popup["📱 Popup Interface<br/><code>{p_node}</code>"]
        PageDOM["🌐 Active Webpage DOM"] <--> Content["💉 Content Script<br/><code>{c_node}</code>"]
    end

    subgraph Runtime ["⚙️ Extension Background Core"]
        Popup -->|chrome.runtime.sendMessage| Background["⚡ Background Service Worker<br/><code>{bg_node}</code>"]
        Content -->|DOM Events & Extraction| Background
        Background <--> Storage[("💾 chrome.storage<br/>(Local & Sync Cache)")]
    end

    subgraph External ["☁️ External Network Layer"]
        Background -.->|fetch API / Webhooks| ExtAPI["🌐 Remote APIs / Backend Services"]
    end

    classDef ui fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e0e7ff;
    classDef core fill:#14532d,stroke:#22c55e,stroke-width:2px,color:#dcfce7;
    classDef ext fill:#3b0764,stroke:#a855f7,stroke-width:2px,color:#f3e8ff;
    classDef store fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fef3c7;

    class Popup,PageDOM,Content ui;
    class Background core;
    class Storage store;
    class ExtAPI ext;
"""

            sequence = f"""sequenceDiagram
    autonumber
    actor User as 👤 User
    participant Popup as 📱 {p_node.split('/')[-1]}
    participant BG as ⚡ {bg_node.split('/')[-1]}
    participant Content as 💉 {c_node.split('/')[-1]}
    participant DOM as 🌐 Webpage DOM
    participant Storage as 💾 chrome.storage

    User->>Popup: Open Extension / Trigger Action
    Popup->>BG: chrome.runtime.sendMessage(action)
    BG->>Storage: Read Cached Preferences / Tokens
    Storage-->>BG: Return Cached State
    BG->>Content: chrome.tabs.sendMessage(tabId, payload)
    Content->>DOM: Query & Modify Target Elements
    DOM-->>Content: Return Extracted Data
    Content-->>BG: Send Parsed Results
    BG-->>Popup: Response with Data Status
    Popup-->>User: Render Results in Popup UI
"""

            return {
                "title": f"{repo_name} — Chrome Extension Architecture",
                "pattern": "Chrome Extension (Manifest V3 Architecture)",
                "summary": (
                    f"**{repo_name}** is built as a modular **Browser Extension** comprising a Popup UI layer, "
                    f"Background Service Worker orchestrator, and Content Script DOM injectors. "
                    f"Components communicate asynchronously via the `chrome.runtime` and `chrome.tabs` messaging bus."
                ),
                "tech_stack": list(set(tech_stack)),
                "key_layers": [
                    {"layer": "Popup UI Layer", "description": f"User interface rendering extension views. Core files: {', '.join(popup_files[:3]) or 'popup.html'}"},
                    {"layer": "Background Service Worker", "description": f"Event listener and lifecycle orchestrator. Core files: {', '.join(bg_files[:2]) or 'background.js'}"},
                    {"layer": "Content Scripts", "description": f"Isolated scripts running directly inside web pages to extract or alter DOM. Core files: {', '.join(content_files[:2]) or 'content.js'}"},
                    {"layer": "Storage & Chrome APIs", "description": "Persistent key-value cache utilizing chrome.storage and browser permission APIs."}
                ],
                "mermaid_diagram": flowchart,
                "sequence_diagram": sequence,
            }

        # Archetype 2: Dynamic Layered Architecture (FastAPI, Express, Django, Fullstack, or General)
        # Extract top files from each detected module
        module_subgraphs = []
        class_assignments = []
        connections = []

        color_map = {
            "Frontend UI": ("#1e1b4b", "#6366f1", "ui"),
            "API & Routes": ("#083344", "#06b6d4", "api"),
            "Auth & Security": ("#451a03", "#f59e0b", "auth"),
            "Database & Models": ("#064e3b", "#10b981", "db"),
            "Services & Utils": ("#3b0764", "#a855f7", "serv"),
            "Config & DevOps": ("#334155", "#64748b", "conf"),
            "General / Core": ("#182030", "#475569", "core"),
        }

        # Identify existing layers
        active_modules = [m for m, files in modules.items() if files and m != "Tests"]

        for idx, mod_name in enumerate(active_modules):
            files = modules[mod_name][:4]  # top 4 files
            clean_mod_id = f"mod_{idx}"
            file_nodes = []
            for f_idx, f in enumerate(files):
                node_id = f"f_{idx}_{f_idx}"
                clean_name = f["name"].replace('"', '')
                loc = f["loc"]
                file_nodes.append(f'        {node_id}["📄 {clean_name}<br/><code>{loc} LOC</code>"]')

            nodes_str = "\n".join(file_nodes)
            module_subgraphs.append(f"""    subgraph {clean_mod_id} ["{mod_name} ({len(modules[mod_name])} files)"]
{nodes_str}
    end""")

        # Add logical connections between subgraphs
        has_ui = "Frontend UI" in modules and modules["Frontend UI"]
        has_api = "API & Routes" in modules and modules["API & Routes"]
        has_auth = "Auth & Security" in modules and modules["Auth & Security"]
        has_serv = "Services & Utils" in modules and modules["Services & Utils"]
        has_db = "Database & Models" in modules and modules["Database & Models"]

        flowchart_lines = ["graph TD", "    Client([\"🌐 Client / External Request\"])"]

        if has_ui:
            flowchart_lines.append("    Client --> f_0_0")
            if has_api:
                api_idx = active_modules.index("API & Routes") if "API & Routes" in active_modules else 0
                flowchart_lines.append(f"    f_0_0 -->|API Request| f_{api_idx}_0")
        elif has_api:
            api_idx = active_modules.index("API & Routes")
            flowchart_lines.append(f"    Client -->|HTTP / JSON| f_{api_idx}_0")

        if has_auth and has_api:
            auth_idx = active_modules.index("Auth & Security")
            api_idx = active_modules.index("API & Routes")
            flowchart_lines.append(f"    f_{api_idx}_0 -->|Verify Token / Session| f_{auth_idx}_0")

        if has_serv and has_api:
            api_idx = active_modules.index("API & Routes")
            serv_idx = active_modules.index("Services & Utils")
            flowchart_lines.append(f"    f_{api_idx}_0 -->|Dispatch Handler| f_{serv_idx}_0")

        if has_db:
            db_idx = active_modules.index("Database & Models")
            if has_serv:
                serv_idx = active_modules.index("Services & Utils")
                flowchart_lines.append(f"    f_{serv_idx}_0 -->|Query / Mutate| f_{db_idx}_0")
            elif has_api:
                api_idx = active_modules.index("API & Routes")
                flowchart_lines.append(f"    f_{api_idx}_0 -->|ORM / SQL Query| f_{db_idx}_0")

        flowchart_body = "\n\n".join(module_subgraphs)
        full_flowchart = f"{chr(10).join(flowchart_lines)}\n\n{flowchart_body}\n"

        # Build Sequence Trace
        first_api_file = modules.get("API & Routes", [{}])[0].get("name", "Router")
        first_auth_file = modules.get("Auth & Security", [{}])[0].get("name", "AuthGuard")
        first_serv_file = modules.get("Services & Utils", [{}])[0].get("name", "ServiceLogic")
        first_db_file = modules.get("Database & Models", [{}])[0].get("name", "DatabaseModel")

        sequence = f"""sequenceDiagram
    autonumber
    actor User as 👤 Client / User
    participant Router as 🔌 {first_api_file}
    participant Auth as 🔐 {first_auth_file}
    participant Service as ⚙️ {first_serv_file}
    participant DB as 🗄️ {first_db_file}

    User->>Router: Incoming Request (Headers + Body)
    Router->>Auth: Validate Credentials & Permissions
    alt Valid Credentials
        Auth-->>Router: Authorized (User Context)
        Router->>Service: Execute Business Logic
        Service->>DB: Execute Query / Model Mutation
        DB-->>Service: Database Records Returned
        Service-->>Router: Formatted Response DTO
        Router-->>User: 200 OK (JSON Result)
    else Invalid Credentials
        Auth-->>Router: 401 Unauthorized
        Router-->>User: 401 / 403 Forbidden Error
    end
"""

        arch_pattern = "Layered Clean Architecture"
        if is_fastapi:
            arch_pattern = "FastAPI Asynchronous Microservice"
            tech_stack.append("FastAPI")
        elif is_express:
            arch_pattern = "Node.js Express REST API"
            tech_stack.append("Express.js")
        elif is_react_next:
            arch_pattern = "Fullstack React / Next.js Architecture"
            tech_stack.append("React")

        return {
            "title": f"{repo_name} — System Architecture & Data Flow",
            "pattern": arch_pattern,
            "summary": (
                f"**{repo_name}** is engineered following **{arch_pattern}** principles across {len(active_modules)} distinct layers. "
                f"The core implementation spans {total_loc:,} lines of code primarily in {', '.join(top_langs)}."
            ),
            "tech_stack": list(set(tech_stack)),
            "key_layers": [
                {
                    "layer": cat,
                    "description": f"Contains {len(files)} files managing {cat.lower()}. Key modules: {', '.join([f['name'] for f in files[:3]])}"
                }
                for cat, files in modules.items() if files
            ],
            "mermaid_diagram": full_flowchart,
            "sequence_diagram": sequence,
        }

    def answer_query(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        repo_name: str,
        modules: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Synthesizes an answer to developer questions with step-by-step flow and citations.
        """
        context_snippets = []
        citations = []
        for i, chunk in enumerate(retrieved_chunks):
            path = chunk["file_path"]
            s_line = chunk["start_line"]
            e_line = chunk["end_line"]
            symbol = chunk.get("symbol", "")
            citations.append({
                "file_path": path,
                "start_line": s_line,
                "end_line": e_line,
                "symbol": symbol,
                "preview": f"{path}:{s_line}-{e_line}",
            })
            context_snippets.append(
                f"--- [Snippet {i+1}] {path} (Lines {s_line}-{e_line}) {f'[{symbol}]' if symbol else ''} ---\n{chunk['content']}"
            )

        context_str = "\n\n".join(context_snippets)

        system_prompt = f"""You are an expert Senior Staff Software Engineer and Codebase Guide for '{repo_name}'.
Explain the code flow accurately based on the provided context chunks.

Formatting Rules:
1. **Direct Answer**: Provide a concise answer identifying which module is responsible.
2. **Step-by-Step Flow**: Break down the control flow across files from entry to output.
3. **Citations**: Whenever referencing code, use `[path:start_line-end_line]` (e.g. `[src/auth/jwt.py:12-45]`).
4. **Flowchart**: Include a ```mermaid sequenceDiagram or graph TD block.
"""

        # 1. Try Anthropic Claude 3.5 Sonnet if configured
        if self.anthropic_client:
            try:
                resp = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": f"Retrieved Chunks:\n{context_str}\n\nQuestion: {query}"}],
                    timeout=15.0
                )
                return {
                    "answer": resp.content[0].text,
                    "citations": citations,
                    "provider": "Claude 3.5 Sonnet",
                }
            except Exception:
                pass

        # 2. Try OpenAI GPT-4o if configured
        if self.openai_client:
            try:
                completion = self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Retrieved Chunks:\n{context_str}\n\nQuestion: {query}"}
                    ],
                    max_tokens=2000,
                    timeout=15.0
                )
                return {
                    "answer": completion.choices[0].message.content,
                    "citations": citations,
                    "provider": "GPT-4o (OpenAI)",
                }
            except Exception:
                pass

        return self._heuristic_answer(query, retrieved_chunks, repo_name, citations)

    def _heuristic_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        repo_name: str,
        citations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates a structured, file-aware explanation with diagram."""
        if not retrieved_chunks:
            return {
                "answer": (
                    f"### 🔍 Analysis for: '{query}'\n\n"
                    f"No direct code matches were found in `{repo_name}` for this search term. "
                    "Try querying specific architectural modules like **authentication**, **API routes**, **models**, or **middleware**."
                ),
                "citations": [],
                "provider": "Local Architectural Engine",
            }

        top_chunk = retrieved_chunks[0]
        files_mentioned = list(dict.fromkeys([c["file_path"] for c in retrieved_chunks]))
        top_filename = top_chunk['file_path'].split('/')[-1]
        second_filename = files_mentioned[1].split('/')[-1] if len(files_mentioned) > 1 else "Handler"

        file_bullets = []
        for f in files_mentioned[:4]:
            matching = [c for c in retrieved_chunks if c['file_path'] == f]
            if matching:
                s = matching[0]['start_line']
                e = matching[0]['end_line']
                file_bullets.append(f"- 📄 `[{f}:{s}-{e}]`")

        answer_md = f"""### 🎯 Architectural Overview

In **`{repo_name}`**, logic relevant to **"{query}"** is anchored in these primary files:
{chr(10).join(file_bullets)}

---

### 📜 Execution & Control Flow

1. **Entry Point & Initialization**:
   Incoming execution flows through `[{top_chunk['file_path']}:{top_chunk['start_line']}-{top_chunk['end_line']}]` ({top_chunk.get('symbol') or 'Primary Module'}).
2. **State & Dispatch**:
   Parameters and handlers coordinate across `{files_mentioned[1] if len(files_mentioned) > 1 else files_mentioned[0]}` to execute the relevant business operations.

---

### 📊 Visual Execution Trace

```mermaid
sequenceDiagram
    autonumber
    actor Client as 👤 Client / Caller
    participant Handler as 📄 {top_filename}
    participant Core as ⚙️ {second_filename}
    
    Client->>Handler: Trigger operation ("{query}")
    Handler->>Core: Forward context & dispatch logic
    Core-->>Handler: Return execution response
    Handler-->>Client: Final result & status
```
"""

        return {
            "answer": answer_md,
            "citations": citations,
            "provider": "Local Architectural Engine",
        }

    def suggest_questions(self, modules: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Returns intelligent starter questions based on detected modules."""
        questions = []
        all_paths = [f["path"].lower() for files in modules.values() for f in files]
        
        if any("manifest.json" in p or "popup" in p for p in all_paths):
            questions.append("How do the popup UI and background service worker communicate?")
            questions.append("Where are content scripts injected and what DOM elements do they touch?")
            questions.append("How is extension storage and local state managed?")
        
        if modules.get("Auth & Security"):
            questions.append("Where does user authentication and authorization happen?")
        if modules.get("API & Routes"):
            questions.append("How are API routes and endpoints structured?")
        if modules.get("Database & Models"):
            questions.append("What database models and schemas exist?")
        if modules.get("Frontend UI"):
            questions.append("How is the frontend UI and component tree organized?")

        if len(questions) < 3:
            questions.extend([
                "Explain the overall request lifecycle in this application",
                "Where are errors and exceptions handled?",
                "What are the main entry points of the application?"
            ])

        return questions[:5]


# Singleton instance
llm_service = LLMService()
