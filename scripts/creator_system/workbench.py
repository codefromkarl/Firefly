"""Read-only legacy indexing, candidate proposals, and an explicit Obsidian dashboard."""
from pathlib import Path
import re

import yaml

from .store import ControlError, digest, safe_path, utc_now


def track_legacy_notes(store):
    """Index without migrating or writing any user-owned note or verification label."""
    tracked = []
    seen = set()
    for folder in ["10 书籍", "20 知识卡片", "30 主题研究", "40 内容项目", "50 来源"]:
        parent = safe_path(store.vault, folder)
        if not parent.exists():
            continue
        for path in sorted(parent.rglob("*.md")):
            relative = path.relative_to(store.vault).as_posix()
            path = safe_path(store.vault, relative)
            raw = path.read_bytes()
            text = raw.decode("utf-8")
            match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
            data = yaml.safe_load(match[1]) if match else {}
            if not isinstance(data, dict):
                raise ControlError(f"Invalid frontmatter: {relative}")
            identity = str(data.get("id") or data.get("book_id") or relative)
            record_id = "legacy-" + digest(f"{data.get('type','note')}:{identity}".encode())[:32]
            if record_id in seen:
                raise ControlError("Duplicate stable legacy ID; resolve ambiguity before indexing")
            seen.add(record_id)
            tracked.append((record_id, {"note_path": relative, "note_sha256": digest(raw),
                                        "blob": store.blob(raw), "declared_type": data.get("type", "note"),
                                        "declared_id": data.get("id") or data.get("book_id"),
                                        "declared_verification": str(data.get("verification", "unknown")),
                                        "effective_review": "legacy_unverified", "present": True,
                                        "title": data.get("title", path.stem), "authors": data.get("authors", [])}))
    existing = {row["id"]: row for row in store.list("legacy_note")}
    for record_id, data in tracked:
        if record_id in existing:
            store.update("legacy_note", record_id, data, existing[record_id]["digest"])
        else:
            store.create("legacy_note", data, record_id)
        if data["declared_type"] == "book" and data["declared_id"]:
            work_id = str(data["declared_id"])
            if not any(row["id"] == work_id for row in store.list("work")):
                store.create("work", {"title": data["title"], "authors": data["authors"], "legacy_note_id": record_id,
                                      "identity_basis": "existing_user_catalogue", "version_mapping": "not_inferred"}, work_id)
    for record_id, row in existing.items():
        if record_id not in seen and row["data"].get("present"):
            store.update("legacy_note", record_id, {**row["data"], "present": False}, row["digest"])
    return {"indexed": len(tracked), "notes_modified": 0, "review_promotions": 0}


def propose_change(store, note_path, candidate_text, expected_hash):
    target = safe_path(store.vault, note_path)
    if not target.is_file():
        raise ControlError("A candidate must name an existing note")
    record = store.create("candidate", {"note_path": note_path, "base_sha256": expected_hash,
                                       "candidate_blob": store.blob(candidate_text.encode()), "created_at": utc_now()})
    file = safe_path(store.root, f"candidates/{record['id']}.md")
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("x", encoding="utf8") as stream:
        stream.write(candidate_text)
    return {"candidate_id": record["id"], "file": str(file), **candidate_status(store, record["id"])}


def candidate_status(store, candidate_id):
    data = store.get("candidate", candidate_id)["data"]
    note = safe_path(store.vault, data["note_path"])
    current = digest(note.read_bytes()) if note.is_file() else None
    return {"status": "ready_for_manual_merge" if current == data["base_sha256"] else "conflict",
            "current_sha256": current, "base_sha256": data["base_sha256"], "original_modified": False}


def system_status(store):
    from .sources import source_status
    from .workflow import Workflow
    workflow = Workflow(store)
    sources = []
    for row in store.list("source"):
        version = row["data"].get("active_version_id")
        try:
            status = source_status(store, version) if version else {"error": "no_active_version"}
        except (ControlError, OSError) as error:
            status = {"error": str(error)}
        sources.append({"id": row["id"], **status})
    def inspect(kind):
        results = []
        for row in store.list(kind):
            try:
                report = workflow.inspect(kind, row["id"])
            except (ControlError, OSError) as error:
                report = {"error": str(error), "stale": True}
            if kind == "project" and hasattr(workflow, "project_status"):
                report = {**report, "workflow": workflow.project_status(row["id"])}
            results.append({"id": row["id"], "data": row["data"], "inspection": report})
        return results
    return {"generated_at": utc_now(), "projects": inspect("project"), "sources": sources,
            "claims": inspect("claim"), "drafts": inspect("draft"), "reviews": inspect("review"),
            "runs": store.list("run"), "releases": inspect("release"), "deliveries": store.list("delivery"),
            "candidates": [{"id": row["id"], **candidate_status(store, row["id"])} for row in store.list("candidate")],
            "legacy_notes": len(store.list("legacy_note")), "backups": store.list("backup"),
            "previews": inspect("preview"), "selections": store.list("selection"),
            "review_actions": inspect("review_action"),
            "facts": {"semantic_truth": "not_guaranteed", "publisher": "manual_or_separately_authorized",
                      "strong_authentication": False, "background_automation": False}}


