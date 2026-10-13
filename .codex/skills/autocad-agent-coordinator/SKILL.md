---
name: autocad-agent-coordinator
description: Coordinate AutoCAD work through this project's autocad_beiming and autocad_puran MCP tools. Use when an agent is asked to inspect, create, edit, or export a CAD drawing: explain the intended changes to the user before applying tools, then verify the result.
---

# AutoCAD Agent Coordinator

Use this workflow for AutoCAD tasks performed through the project's MCP launcher. The skill guides the agent; the MCP tools perform the CAD operations. Do not claim that loading this skill starts AutoCAD or connects an MCP server.

## Workflow

1. Identify the user's requested outcome and the drawing to affect. Inspect the available MCP tools and current drawing state using read-only operations. `autocad_beiming` is the default connection; use `autocad_puran` only when its exposed capability better fits the task or the user requests it. The gateway changes connections when a tool is called.
2. Before the first CAD mutation, send a short user-facing message in plain language: which drawing or area will change, what you will do, and how you will check the result. For a multi-step task, list the main steps. This message communicates the plan; it does not ask for approval unless approval is genuinely required by the task or agent host.
3. Execute the plan with the tools actually exposed by the selected MCP. Read each tool's schema before calling it. Keep CAD mutations sequential. Do not assume a transaction, rollback, readback, or export operation exists unless the active tool provides it. If the plan changes materially, tell the user before continuing.
4. After each meaningful mutation, use available read-only tools to compare the actual drawing state with the requested result. If a call fails or its result is ambiguous, stop further dependent changes, report the specific failure, and avoid claiming completion.
5. Finish with a concise report: what changed, what was verified, and any remaining uncertainty. Distinguish tool success from verified drawing correctness.

## Boundaries

- Loading or invoking this skill is not proof that a tool ran. Report only observed tool results.
- Never invent an MCP operation or pass an example payload as if it were a supported schema.
- Do not modify unrelated geometry or silently change the active drawing. Clarify the target when multiple drawings could be affected.
- For mechanical drafting under GB/T, apply `mechanical-drafting-gbt` too if that skill is available in the agent. Its engineering checks complement this coordination workflow; they do not replace the user-facing plan.
- This skill asks the agent to explain before acting. A host that needs to enforce the sequence for every agent must also gate CAD mutations outside the skill.

## Example of the user-facing plan

"Tôi sẽ kiểm tra bản vẽ đang mở, tạo các đối tượng theo kích thước bạn đưa trên đúng layer, rồi đọc lại tọa độ và số lượng đối tượng để xác nhận. Nếu bản vẽ hoặc kích thước chưa rõ, tôi sẽ hỏi trước khi sửa."
