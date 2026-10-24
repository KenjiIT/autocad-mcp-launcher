import ast
from pathlib import Path

from lt_adapter.lt_file_ipc import LtFileIPCBackend


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_FILE = ROOT / "autocad-beiming-mcp-custom" / "src" / "autocad_mcp" / "backends" / "file_ipc.py"
COM_HELPERS = {
    "_com_executor", "_get_autocad_application", "_get_entity_via_com",
    "_create_entity_via_com", "_create_with_com_fallback", "_create_hatch_com",
    "_save_via_com", "_export_dxf_via_com", "_collect_entities_via_com",
    "_plot_preview_via_com", "_plot_png_via_com", "_join_lines_via_com",
    "_layer_set_color_com", "_create_dimension_via_com", "_solid_context",
}
# shutdown only closes the idle STA executor allocated by the upstream base
# constructor; the LT backend never submits a COM callback to it.
INHERITED_COM_CLEANUP_ONLY = {"shutdown"}


def test_every_public_method_with_a_com_dependency_is_classified():
    tree = ast.parse(UPSTREAM_FILE.read_text(encoding="utf-8"))
    backend = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "FileIPCBackend")
    missing = []
    for node in backend.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name.startswith("_"):
            continue
        dependencies = {
            item.attr for item in ast.walk(node)
            if isinstance(item, ast.Attribute)
            and (item.attr in COM_HELPERS or item.attr.endswith("_com") or "_com_" in item.attr)
        }
        if not dependencies:
            continue
        if (node.name in LtFileIPCBackend._UNSUPPORTED
                or node.name in LtFileIPCBackend.__dict__
                or node.name in INHERITED_COM_CLEANUP_ONLY):
            continue
        if "_create_with_com_fallback" in dependencies and "_create_with_com_fallback" in LtFileIPCBackend.__dict__:
            continue
        missing.append(f"{node.name}: {sorted(dependencies)}")
    assert not missing, "Unclassified upstream COM methods: " + "; ".join(missing)