def write_dashboard(store):
    report = system_status(store)
    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = ["# 知识生产系统", "", f"最近显式刷新：{report['generated_at']}", "",
             "> 此页由运行记录生成。编辑此页不会批准内容或改变发布状态。继续研究时由助手显式调用工具，未配置后台自动运行。", "",
             "## 当前项目", "", "| 项目 | 目标 | 当前状态与检查 |", "| --- | --- | --- |"]
    for row in report["projects"]:
        state = row["inspection"].get("workflow", {})
        labels = {
            "awaiting_reconciliation": ("等待核实外部结果", "先核实结果，再回填记录；不要重复提交"),
            "maintenance_reported_published": ("已登记发布结果", "保留平台链接并处理反馈；系统未自动核实平台"),
            "delivery_failed": ("交付失败", "查看失败记录，重新核对产物和授权"),
            "in_progress_or_interrupted": ("运行中或曾中断", "查看已保存步骤后显式继续"),
            "run_failed": ("运行失败", "检查失败原因；在次数上限内继续或修订输入"),
            "changes_need_review": ("版本变化，需复查", "检查受影响的证据、稿件和审查"),
            "awaiting_author_decision": ("等待作者决定", "审阅当前发布包并明确采用或退回"),
            "revision_requested": ("作者要求修改", "依据作者决定修改候选稿"),
            "ready_for_authorized_delivery": ("可按授权交付", "仅执行已授权的外部动作并保留回执"),
            "review_objections_open": ("存在未解决异议", "逐项复查，明确记录哪些异议已解决"),
            "ready_to_prepare": ("可准备发布包", "导出并检查排版，然后绑定当前审查"),
            "awaiting_review": ("等待审查", "核对原文、推论和段落对应"),
            "evidence_needs_recheck": ("证据需复查", "检查换版、撤回或不可用的来源"),
            "claim_candidates_ready": ("观点候选已登记", "组织稿件并记录段落与观点的对应"),
            "research_needed": ("等待研究", "登记来源版本，检索原文并形成证据"),
        }
        description, action = labels.get(state.get("status"), ("任务已登记", "查看项目记录并继续执行"))
        lines.append(f"| {cell(row['id'])} | {cell(row['data'].get('goal',''))} | {cell(description)}；{cell(action)} |")
    if not report["projects"]:
        lines.append("| 尚无受控项目 | 使用 creator:system project-create 新建，或显式关联已有项目 | 历史笔记不会自动变成已审阅项目 |")
    lines += ["", "## 资料与待处理事项", "",
              f"- 历史笔记索引：{report['legacy_notes']}；索引不会自动提升历史核查状态。",
              f"- 已登记来源：{len(report['sources'])}；观点：{len(report['claims'])}；稿件：{len(report['drafts'])}。", ""]
    navigation = [f"[[{name}]]" for name in ("阅读导航", "创作导航") if (store.vault / f"{name}.md").is_file()]
    if navigation:
        lines += ["原有资料入口：" + " · ".join(navigation), ""]
    lines += editorial_sections(store, report)
    for label, entries in [("来源状态", report["sources"]), ("审查有效性", report["reviews"]),
                           ("候选合并", report["candidates"]), ("最近任务运行", report["runs"][-10:]),
                           ("交付状态", report["releases"]), ("平台记录", report["deliveries"])]:
        lines += [f"## {label}", ""]
        if entries:
            for row in entries:
                data = row.get("data", row)
                if "inspection" in row:
                    check = row["inspection"]
                    text = "当前版本有效" if check.get("valid") else "需重新检查"
                    if check.get("issues"):
                        text += "；" + "; ".join(str(item) for item in check["issues"])
                    if label == "审查有效性":
                        text += f"；审查结论：{data.get('conclusion','未记录')}（不等于作者确认）"
                elif label == "来源状态":
                    labels = {"withdrawn": "已撤回", "active_version_changed": "当前版本已改变", "current_source_changed": "原文件已改变", "current_source_unavailable": "原文件不可用"}
                    problems = [name for key, name in labels.items() if data.get(key)]
                    text = "、".join(problems) if problems else f"原文状态：{data.get('parse_status','待检查')}"
                    if data.get("web_live_status") == "not_checked":
                        text += "；网页当前可访问性尚未检查"
                    if data.get("uncertainty") == "ocr_unverified":
                        text += "；OCR文本待对照原页面"
                    if data.get("error"):
                        text = "读取失败：" + data["error"]
                elif label == "最近任务运行":
                    text = f"阶段 {data.get('stage')}；状态 {data.get('state')}；尝试 {data.get('attempts')} 次；费用 {data.get('cost_status','未知')}"
                elif label == "平台记录":
                    text = f"渠道 {data.get('channel')}；本地记录状态 {data.get('state')}；平台事实未自动核实"
                else:
                    text = {"ready_for_manual_merge": "候选可供人工合并，原稿未改动", "conflict": "原稿已变化，请比较后合并"}.get(data.get("status"), str(data.get("status", "待检查")))
                lines += [f"- `{cell(row['id'])}`：{cell(text)}"]
        else:
            lines += ["暂无记录。"]
        lines.append("")
    lines += ["## 备份与恢复", ""]
    if report["backups"]:
        for row in report["backups"]:
            data = row['data']
            purpose = "本地恢复演练" if data.get("purpose") == "local_recovery_drill" else "手动备份"
            filesystem = "同一文件系统" if data.get("filesystem_relation") == "same_filesystem" else "文件系统关系未确认或不同"
            lines.append(f"- {purpose} `{cell(row['id'])}`：{data.get('files')} 个文件，文件校验完成于 {cell(data.get('verified_at'))}；恢复演练：{'已通过' if data.get('restore_tested') else '未执行'}；{filesystem}，独立物理设备未确认。")
        if all(row["data"].get("purpose") == "local_recovery_drill" for row in report["backups"]):
            lines.append("\n以上是可追溯的本地恢复验证；独立备份位置仍未配置，不代表已具备设备故障恢复能力。")
    else:
        lines.append("独立备份未配置。恢复工具可用不代表本仓库已有备份；需要明确目标位置后运行并验证。")
    lines += ["", "## 操作入口", "", "在项目目录运行 `pnpm creator:system --help` 查看命令。", "",
              "常用顺序：登记来源 → 检索/读取原文 → 建立证据 → 登记观点与稿件 → 审查 → 预览 → 作者决定 → 交付记录。",
              "", "检查通过只表示相应检查完成；审查和确认都针对具体版本，来源或稿件变动可能使之失效。", ""]
    content = "\n".join(lines)
    target = safe_path(store.vault, "系统首页.md")
    previous = next((r for r in store.list("view") if r["id"] == "dashboard"), None)
    if target.exists() and (previous is None or digest(target.read_bytes()) != previous["data"]["sha256"]):
        raise ControlError("System dashboard was edited; preserve it and resolve the difference before refreshing")
    # Explicit refresh of a generated view; never modifies an author-owned note.
    target.write_text(content, encoding="utf8")
    data = {"path": "系统首页.md", "sha256": digest(content.encode()), "generated_at": report["generated_at"]}
    if previous:
        store.update("view", "dashboard", data, previous["digest"])
    else:
        store.create("view", data, "dashboard")
    return {"path": str(target), "status": report}


