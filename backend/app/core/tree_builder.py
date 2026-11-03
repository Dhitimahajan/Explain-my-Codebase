import re
from typing import Dict, List, Any, Optional

MODULE_PATTERNS = [
    ("Tests", r"(^tests?\/|\/tests?\/|^__tests__\/|\/test_[^\/]+$|\/_test\.[^\/]+$|\.test\.[^\/]+$|\.spec\.[^\/]+$|cypress|playwright|jest|unittest)"),
    ("Config & DevOps", r"(docker|compose|ci|cd|github\/workflows|k8s|kubernetes|terraform|dockerfile|\.env\.|\.ya?ml$|\.toml$)"),
    ("Frontend UI", r"(frontend|ui|components?|pages?|views?|templates?|layouts?|hooks?|styles?|public|assets|client|\.tsx?$|\.jsx?$|\.vue$|\.svelte$|\.html$|\.s?css$)"),
    ("Auth & Security", r"(auth|jwt|token|session|oauth|passport|security|permission|guard|login|signup|password|crypto)"),
    ("Database & Models", r"(db|database|models?|schemas?|entities|migrations?|prisma|alembic|seeds?|repositor(y|ies)|sql|orm|query)"),
    ("API & Routes", r"(api|routes?|routers?|controllers?|endpoints?|handlers?|trpc|graphql)"),
    ("Services & Utils", r"(services?|utils?|helpers?|lib|clients?|integrations?|workers?|jobs?|tasks?|adapters?|middleware)"),
]

MODULE_ICONS = {
    "Auth & Security": "🔐",
    "Database & Models": "🗄️",
    "API & Routes": "🔌",
    "Frontend UI": "🌐",
    "Services & Utils": "⚙️",
    "Tests": "🧪",
    "Config & DevOps": "🛠️",
    "General / Core": "📦",
}


def classify_module(path: str, file_name: str = "") -> str:
    """Classifies a file or folder into an architectural category."""
    lower_path = path.lower().replace("\\", "/")
    lower_name = file_name.lower()
    full_search = f"{lower_path}/{lower_name}" if lower_name else lower_path

    for category, pattern in MODULE_PATTERNS:
        if re.search(pattern, full_search):
            return category

    return "General / Core"


def build_file_tree(code_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a recursive, hierarchical tree structure from a flat list of files.
    """
    root: Dict[str, Any] = {
        "id": "root",
        "name": "Project Root",
        "path": "",
        "type": "directory",
        "module": "General / Core",
        "icon": "📁",
        "loc": 0,
        "children": {},
    }

    for file in code_files:
        path_parts = file["path"].split("/")
        current = root
        current["loc"] += file["loc"]

        accum_path = ""
        for i, part in enumerate(path_parts):
            accum_path = f"{accum_path}/{part}" if accum_path else part
            is_file = (i == len(path_parts) - 1)

            if is_file:
                module = classify_module(file["path"], file["name"])
                icon = MODULE_ICONS.get(module, "📄")

                current["children"][part] = {
                    "id": accum_path,
                    "name": file["name"],
                    "path": file["path"],
                    "type": "file",
                    "module": module,
                    "icon": icon,
                    "loc": file["loc"],
                    "size_kb": file["size_kb"],
                    "language": file["language"],
                }
            else:
                if part not in current["children"]:
                    dir_module = classify_module(accum_path, part)
                    current["children"][part] = {
                        "id": accum_path,
                        "name": part,
                        "path": accum_path,
                        "type": "directory",
                        "module": dir_module,
                        "icon": "📁",
                        "loc": 0,
                        "children": {},
                    }
                current = current["children"][part]
                current["loc"] += file["loc"]

    def convert_dict_to_list(node: Dict[str, Any]) -> Dict[str, Any]:
        if node.get("type") == "directory":
            children_dict = node.pop("children", {})
            sorted_children = sorted(
                children_dict.values(),
                key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower())
            )
            node["children"] = [convert_dict_to_list(child) for child in sorted_children]
        return node

    return convert_dict_to_list(root)


def extract_architecture_modules(code_files: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Groups repository files by architectural module category with key metrics.
    """
    modules: Dict[str, List[Dict[str, Any]]] = {}

    for file in code_files:
        cat = classify_module(file["path"], file["name"])
        if cat not in modules:
            modules[cat] = []
        modules[cat].append({
            "path": file["path"],
            "name": file["name"],
            "loc": file["loc"],
            "language": file["language"],
        })

    # Sort files inside modules by LOC descending
    for cat in modules:
        modules[cat].sort(key=lambda x: x["loc"], reverse=True)

    return modules
