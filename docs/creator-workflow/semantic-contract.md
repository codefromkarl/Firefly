# 语义候选、反向审稿与变更影响的数据合同

实现为 `scripts/creator_system/semantic.py`。这里只做原文定位、身份、字段、字面引用、覆盖与版本校验；不把 Markdown 排版段落自动称为观点，不自动生成语义判断或作者批准。所有真实 pack、候选和审稿记录都应保存在私有工作目录。

## 接口

```python
prepare_document(path, source_paths=None)  # 原稿与显式提供的本地 Markdown 来源卡
pack_fingerprint(pack)                    # canonical 完整 pack，忽略顶层 captured_at
validate_analysis(pack, analysis)         # errors/warnings/coverage/analysis_sha256
validate_review(pack, analysis, review)   # 字面锚点、身份、版本和字段检查
static_findings(pack, analysis)           # 结构信号，不是语义审查结论
compare_documents(old_pack, new_pack, analysis)
```

所有校验结果保持 `status=pending_review`、`semantic_verified=false`、`author_approved=false`。`valid=true` 只表示当前合同检查通过，不能解释为观点被证实、审稿人身份已认证或允许发布。原稿中的命令、链接和代码都作为文本保存，不执行、不联网。

## 原文 pack

`schema=1`；`document` 包含原文件字节 `sha256`、标题及本地绝对 `path`。标题优先 frontmatter 的 title，其次首个标题，最后文件名。frontmatter 不变成正文 block，但正文 `line_start/line_end` 对应真实文件行号。

每个 block 包含：

- `id`：`B-<内容SHA前20位>-<同文出现序号>`。
- `ordinal`：本次排列序号，不参与身份生成。
- `kind`：heading/paragraph/list/quote/code，仅为确定性排版分类。
- `section`：当前位置的标题层级文本。
- `text`、完整内容 `sha256`、实际行号、`ambiguous`。

段落文本保留原句和内部换行，不改写观点。文件换行由 Python `splitlines()` 统一表示为 `\n`；文件级哈希仍采用原始字节。相同文字出现多次有不同出现序号，同时全部标 `ambiguous=true`。新增普通段落不会让后文仅因 ordinal 改变而换 ID；新增重复段落的身份歧义必须人工核对。

`sources` 是显式传入的 Markdown 来源卡：`id` 优先采用 frontmatter id，否则由内容哈希生成；同时记录原字节 `sha256`、`content`、绝对 `path`、`provenance=provided_source_note`。保存一张来源卡不证明读过原始出版物，不升级成 primary verified。

`pack_fingerprint` 绑定原文 block、原文身份以及全部来源卡的 ID、内容、版本和位置。CLI 应从 document.path 与 sources.path 重新读取并比较，拒绝把手改 pack 当成未变的真实原稿；本模块的历史比较函数不读取当前路径，以便分析旧快照。

## 语义 analysis

analysis 必须为 schema 1，带 `document_sha256` 和 **`pack_sha256=pack_fingerprint(pack)`**。来源卡改变即使原稿未变，也使旧 analysis/review 不再适用。

每个 segment 按约定记录 id、title、role、question、thesis、claim_type、audience_before、audience_after、source_blocks、context_blocks、reasoning_steps、evidence、limitations、visuals，以及可选 transition。role 支持 hook/definition/explanation/comparison/example/boundary/application/conclusion/transition；claim_type 支持 definition/factual/causal/comparison/recommendation/personal_judgment/none。

- 正文 block 必须明确归属一个 segment，或出现在带理由的 exclusions 中；漏段、重复归属和同时排除/归属都是错误。
- heading 可作为共享 source/context；context 引用不替代正文覆盖。
- block ID、source ID、segment ID、visual ID 均校验存在性/唯一性。
- visual 必须说明 type/purpose，并锚定其 segment 已声明的 source/context blocks。渲染字段由分镜编译器进一步校验。
- evidence 必须指向 pack 提供的 source_id，写明 relation 和 scope；不能仅凭该结构断言来源支持主张。
- transition.to 必须指向其他实际存在的 segment，并有 reason。

