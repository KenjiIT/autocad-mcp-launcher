"""MCP server cho phần mềm dự toán xây dựng — truy cập SQLite trực tiếp."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from dutoan_mcp.database import SessionLocal
from dutoan_mcp.models.don_gia import DonGia, TuDienVatTu
from dutoan_mcp.models.project import (
    Project,
    ProjectItem,
    ProjectSection,
    ProjectSettings,
)
from dutoan_mcp.services.cost_summary import (
    DEFAULT_SECTION_RATES,
    SECTION_NAMES,
    calculate_cost_summary_for_project,
    detect_cost_type,
)
from dutoan_mcp.services.price_calculator import calculate_unit_price

server = Server("dutoan-mcp")


def _text(data: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


def _ensure_section(db, project_id: int, cost_type: str) -> ProjectSection:
    section = db.query(ProjectSection).filter(
        ProjectSection.project_id == project_id,
        ProjectSection.cost_type == cost_type,
    ).first()
    if not section:
        sort_map = {"XD": 0, "LD": 1, "SC": 2, "KS": 3}
        defaults = DEFAULT_SECTION_RATES.get(cost_type, DEFAULT_SECTION_RATES["XD"])
        section = ProjectSection(
            project_id=project_id,
            name=f"Phần {cost_type} - {SECTION_NAMES.get(cost_type, cost_type)}",
            cost_type=cost_type,
            sort_order=sort_map.get(cost_type, 99),
            chi_phi_chung_pct=defaults["chi_phi_chung_pct"],
            thu_nhap_tt_pct=defaults["thu_nhap_tt_pct"],
        )
        db.add(section)
        db.flush()
    return section


# ======================================================================
# Tool definitions
# ======================================================================

TOOLS: list[Tool] = [
    Tool(
        name="search_don_gia",
        description="Tra cứu đơn giá xây dựng theo mã hoặc tên công việc. Trả về danh sách công việc với mã hiệu, tên, đơn vị tính và chi phí VLC/NC/MTC.",
        inputSchema={
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Từ khóa tìm kiếm (mã hiệu đơn giá hoặc tên công việc)"},
                "chapter": {"type": "string", "description": "Lọc theo chương (ví dụ: 'AF' cho công tác bê tông)"},
                "regulation_code": {"type": "string", "description": "Mã thông tư áp dụng (mặc định TT12-2021)"},
                "page": {"type": "integer", "description": "Số trang (phân trang)"},
                "limit": {"type": "integer", "description": "Số kết quả mỗi trang (mặc định 20)", "default": 20},
            },
            "required": ["q"],
        },
    ),
    Tool(
        name="phan_tich_don_gia",
        description="Phân tích chi tiết đơn giá cho một mã hiệu công việc. Trả về bảng phân tích VLC (vật liệu), NC (nhân công), MTC (máy thi công) với định mức và đơn giá từng thành phần.",
        inputSchema={
            "type": "object",
            "properties": {
                "mhdg": {"type": "string", "description": "Mã hiệu đơn giá (ví dụ: 'AF.11110')"},
                "source": {"type": "string", "description": "Nguồn đơn giá (ví dụ: tên tỉnh/thành phố)"},
                "regulation_code": {"type": "string", "description": "Mã thông tư áp dụng"},
            },
            "required": ["mhdg"],
        },
    ),
    Tool(
        name="create_project",
        description="Tạo dự án dự toán mới. Sau khi tạo, có thể thêm công việc vào dự án bằng tool add_project_item.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Tên dự án"},
                "description": {"type": "string", "description": "Mô tả dự án"},
                "regulation_code": {"type": "string", "description": "Mã thông tư áp dụng"},
                "estimate_type": {
                    "type": "string",
                    "enum": ["new", "repair"],
                    "description": "Loại dự toán: 'new' (xây mới) hoặc 'repair' (sửa chữa)",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="add_project_item",
        description="Thêm một công việc (hạng mục) vào dự án dự toán. Cần có mã hiệu đơn giá và khối lượng. Hệ thống tự tính thành tiền.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "ID của dự án"},
                "mhdg": {"type": "string", "description": "Mã hiệu đơn giá của công việc"},
                "quantity": {"type": "number", "description": "Khối lượng công việc"},
                "notes": {"type": "string", "description": "Ghi chú cho hạng mục"},
            },
            "required": ["project_id", "mhdg", "quantity"],
        },
    ),
    Tool(
        name="get_project_summary",
        description="Xem tổng hợp chi phí dự án, bao gồm: chi phí vật liệu (VLC), nhân công (NC), máy thi công (MTC), chi phí trực tiếp (T), chi phí chung (C), thu nhập chịu thuế tính trước (TL), giá trị dự toán (G), thuế GTGT, giá trị dự toán sau thuế (GXD).",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "ID của dự án"},
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="search_vat_tu",
        description="Tra cứu giá vật tư, vật liệu xây dựng theo tên hoặc mã. Trả về danh sách vật tư với mã số, tên, đơn vị tính và giá gốc.",
        inputSchema={
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Từ khóa tìm kiếm (mã số hoặc tên vật tư)"},
                "source": {"type": "string", "description": "Nguồn giá vật tư (ví dụ: tên tỉnh/thành phố)"},
                "page": {"type": "integer", "description": "Số trang (phân trang)"},
                "limit": {"type": "integer", "description": "Số kết quả mỗi trang (mặc định 20)", "default": 20},
            },
            "required": ["q"],
        },
    ),
    Tool(
        name="calculate_cvc",
        description="Tính chi phí vận chuyển vật liệu xây dựng theo cự ly. Nhập tên vật liệu và khoảng cách (km) để tính cước vận chuyển.",
        inputSchema={
            "type": "object",
            "properties": {
                "vatlieu": {"type": "string", "description": "Tên hoặc loại vật liệu cần vận chuyển"},
                "culy_km": {"type": "number", "description": "Cự ly vận chuyển (km)"},
                "vehicle_id": {"type": "integer", "description": "ID phương tiện vận chuyển (nếu muốn chỉ định)"},
                "klg": {"type": "number", "description": "Khối lượng vận chuyển"},
            },
            "required": ["vatlieu", "culy_km"],
        },
    ),
    Tool(
        name="lookup_svdt",
        description="Tra cứu suất vốn đầu tư xây dựng theo loại công trình. Dùng để ước tính sơ bộ chi phí đầu tư theo diện tích hoặc công suất.",
        inputSchema={
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Loại công trình cần tra (ví dụ: 'nhà ở', 'trường học')"},
                "nam": {"type": "integer", "description": "Năm áp dụng suất vốn đầu tư"},
            },
            "required": ["q"],
        },
    ),
    Tool(
        name="calculate_svdt",
        description="Tính chi phí ước tính từ suất vốn đầu tư. Cần có ID suất vốn (từ lookup_svdt) và diện tích/công suất công trình.",
        inputSchema={
            "type": "object",
            "properties": {
                "svdt_id": {"type": "integer", "description": "ID suất vốn đầu tư (lấy từ kết quả lookup_svdt)"},
                "dien_tich": {"type": "number", "description": "Diện tích hoặc công suất công trình"},
            },
            "required": ["svdt_id", "dien_tich"],
        },
    ),
    Tool(
        name="compare_prices",
        description="So sánh đơn giá của một mã hiệu công việc giữa các nguồn (tỉnh/thành phố) khác nhau.",
        inputSchema={
            "type": "object",
            "properties": {
                "mhdg": {"type": "string", "description": "Mã hiệu đơn giá cần so sánh"},
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách nguồn đơn giá để so sánh (ví dụ: ['HCM', 'HN', 'DN'])",
                },
            },
            "required": ["mhdg", "sources"],
        },
    ),
    Tool(
        name="get_thvt",
        description="Lấy bảng tổng hợp vật tư, nhân công, máy thi công của dự án. Tổng hợp tất cả tài nguyên cần thiết với số lượng và thành tiền.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "integer", "description": "ID của dự án"},
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="list_projects",
        description="Liệt kê tất cả dự án dự toán đã tạo, với thông tin cơ bản (ID, tên, ngày tạo).",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


# ======================================================================
# Tool handlers
# ======================================================================

def _do_search_don_gia(args: dict) -> dict:
    db = SessionLocal()
    try:
        q = args.get("q", "")
        chapter = args.get("chapter")
        regulation_code = args.get("regulation_code", "TT12-2021")
        page = args.get("page", 1)
        limit = args.get("limit", 20)

        query = db.query(DonGia).filter(
            DonGia.regulation_code == regulation_code,
            DonGia.db_type == "XD+LD+SC",
            DonGia.source == "norm",
        )
        if chapter:
            query = query.filter(DonGia.mhdg.like(f"{chapter}%"))
        if q:
            query = query.filter(
                DonGia.mhdg.contains(q) | DonGia.tcv.contains(q) | DonGia.tk.contains(q)
            )
        total = query.count()
        items = query.order_by(DonGia.mhdg).offset((page - 1) * limit).limit(limit).all()
        return {
            "items": [
                {"mhdg": i.mhdg, "tcv": i.tcv, "dvt": i.dvt,
                 "vlc": i.vlc, "vlp": i.vlp, "nc": i.nc, "mtc": i.mtc,
                 "plv": i.plv, "regulation_code": i.regulation_code, "source": i.source}
                for i in items
            ],
            "total": total, "page": page, "limit": limit,
        }
    finally:
        db.close()


def _do_phan_tich_don_gia(args: dict) -> dict:
    db = SessionLocal()
    try:
        mhdg = args["mhdg"]
        source = args.get("source", "norm")
        regulation_code = args.get("regulation_code", "TT12-2021")
        return calculate_unit_price(db, mhdg, regulation_code, "XD+LD+SC", source)
    finally:
        db.close()


def _do_create_project(args: dict) -> dict:
    db = SessionLocal()
    try:
        regulation_code = args.get("regulation_code", "TT12-2021")
        project = Project(
            name=args["name"],
            description=args.get("description"),
            estimate_type=args.get("estimate_type", "new"),
        )
        db.add(project)
        db.flush()
        settings = ProjectSettings(
            project_id=project.id,
            regulation_code=regulation_code,
            db_type="XD+LD+SC",
            source="norm",
        )
        db.add(settings)
        db.commit()
        return {"id": project.id, "name": project.name, "description": project.description,
                "estimate_type": project.estimate_type, "regulation_code": regulation_code}
    finally:
        db.close()


def _do_add_project_item(args: dict) -> dict:
    db = SessionLocal()
    try:
        project_id = args["project_id"]
        mhdg = args["mhdg"]
        quantity = args["quantity"]

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": f"Dự án {project_id} không tồn tại"}

        settings = project.settings
        reg = settings.regulation_code if settings else "TT12-2021"
        dbt = settings.db_type if settings else "XD+LD+SC"
        src = settings.source if settings else "norm"

        calc = calculate_unit_price(db, mhdg, reg, dbt, src)
        if "error" in calc:
            return calc

        max_order = db.query(ProjectItem.sort_order).filter(
            ProjectItem.project_id == project_id
        ).order_by(ProjectItem.sort_order.desc()).first()
        next_order = (max_order[0] + 1) if max_order and max_order[0] is not None else 0

        cost_type = detect_cost_type(mhdg)
        section = _ensure_section(db, project_id, cost_type)

        item = ProjectItem(
            project_id=project_id,
            section_id=section.id,
            mhdg=mhdg,
            tcv=calc["tcv"],
            dvt=calc["dvt"],
            quantity=quantity,
            vlc=calc["vlc"],
            nc=calc["nc"],
            mtc=calc["mtc"],
            notes=args.get("notes"),
            sort_order=next_order,
        )
        db.add(item)
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(item)

        tt = round(quantity * (calc["vlc"] + calc["nc"] + calc["mtc"]))
        return {
            "id": item.id, "mhdg": mhdg, "tcv": calc["tcv"], "dvt": calc["dvt"],
            "quantity": quantity, "vlc": calc["vlc"], "nc": calc["nc"], "mtc": calc["mtc"],
            "thanh_tien": tt,
        }
    finally:
        db.close()


def _do_get_project_summary(args: dict) -> dict:
    db = SessionLocal()
    try:
        project_id = args["project_id"]
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": f"Dự án {project_id} không tồn tại"}
        summary = calculate_cost_summary_for_project(db, project_id)
        items = db.query(ProjectItem).filter(ProjectItem.project_id == project_id).order_by(ProjectItem.sort_order).all()
        summary["project"] = {"id": project.id, "name": project.name}
        summary["item_count"] = len(items)
        return summary
    finally:
        db.close()


def _do_search_vat_tu(args: dict) -> dict:
    db = SessionLocal()
    try:
        q = args.get("q", "")
        source = args.get("source", "norm")
        regulation_code = "TT12-2021"
        page = args.get("page", 1)
        limit = args.get("limit", 20)

        query = db.query(TuDienVatTu).filter(
            TuDienVatTu.regulation_code == regulation_code,
            TuDienVatTu.source == source,
        )
        if q:
            query = query.filter(
                TuDienVatTu.msvt.contains(q) | TuDienVatTu.tvt.contains(q)
            )
        total = query.count()
        items = query.order_by(TuDienVatTu.msvt).offset((page - 1) * limit).limit(limit).all()
        return {
            "items": [
                {"msvt": i.msvt, "tvt": i.tvt, "dvt": i.dvt, "gia_goc": i.gia_goc}
                for i in items
            ],
            "total": total, "page": page, "limit": limit,
        }
    finally:
        db.close()


def _do_calculate_cvc(args: dict) -> dict:
    db = SessionLocal()
    try:
        from dutoan_mcp.services.cvc_calculator import calculate_transport_cost
        from types import SimpleNamespace
        req = SimpleNamespace(
            vatlieu=args["vatlieu"],
            culy_km=args["culy_km"],
            vehicle_id=args.get("vehicle_id"),
            klg=args.get("klg"),
            road_type_id=None,
            terrain_type_id=None,
            slope_type_id=None,
        )
        result = calculate_transport_cost(db, req)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if hasattr(result, "__dict__"):
            return {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
        return result
    finally:
        db.close()


def _do_lookup_svdt(args: dict) -> dict:
    db = SessionLocal()
    try:
        from dutoan_mcp.services.svdt_service import search_svdt
        result = search_svdt(db, q=args.get("q"), nam=args.get("nam"))
        items = result.get("items", [])
        return {
            "items": [
                {"id": i.id, "ten": i.ten, "dvt": i.dvt, "suat_von": i.suat_von,
                 "nam": i.nam, "quyet_dinh": i.quyet_dinh}
                for i in items
            ],
            "total": result.get("total", 0),
        }
    finally:
        db.close()


def _do_calculate_svdt(args: dict) -> dict:
    db = SessionLocal()
    try:
        from dutoan_mcp.services.svdt_service import calculate_svdt
        result = calculate_svdt(db, args["svdt_id"], args["dien_tich"])
        if result is None:
            return {"error": "Không tìm thấy suất vốn đầu tư"}
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result
    finally:
        db.close()


def _do_compare_prices(args: dict) -> dict:
    db = SessionLocal()
    try:
        mhdg = args["mhdg"]
        sources = args.get("sources", ["norm"])
        tcv = None
        dvt = None
        comparisons = []
        for src in sources:
            calc = calculate_unit_price(db, mhdg, "TT12-2021", "XD+LD+SC", src)
            if "error" in calc:
                comparisons.append({"source": src, "vlc": None, "nc": None, "mtc": None, "total": None, "error": calc["error"]})
                continue
            if tcv is None:
                tcv = calc.get("tcv")
                dvt = calc.get("dvt")
            comparisons.append({"source": src, "vlc": calc["vlc"], "nc": calc["nc"], "mtc": calc["mtc"],
                                "total": calc["vlc"] + calc["nc"] + calc["mtc"]})
        return {"mhdg": mhdg, "tcv": tcv, "dvt": dvt, "comparisons": comparisons}
    finally:
        db.close()


def _do_get_thvt(args: dict) -> dict:
    db = SessionLocal()
    try:
        from dutoan_mcp.services.thvt_service import calculate_thvt
        project = db.query(Project).filter(Project.id == args["project_id"]).first()
        if not project:
            return {"error": f"Dự án {args['project_id']} không tồn tại"}
        return calculate_thvt(db, args["project_id"])
    finally:
        db.close()


def _do_list_projects() -> dict:
    db = SessionLocal()
    try:
        projects = db.query(Project).order_by(Project.updated_at.desc()).all()
        return {
            "projects": [
                {"id": p.id, "name": p.name, "description": p.description,
                 "estimate_type": p.estimate_type or "new",
                 "created_at": str(p.created_at) if p.created_at else None,
                 "updated_at": str(p.updated_at) if p.updated_at else None}
                for p in projects
            ]
        }
    finally:
        db.close()


# ======================================================================
# MCP interface
# ======================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    handlers = {
        "search_don_gia": lambda: _do_search_don_gia(arguments),
        "phan_tich_don_gia": lambda: _do_phan_tich_don_gia(arguments),
        "create_project": lambda: _do_create_project(arguments),
        "add_project_item": lambda: _do_add_project_item(arguments),
        "get_project_summary": lambda: _do_get_project_summary(arguments),
        "search_vat_tu": lambda: _do_search_vat_tu(arguments),
        "calculate_cvc": lambda: _do_calculate_cvc(arguments),
        "lookup_svdt": lambda: _do_lookup_svdt(arguments),
        "calculate_svdt": lambda: _do_calculate_svdt(arguments),
        "compare_prices": lambda: _do_compare_prices(arguments),
        "get_thvt": lambda: _do_get_thvt(arguments),
        "list_projects": lambda: _do_list_projects(),
    }
    handler = handlers.get(name)
    if not handler:
        return _text({"error": f"Tool '{name}' không tồn tại"})
    result = await asyncio.to_thread(handler)
    return _text(result)


def main():
    async def _run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