def editorial_sections(store, report):
    from .workflow import Workflow
    flow = Workflow(store)
    def text(value):
        return str(value).replace("\n", " ").replace("\r", " ")
    def link(label, path):
        return f"[{label}](<{Path(path).as_uri()}>)"
    lines = ["## 本期审稿与预览", ""]
    for project in report["projects"]:
        project_id = project["id"]
        drafts = sorted((r for r in report["drafts"] if r["data"]["project_id"] == project_id),
                        key=lambda r: (r["data"]["created_at"], r["id"]))
        if not drafts:
            continue
        draft = drafts[-1]
        lines += [f"### {project_id} · {draft['id']}", "", link("打开原稿", safe_path(store.vault, draft["data"]["note_path"])), ""]
        selection = next((r for r in report["selections"] if r["data"]["project_id"] == project_id), None)
        preview = next((r for r in report["previews"] if selection and r["id"] == selection["data"]["preview_id"]), None)
        if preview:
            label = "当前预览" if preview["inspection"].get("valid") and preview["data"]["draft_id"] == draft["id"] else "历史/需重新检查的预览"
            directory = safe_path(store.vault, preview["data"]["artifact_dir"])
            lines += [f"- {link(label, directory / 'bilibili.html')} · `{preview['id']}`；仅本地预览，未代表作者批准。", ""]
        else:
            lines += ["尚未登记当前预览。", ""]
        inherited_ids = {ref["id"] for ref in draft["data"].get("inherited_reviews", [])}
        current_reviews = [r for r in report["reviews"] if r["id"] in inherited_ids or
                           r["data"]["target_kind"] == "draft" and r["data"]["target_id"] == draft["id"]]
        priority = {"major": 0, "minor": 1, "suggestion": 2}
        current_reviews.sort(key=lambda r: (min((priority.get(finding.get("severity"), 3) for finding in r["data"].get("findings", [])), default=3),
                                            min((finding["id"] for finding in r["data"].get("findings", [])), default=r["id"])))
        outstanding = {r["id"] for r in flow._outstanding_reviews([("draft", draft["id"])])}
        lines += [f"本稿未解决审查：{len(outstanding)} 项。修订、保留与暂缓均需记录理由；处理意向不表示已复查或批准。", ""]
        for review in current_reviews:
            data = review["data"]
            inherited = review["id"] in inherited_ids
            if (inherited or review["inspection"].get("valid")) and review["id"] not in outstanding:
                continue
            state = "旧稿意见，需对照新稿复查" if inherited else "待处理" if review["inspection"].get("valid") else "输入变化，需重新审查"
            actions = sorted((row for row in report["review_actions"] if row["data"]["draft_id"] == draft["id"] and
                              row["data"]["review_ref"]["id"] == review["id"]), key=lambda row: (row["data"]["created_at"], row["id"]))
            for finding in data.get("findings", []):
                severity = {"major": "重要", "minor": "一般", "suggestion": "建议"}.get(finding["severity"], finding["severity"])
                lines += [f"#### {text(finding['id'])} · {text(severity)} · {state}", "",
                          f"审查记录：`{review['id']}`；意见来源为调用者声明，仍属候选。", ""]
                for anchor in finding.get("mapped_anchors", []):
                    origin = f"旧稿 {data['target_id']} " if inherited else "原稿"
                    lines += [f"{origin}第 {anchor['line_start']} 行 / 第 {anchor['paragraph']} 块：", "", "> " + text(anchor["quote"]), ""]
                for label, key in [("问题", "observation"), ("理由", "reason"), ("影响", "impact"), ("不确定性", "uncertainty")]:
                    lines += [f"{label}：{text(finding[key])}", ""]
                lines += [f"- 处理选项：{text(option)}" for option in finding["options"]] + [""]
                if actions:
                    action = actions[-1]
                    label = {"revise": "计划修订", "retain": "保留原文", "defer": "暂缓处理"}[action["data"]["action"]]
                    validity = "待复查" if action["inspection"].get("valid") else "材料已变化，处理记录需重新检查"
                    lines += [f"最近处理：{label}（{validity}）；记录者：{text(action['data']['actor'])}。", "",
                              f"处理理由：{text(action['data']['reason'])}", ""]
                    if action["data"].get("candidate_path"):
                        lines += [link("查看修订候选（未覆盖原稿）", safe_path(store.vault, action["data"]["candidate_path"])), ""]
                else:
                    lines += ["尚未记录处理方式。可告诉助手意见编号、修订/保留/暂缓及理由；由 review-action 保存记录。", ""]
                lines += ["完成实际检查后，使用覆盖同名检查的显式复查关联本记录；新稿中的旧原句位置不得直接沿用。", ""]
            if not data.get("findings"):
                lines += [f"- {state} · `{review['id']}`：{text('; '.join(data.get('issues', [])))}", ""]
                if actions:
                    action = actions[-1]
                    label = {"revise": "计划修订", "retain": "保留原文", "defer": "暂缓处理"}[action["data"]["action"]]
                    validity = "待复查" if action["inspection"].get("valid") else "材料变化，需重新检查"
                    lines += [f"最近处理：{label}（{validity}）；理由：{text(action['data']['reason'])}；记录者：{text(action['data']['actor'])}。", ""]
        lines += ["#### 观点与原文对应", ""]
        for claim_id in draft["data"]["claim_ids"]:
            claim = store.get("claim", claim_id)["data"]
            paragraphs = [str(m["paragraph"]) for m in draft["data"]["paragraphs"] if claim_id in m["claim_ids"]]
            lines += [f"- `{claim_id}` · 正文块 {', '.join(paragraphs)}：{text(claim['text'])}",
                      f"  适用范围：{text(claim.get('boundaries', ''))}"]
            for relation in claim["evidence_links"]:
                evidence = store.get("evidence", relation["evidence_id"])["data"]
                source = store.get("source_version", evidence["source_version_id"])["data"]
                lines += [f"  原文：{link(source['source_id'], source['original_path'])} · `{relation['evidence_id']}` · {text(relation['relation'])} · 定位 {text(evidence['locator'])}；捕获范围 {source['capture_scope']}。"]
        lines.append("")
    return lines
