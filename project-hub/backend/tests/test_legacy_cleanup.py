"""Provas estruturais focadas contra a reintrodução do legado removido neste GOAL."""

import ast
import re
from pathlib import Path

from app.core import auth, http_client
from app.main import app
from app.services.n8n_service import N8NService
from app.services.whatsapp_client import WhatsAppClient
from app.services import whatsapp_service


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_APP = Path(__file__).resolve().parents[1] / "app"
FRONTEND_SRC = REPO_ROOT / "src"


def _frontend_runtime_source() -> str:
    assert FRONTEND_SRC.is_dir(), f"Frontend source directory not found: {FRONTEND_SRC}"
    sources = []
    for path in sorted(FRONTEND_SRC.rglob("*")):
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        relative = path.relative_to(FRONTEND_SRC)
        if any(part in {"test", "tests", "__tests__"} for part in relative.parts):
            continue
        if re.search(r"\.(?:test|spec)\.[^.]+$", path.name):
            continue
        # Conteúdo bruto evita que um parser manual incompleto esconda código executável.
        sources.append(path.read_text(encoding="utf-8"))
    assert sources, f"No frontend runtime source found under: {FRONTEND_SRC}"
    return "\n".join(sources)


def _executable_python_strings(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstring_nodes: set[int] = set()
    documented_nodes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, documented_nodes) or not node.body:
            continue
        first_statement = node.body[0]
        if (
            isinstance(first_statement, ast.Expr)
            and isinstance(first_statement.value, ast.Constant)
            and isinstance(first_statement.value.value, str)
        ):
            docstring_nodes.add(id(first_statement.value))

    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstring_nodes
    }


def test_removed_compatibility_layers_and_helpers_stay_absent():
    assert not (BACKEND_APP / "services" / "identity_service.py").exists()

    imported_legacy_module = []
    for source_root in (BACKEND_APP, BACKEND_APP.parent / "tests"):
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(alias.name == "app.services.identity_service" for alias in node.names):
                        imported_legacy_module.append(path)
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "app.services.identity_service" or (
                        node.module == "app.services"
                        and any(alias.name == "identity_service" for alias in node.names)
                    ):
                        imported_legacy_module.append(path)
    assert not imported_legacy_module

    for helper in {"get_oauth_token", "check_token_validity", "invalidate_token"}:
        assert not hasattr(whatsapp_service, helper)
    for helper in {"instagram_login", "instagram_logout"}:
        assert not hasattr(WhatsAppClient, helper)

    assert not hasattr(http_client, "EncryptedAsyncClient")
    assert not hasattr(auth, "check_project_create_permission")
    assert not hasattr(auth, "check_project_edit_permission")
    assert not hasattr(N8NService, "get_chat_history")
    assert "refreshAuthTokenPreventively" not in _frontend_runtime_source()


def test_dead_instagram_proxy_routes_and_frontend_helpers_stay_absent():
    route_paths = {getattr(route, "path", "") for route in app.routes}
    assert not any(path.startswith("/api/v1/whatsapp/instagram/") for path in route_paths)

    runtime_source = _frontend_runtime_source()
    assert "/whatsapp/instagram/" not in runtime_source
    assert not re.search(
        r"\b(?:loginInstagramProxy|logoutInstagramProxy|handleInstagramLogin|"
        r"handleDisconnectInstagram|LogOutInstagram)\b",
        runtime_source,
    )


def test_whatsapp_client_executable_code_has_no_forbidden_legacy_headers():
    executable_strings = {
        value.casefold()
        for value in _executable_python_strings(BACKEND_APP / "services" / "whatsapp_client.py")
    }
    forbidden_headers = {
        "x-master-api-key",
        "x-session-token",
        "x-tenant-id",
        "x-user-id",
        "authtoken",
    }
    assert executable_strings.isdisjoint(forbidden_headers)


def test_whatsapp_client_uses_only_the_frozen_scope_set():
    tree = ast.parse(
        (BACKEND_APP / "services" / "whatsapp_client.py").read_text(encoding="utf-8")
    )
    declared_scopes = {
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "scope"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    }

    assert declared_scopes == {
        "whatsapp:sessions:read",
        "whatsapp:sessions:create",
        "whatsapp:sessions:write",
        "whatsapp:sessions:delete",
        "whatsapp:messages:send",
    }


def test_identity_client_is_the_only_m2m_authority_and_has_no_persistence_imports():
    identity_path = BACKEND_APP / "services" / "identity_client.py"
    identity_tree = ast.parse(identity_path.read_text(encoding="utf-8"))
    imported_modules = {
        node.module
        for node in ast.walk(identity_tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(identity_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    forbidden_persistence_imports = ("sqlalchemy", "app.models", "app.repositories")
    assert not any(
        module.startswith(forbidden_persistence_imports)
        for module in imported_modules
    )

    production_importers = set()
    for path in BACKEND_APP.rglob("*.py"):
        if path == identity_path:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports_identity_client = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                alias.name == "app.services.identity_client" for alias in node.names
            ):
                imports_identity_client = True
            elif isinstance(node, ast.ImportFrom) and (
                node.module == "app.services.identity_client"
                or (
                    node.module == "app.services"
                    and any(alias.name == "identity_client" for alias in node.names)
                )
                or (
                    path.parent == BACKEND_APP / "services"
                    and node.level == 1
                    and (
                        node.module == "identity_client"
                        or (
                            node.module is None
                            and any(
                                alias.name == "identity_client" for alias in node.names
                            )
                        )
                    )
                )
            ):
                imports_identity_client = True
        if imports_identity_client:
            production_importers.add(path.relative_to(BACKEND_APP).as_posix())
    assert production_importers == {"services/whatsapp_client.py"}

    whatsapp_account_tree = ast.parse(
        (BACKEND_APP / "models" / "whatsapp_account.py").read_text(encoding="utf-8")
    )
    whatsapp_account_fields = {
        target.id
        for node in ast.walk(whatsapp_account_tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert whatsapp_account_fields.isdisjoint(
        {"token", "jwt", "m2m_token", "access_token", "refresh_token"}
    )


def test_frontend_runtime_has_no_m2m_credentials_or_token_endpoint():
    """Tokens humanos admin/refresh permanecem válidos; apenas marcadores M2M são proibidos."""
    runtime_source = _frontend_runtime_source()
    normalized = runtime_source.casefold()

    forbidden_markers = {
        "/v1/tokens",
        "get_m2m_jwt",
        "identity_client",
        "idpw_token",
        "m2m_token",
        "m2m-token",
        "service_token",
        "service-token",
    }
    assert not any(marker in normalized for marker in forbidden_markers)
    assert not re.search(
        r"(?:localstorage|sessionstorage)\s*(?:\.\s*setitem\s*\(|\[)\s*['\"]"
        r"(?:whatsapp|identity|service)[_-]?(?:access[_-]?)?(?:token|jwt)['\"]",
        runtime_source,
        flags=re.IGNORECASE,
    )
