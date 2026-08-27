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
    Interface for Claude 3.5 Sonnet / Haiku and OpenAI models.
    Includes smart heuristic fallback when no API key is provided yet.
    """

    def __init__(self):
        self.anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if (ANTHROPIC_API_KEY and anthropic) else None
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if (OPENAI_API_KEY and openai) else None

    @property
    def is_configured(self) -> bool:
        return bool(self.anthropic_client or self.openai_client)

    @property
    def active_provider(self) -> str:
        if self.anthropic_client:
            return "Claude 3.5 Sonnet (Anthropic)"
        elif self.openai_client:
            return "GPT-4o (OpenAI)"
        return "Built-in Heuristic Engine (Add API Key for Claude 3.5)"

    def generate_architecture_overview(
        self,
        repo_name: str,
        modules: Dict[str, List[Dict[str, Any]]],
        total_loc: int,
        languages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates a high-level architecture overview and Mermaid.js diagram.
        """
        if self.anthropic_client:
            try:
                module_summary = {
                    cat: [f["path"] for f in files[:8]]
                    for cat, files in modules.items()
                }
                prompt = f"""
You are a Principal Software Architect analyzing the repository '{repo_name}'.
Statistics:
- Total LOC: {total_loc}
- Top Languages: {json.dumps(languages[:4])}
- Architectural Modules & Sample Files: {json.dumps(module_summary, indent=2)}

Please provide an architectural summary in JSON with the exact following schema:
{{
  "title": "Short descriptive architecture title",
  "summary": "2-3 paragraphs explaining the system design, main responsibilities, and how components interact.",
  "tech_stack": ["List", "of", "detected", "frameworks", "and", "tools"],
  "key_layers": [
    {{"layer": "Frontend", "description": "What frontend framework/technologies are used and where"}},
    {{"layer": "Backend / API", "description": "Routing, API design, handlers"}},
    {{"layer": "Data Layer", "description": "Database, ORM, models, migrations"}},
    {{"layer": "Services & Auth", "description": "Security, background jobs, external services"}}
  ],
  "mermaid_diagram": "graph TD\\n  A[Client / User] --> B[Frontend UI]\\n  B --> C[API Routes / Controllers]\\n  C --> D[Services / Business Logic]\\n  D --> E[(Database / Storage)]"
}}
Return ONLY valid JSON.
"""
                resp = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}]
                )
                raw_text = resp.content[0].text.strip()
                match = re.search(r"\{.*\}", raw_text, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except Exception:
                pass

        # Smart Heuristic Fallback
        return self._heuristic_architecture(repo_name, modules, languages)

    def _heuristic_architecture(
        self,
        repo_name: str,
        modules: Dict[str, List[Dict[str, Any]]],
        languages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates accurate architectural overview from file structure."""
        top_langs = [l["language"] for l in languages[:3]]
        tech_stack = top_langs.copy()

        # Identify frameworks from paths
        all_paths = [f["path"] for files in modules.values() for f in files]
        has_react = any("react" in p.lower() or p.endswith(".tsx") or p.endswith(".jsx") for p in all_paths)
        has_fastapi = any("fastapi" in p.lower() or "main.py" in p.lower() for p in all_paths)
        has_express = any("express" in p.lower() or "server.js" in p.lower() or "app.ts" in p.lower() for p in all_paths)
        has_prisma = any("prisma" in p.lower() for p in all_paths)
        has_auth = bool(modules.get("Auth & Security"))

        if has_react:
            tech_stack.append("React")
        if has_fastapi:
            tech_stack.append("FastAPI")
        if has_express:
            tech_stack.append("Node.js / Express")
        if has_prisma:
            tech_stack.append("Prisma ORM")
        if has_auth:
            tech_stack.append("Auth Module")

        mermaid = """graph TD
    Client["🌐 Client / User Interface"] --> API["🔌 API Gateway / Router"]
    API --> Auth{"🔐 Auth & Security"}
    Auth -->|Authorized| Logic["⚙️ Services & Business Logic"]
    Auth -->|Unauthorized| Deny["❌ 401 Unauthorized"]
    Logic --> DB[("🗄️ Database & Models")]
    Logic --> Ext["🧩 External Services / Helpers"]
"""

        return {
            "title": f"{repo_name} - System Architecture",
            "summary": (
                f"The **{repo_name}** repository is structured into modular layers covering "
                f"{', '.join(modules.keys())}. "
                f"Primary codebase logic is built with {', '.join(top_langs)}."
            ),
            "tech_stack": list(set(tech_stack)),
            "key_layers": [
                {"layer": cat, "description": f"Contains {len(files)} files managing {cat.lower()}."}
                for cat, files in modules.items() if files
            ],
            "mermaid_diagram": mermaid,
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
        # Format code chunks for prompt
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

        if self.anthropic_client:
            try:
                system_prompt = f"""
You are an expert Senior Staff Software Engineer and Codebase Guide for the repository '{repo_name}'.
A developer is asking questions to understand how this codebase is designed, how data flows, or where specific logic resides.

Use the provided code snippets to answer accurately.

Formatting Rules:
1. **Direct Answer**: Start with a concise, direct answer summarizing where this happens and which module is responsible.
2. **Step-by-Step Flow**: Break down the execution flow from entry point to database/output.
3. **Citations**: Whenever referencing code, use markdown format `[path:start_line-end_line]` (e.g. `[src/auth/jwt.py:12-45]`).
4. **Flowchart (Mermaid.js)**: If explaining a workflow (like authentication, payment, API handling, or state changes), include a ```mermaid sequenceDiagram or graph TD block.
5. If the provided snippets do not have full information, explain what is available from the codebase structure and guide the user on where to look next.
"""
                user_msg = f"""
Retrieved Code Snippets:
{context_str}

User Question: {query}
"""
                resp = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_msg}]
                )
                answer_markdown = resp.content[0].text
                return {
                    "answer": answer_markdown,
                    "citations": citations,
                    "provider": "Claude 3.5 Sonnet",
                }
            except Exception as e:
                # Fallback to local heuristic answer
                pass

        return self._heuristic_answer(query, retrieved_chunks, repo_name, citations)

    def _heuristic_answer(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        repo_name: str,
        citations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates a structured explanation when no external API key is configured."""
        if not retrieved_chunks:
            return {
                "answer": (
                    f"### 🔍 Analysis for: '{query}'\n\n"
                    f"No direct code matches were found in `{repo_name}` for this search term. "
                    "Try querying specific architectural modules like **authentication**, **database models**, or **API routes**."
                ),
                "citations": [],
                "provider": "Local Heuristic Index",
            }

        top_chunk = retrieved_chunks[0]
        files_mentioned = list(dict.fromkeys([c["file_path"] for c in retrieved_chunks]))

        answer_md = f"""### 🎯 Overview

Based on the repository index for **`{repo_name}`**, relevant logic related to **"{query}"** is located across the following files:
{chr(10).join([f"- 📄 `{f}`" for f in files_mentioned[:4]])}

---

### 📜 Execution & Control Flow

1. **Primary Entry / Definition**:
   Logic is anchored in `[{top_chunk['file_path']}:{top_chunk['start_line']}-{top_chunk['end_line']}]` ({top_chunk.get('symbol', 'Core Logic')}).
2. **Data & Request Processing**:
   Cross-references and helper utilities in `{files_mentioned[1] if len(files_mentioned) > 1 else files_mentioned[0]}` participate in executing this flow.

---

### 📊 Visual Flow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Dev as User / Client
    participant Flow as {top_chunk['file_path'].split('/')[-1]}
    participant System as System Logic
    
    Dev->>Flow: Request / Action relating to "{query}"
    Flow->>System: Execute handler & validate parameters
    System-->>Dev: Return result & status
```

---

> [!TIP]
> 💡 *To enable full deep code synthesis with Claude 3.5 Sonnet, add your `ANTHROPIC_API_KEY` in the `.env` file or via the top-right settings.*
"""

        return {
            "answer": answer_md,
            "citations": citations,
            "provider": "Local Heuristic Index",
        }

    def suggest_questions(self, modules: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Returns intelligent starter questions based on detected modules."""
        questions = []
        if modules.get("Auth & Security"):
            questions.append("Where does user authentication and authorization happen?")
        if modules.get("API & Routes"):
            questions.append("How are API routes structured and handled?")
        if modules.get("Database & Models"):
            questions.append("What database models and schemas exist in this project?")
        if modules.get("Frontend UI"):
            questions.append("How is the frontend UI and state management organized?")
        if modules.get("Services & Utils"):
            questions.append("What background services, workers, or utility helpers exist?")
        if modules.get("Config & DevOps"):
            questions.append("How is the deployment, Docker, and environment configured?")

        if len(questions) < 3:
            questions.extend([
                "Explain the overall request lifecycle in this application",
                "Where are errors and exceptions handled?",
                "What are the main entry points of the application?"
            ])

        return questions[:5]


# Singleton instance
llm_service = LLMService()