校验器不会把没有 evidence 的 factual 自动补上引文，也不会凭字数、标题或图数判断逻辑优劣。返回的 coverage.ratio 仅是声明的正文归属/排除覆盖率。

## 反向审稿 review

review 带原稿 `document_sha256`、完整规范 analysis 的 `analysis_sha256`、显式声明的 reviewer.kind（ai/human）与 name，以及 findings/strengths。完整 analysis 哈希包括 pack 绑定，因此来源卡变化也会使审稿过期。

每条 finding 记录 id、segment_ids、block_ids、category、severity、observation、reason、impact、options、uncertainty、status，并且至少有一个：

```json
{"anchors":[{"block_id":"实际block ID","quote":"逐字包含在原block中的原句"}]}
```

锚点必须指向 finding 声明的原文 block；声明 segment 时，还要能在那些 segment 的 source/context 找到。伪造原句、未知 block、与片段无关的锚点都拒绝。category 支持 evidence/logic/scope/definition/transition/presentation/coverage；severity 支持 major/minor/suggestion。

status 为 open/resolved/dismissed。resolved/dismissed 需要 `resolution.reason` 与 `resolution.actor`（非空名称字符串或含 name 的对象）。这些只是调用者声明的处理记录；`identity_provenance=caller_declared_not_authenticated`，不能生成作者批准。没有发现也不要求人为制造批评；strengths 不被用来抵消未解决问题。

## 静态信号

`static_findings` 只发出可核对的结构信号：遗漏正文、声明 causal 但 reasoning_steps 为空、声明 factual/causal/comparison 但 evidence 为空，以及单张 visual 的节点数超过当前renderer的5节点上限。最后一项要求拆图，不据此判论证薄弱，也不因一个片段使用多张图而报错。

所有条目标 `provenance=program_signal_needs_review`、`semantic_verdict=null`。实际逻辑、事实、边界和观众理解的判断应来自另一份可追溯审稿候选，而不是这个计数器。

## 修改后比较

`compare_documents(old_pack,new_pack,analysis)` 要求 analysis 绑定 old_pack，返回：

- added、removed、moved、context_changed、ambiguous_duplicate。
- changed：按结构对齐发现的 `{old_id,new_id,basis}` 候选配对；不是自动认定两句语义等价。
- source_changed_ids：提供的来源卡新增、删除或哈希变化。
- affected_segment_ids、affected_visual_ids。
- rerecord_segment_ids：旧 source_blocks 的正文被删除/改写时列出，单纯图形配置、移动、来源卡变化或相邻语境变化不会自动要求重录。
- new_unassigned_blocks：新增或仍未分配的新正文，不能继承成“已经覆盖”。

移动使用共同 block 的相对顺序，不因前方单纯插入导致所有后文被判移动。相邻块与所属 section 改变会记录需要复核的语境影响。共享 heading 仅因下面新增首段而邻接变化时，不将影响扩散到所有远处片段；标题文字、层级或移动改变仍可传播。

此接口比较的是原文/来源快照与既有候选的依赖；没有传入旧新两份 analysis，因此不声称检测独立的旁白配置修改。旁白候选自身改动仍须由编译/工程版本哈希单独比对。只改 visual 配置而原文不变，rerecord_segment_ids 为空。

## 合成测试

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s scripts/creator_system -t scripts -p 'test_semantic.py'
```

覆盖真实行号、未核实来源标记、断链、重复身份、覆盖与共享标题、伪造锚点、过期候选/审稿、解决记录、插入/移动/标题语境变化、重复段落、核心原文变化与图形单独变化，以及来源卡改版失效。测试不读取用户文稿，不生成真实语义结论。

字段一致性：reasoning_steps、limitations、strengths均为非空字符串组成的数组（数组本身可空）；每条finding必须至少关联一个现有segment。全局发现需明确关联所涉及的段落，不允许空目标默默通过。导出器预留显式visual IDs，自动补图ID会确定性避让；实际生成文件哈希参与缓存身份。上下文块变化会提示该段画面复查，但不自动要求重录不变的旁白。
