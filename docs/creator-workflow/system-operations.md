# 系统操作与控制验收

实现日期：2026-09-22。总设计及唯一阶段验收清单见 [system-design.md](system-design.md)。本文件描述已经能运行的本地功能，不把工具就绪写成真实项目已审阅或平台已发布。

## 数据与运行位置

- 命令入口：`pnpm creator:system --vault .local/creator-vault <command>`。
- Obsidian `系统首页.md` 显示派生状态，显式执行 `dashboard` 刷新，不后台轮询。
- `.creator-system/state.sqlite3` 保存当前记录与不可变修订历史；SQLite 使用 Python 标准库，无新增数据库服务。
- `.creator-system/objects/<sha256>` 保存私有原文、笔记和交付快照。每次读取检查指纹；解析器版本和来源版本共同确定证据定位。
- 原 Obsidian 文件仍是人工编辑入口。`init` 只索引历史笔记和书籍身份，不改写、不提升历史核查状态，不自动把旧摘要变成 evidence/review。
- 搜索仅在显式登记的原文版本内进行。旧库中有来源笔记不等于已经完成原文接入；初始工作台的“已登记来源”指新证据系统中的版本化来源。

初次初始化记录：33 条历史资料笔记索引、17 条作品身份记录，原有 43 篇 Markdown 当时保持不变。后续专栏统一接入首期真实项目与待审稿件；实时状态使用 status/系统首页，不能继续把初始零记录当作当前状态。没有把合成测试写入真实库，也没有自动生成作者批准或发布事实。

## 项目范围与操作入口

```bash
pnpm creator:system --help
pnpm creator:system --vault .local/creator-vault status
pnpm creator:system --vault .local/creator-vault audit
pnpm creator:system --vault .local/creator-vault dashboard
pnpm creator:system --vault .local/creator-vault project-create \
  --id PROJECT-ID --goal '明确的任务目标' --scope /path/to/scope.json
```

scope 示例：

```json
{
  "read_paths": ["10 书籍", "20 知识卡片", "30 主题研究", "40 内容项目", "50 来源"],
  "write_paths": ["40 内容项目", ".creator-system/exports"],
  "tools": ["search", "source-read", "evidence-read"],
  "network": false
}
```

范围是本地接口约束，不是操作系统沙箱。`max_attempts` 限制同阶段同输入的重试次数，不是整个项目总预算。模型费用取不到就记录 unknown；没有自动付费模型调用或后台调度。网络查资料仍由助手显式执行并回写取得的快照；`web-check` 是单独显式的网页访问检查。

## 原文与证据

```bash
pnpm creator:system --vault .local/creator-vault source-add \
  --path /path/to/source.epub --id SOURCE-ID --work-id EXISTING-WORK-ID
pnpm creator:system --vault .local/creator-vault source-units --version SOURCE-VERSION-ID
pnpm creator:system --vault .local/creator-vault search --query '关键词' --topk 5
pnpm creator:system --vault .local/creator-vault source-read \
  --version SOURCE-VERSION-ID --locator '{"kind":"txt","paragraph":1}'
pnpm creator:system --vault .local/creator-vault evidence-add \
  --version SOURCE-VERSION-ID --locator '{"kind":"txt","paragraph":1}' --quote '原文中的必要短摘录'
pnpm creator:system --vault .local/creator-vault evidence-read --id EVIDENCE-ID
pnpm creator:system --vault .local/creator-vault source-recover --version SOURCE-VERSION-ID
```

示例 locator 必须换成 `source-units/search` 实际返回值，不能凭章节印象填写。默认搜索排除撤回来源与旧活动版本；显式选择旧版本可以检索历史，但返回当前适用状态。每次读取原文有长度上限；完整快照只留私有目录。详细格式和解析范围见 [source-interface.md](source-interface.md)。

原文件丢失后，`source-recover` 从校验过的快照恢复到私有 recovered 目录，也可用 `--to` 指定新的 vault-relative 路径。它不覆盖原文件、不创建新来源版本、不把旧版设为活动版，也不撤销来源撤回状态。恢复副本与原始 blob 不共享可写内容；编辑恢复副本不会改坏历史快照。已有文件内容不符时拒绝覆盖。

网页材料用实际取得的 HTML/TXT 文件，加 `--url` 和 `--capture-scope full/excerpt/unknown` 登记，系统明确标记为调用方提供的快照。没有全文访问权限、只拿到片段或 OCR 不可靠，都保留实际范围。`--legacy-note '50 来源/某来源.md'` 可记录旧笔记映射，旧状态不变，映射保持待审查。

`web-check --source SOURCE-ID` 仅 HEAD 检查：2xx 为当时可访问，404/410 为 unavailable，401/403/405/超时等为 unknown。每跳检查公开地址并固定连接 IP，拒绝内网目标及凭据 URL；不下载正文、不证明正文未变。最近 unavailable 记录会使依赖用途需复查；unknown 保持不确定。检查带时间，后续网页变化不会被后台自动发现。

## 运行、候选与审查

`run-start / run-complete / run-fail / run-resume` 接收调用者报告的阶段输入和结果，不会自动执行任意程序。实际执行已接入的原文工具时使用：

```bash
pnpm creator:system --vault .local/creator-vault run-tool \
  --project PROJECT-ID --tool search --arguments /path/to/search-arguments.json --key RUN-KEY
```

参数文件例如 `{"query":"关键词","source_version_id":"SOURCE-VERSION-ID","topk":5}`。已接入工具仅有 `search / source-read / evidence-read`。执行器把真实参数、来源版本、允许工具、结果、错误和耗时连入 run/receipt；完全相同且输入仍有效的完成结果可以复用。工具或模型配置改变不能冒用旧运行。未接入的工具由助手显式执行、保存真实结果再提交记录；begin_run 不表示任务已经执行。

`claim-register / draft-register / review / release-prepare` 均使用 `--spec <JSON文件>`，字段对应 [workflow-controls.md](workflow-controls.md) 的方法参数。例如观点：

```json
{
  "project_id": "PROJECT-ID", "claim_id": "CLAIM-ID", "claim_type": "paraphrase",
  "text": "候选主张", "boundaries": "适用边界",
  "evidence_links": [{"evidence_id":"EVIDENCE-ID","relation":"supports"}]
}
```

稿件：

```json
{
  "project_id": "PROJECT-ID", "note_path": "40 内容项目/项目/主稿.md",
  "claim_ids": ["CLAIM-ID"], "draft_id": "DRAFT-ID",
  "paragraphs": [{"paragraph":2,"claim_ids":["CLAIM-ID"]}]
}
```

段落序号是去掉 frontmatter 后按空行分块，标题也计一个块。系统保存对应块哈希；不会自动识别未被列入映射的新事实。审查：

```json
{
  "target_kind": "draft", "target_id": "DRAFT-ID",
  "checks": [{"name":"原文与推论检查","passed":true,"details":"实际检查范围"}],
  "reviewer_type": "ai", "reviewer": "实际执行者标识",
  "conclusion": "pass", "issues": []
}
```

只应在实际检查后填写。助手仍须执行语义审查、反例检查和范围判断；review 记录不证明调用者没有撒谎或判断一定正确。pending/fail 保留异议；解决时用新的 pass 和 `supersedes` 明确引用被解决的 review ID。新异议或解决记录不会使旧作者确认自动复活。

```bash
pnpm creator:system --vault .local/creator-vault propose \
  --note '40 内容项目/项目/主稿.md' --candidate /path/to/candidate.md --expected-hash ORIGINAL-SHA256
pnpm creator:system --vault .local/creator-vault inspect --kind review --id REVIEW-ID
pnpm creator:system --vault .local/creator-vault impact --kind source --id SOURCE-ID
```

propose 只存候选，不覆盖原稿；基线不同返回 conflict，需人工比较合并。impact 列出间接依赖，inspect 判断输入版本有效性，不能将 valid 翻译成“事实正确”。

## 预览、决定和交付

```bash
pnpm creator:system --vault .local/creator-vault preview --draft DRAFT-ID \
  --assets .creator-system/assets/PROJECT-v1/assets.json
pnpm creator:system --vault .local/creator-vault release-prepare --spec /path/to/release.json
```

预览统一生成 B 站包，始终读取登记稿件快照；无图时省略 --assets。素材 manifest 和每张原图使用 vault-relative 路径，受项目 read_paths 限制。输出目录包含稿件与素材版本；--output 可指定新目录，受 write_paths 限制。成功导出后登记不可变 preview 和项目 selection；系统首页链接当前选定包。改稿或换图后使用新版本，原稿过期时可保留预览但不切换当前选择。导出失败或并行选择冲突不覆盖旧指向。首页被人工编辑时保留原文并返回刷新警告，预览登记结果单独返回。允许预览过期稿但返回 stale；预览不创建审查、批准或发布记录。

release.json 填 `project_id / draft_id / artifact_dir / review_ids`；artifact_dir 用 preview 返回值。B 站包核对原始稿件哈希、公开 Markdown、输入签名、标题、正文、当前图片及顺序清单，保存完整私有快照。未列入当前 asset-order 的旧图片不进入 release。当前稿件和 pass 审查必须仍有效且无未解决异议。B 站交付目录文件在 prepare 后变化或缺失，将使 release 及作者决定失效；独立快照仍可用于历史核对。旧发布格式不能继续交付，需从登记稿件重新生成 B 站包并审查。

`author-decision --release ... --decision approve|reject --author ...` 需要作者在本地终端输入绑定版本的确认短语；普通管道或 Markdown“已批准”属性不产生决定。本轮未对真实内容执行此操作。它是本机声明，没有强身份认证，也无法抵御具有相同文件权限的程序伪造终端。

`delivery-request / delivery-result / delivery-reconcile` 只登记外部操作意图和调用方提供的回执，不登录、不提交、不核实 B 站。结果未知时禁止换 key/包重复登记请求，先查平台事实再回填。记录 published 也保留 platform_verified=false。

## 备份和恢复

```bash
pnpm creator:system --vault .local/creator-vault backup --to /explicit/backup/directory
pnpm creator:system backup-verify --file /explicit/backup.zip
pnpm creator:system restore --file /explicit/backup.zip --to /new/recovery/directory
```

备份必须放在 vault 之外；快照包含笔记、配置、私有对象及一致的 SQLite 快照，manifest 按文件校验。还检查当前记录与最新修订一致、历史连续、被引用的 blob 存在且正确、依赖指向的历史记录存在且指纹吻合。只检查归档中已有文件的哈希不足以证明这些关系完整。

恢复先捕获稳定的私有归档副本，再验证和提取；每个提取文件再次比对已验证 manifest，避免原ZIP在验证后被替换。只允许恢复到新目录。`restore` 和 `backup-verify` 不需要原库存在，也不要求 `--vault`。原库仍可用时，可显式带 `--vault`，恢复成功后把恢复凭据回填到匹配的备份记录；回填失败不会把已成功的独立恢复误报为失败。

外部原文件路径在另一设备上可能需要重新关联；可通过 `source-recover` 恢复已保存的原始快照，同时保留来源活动版本与撤回决定。

2026-09-22 已对真实库完成一次 `--purpose local_recovery_drill` 的仓库外本地备份与全新目录恢复：126 文件全部匹配，51 条记录、52 条历史修订、33 个被引用快照完整；恢复副本的38篇非模板笔记链接无错误。记录在 `.local/validation/real-recovery-report.json`，归档与副本在其指向的 `.local/recovery-validation/` 子目录。

该演练明确记录 same_filesystem / independent_device unknown；真实独立介质备份目标仍未提供，未配置定时备份、云盘或后台服务。不能把本地恢复验证说成具备独立设备故障恢复能力。系统首页按备份 purpose 区分手动备份和恢复演练。

## 验收方式

```bash
pnpm creator:system-test
node --test scripts/creator_system/article-source.test.mjs scripts/creator_system/bilibili-render.test.mjs scripts/creator-validate.test.mjs
python3 -B scripts/obsidian-bridge.test.py
```

测试用合成 TXT/HTML/EPUB/PDF 与临时库，CLI集成测试实际调用现有 Node 导出器。覆盖错误定位、损坏、版本变化、撤回、未解决异议、错误缓存复用、跨项目归属、中断恢复、人工改稿冲突、未知交付、防覆盖恢复及对象损坏。

独立交叉审查复现并修正了：待审查结论误作通过、模型/工具变化仍复用旧结果、跨项目归属穿透、晚到否决不影响旧批准。先前触发场景已复验拒绝。测试通过证明相应行为，不证明所有模型观点正确。

## 首期审稿工作台与变更影响

```bash
pnpm creator:system --vault .local/creator-vault review-import \
  --draft DRAFT-ID --packet '40 内容项目/项目/审稿材料/packet.json' \
  --analysis '40 内容项目/项目/审稿材料/analysis.json' \
  --review '40 内容项目/项目/审稿材料/review.json'
pnpm creator:system --vault .local/creator-vault dashboard
pnpm creator:system --vault .local/creator-vault draft-impact \
  --draft DRAFT-ID --review IMPORTED-REVIEW-ID --input '40 内容项目/项目/修改副本.md'
```

导入要求三份文件与原稿、来源卡处于项目读取范围；实际重新计算 packet 并验证 analysis/review 身份。按真实原文匹配工作流段落块，重复或歧义不猜测。每项意见生成独立、可重复导入的 needs_review 记录，保存原始三份文件的私有快照、问题、原句、理由、影响、选项和不确定性。即便外部报告标记 resolved/dismissed，导入也只登记待审候选。

工作台按项目最新登记稿件展示具体意见、原文与候选观点对应、当前选择的预览。重要程度为编辑候选判断；不能用 valid 或结构覆盖率声称事实准确。解决意见使用现有 review --spec：对同一目标和同名检查作真实 pass 复查，通过 supersedes 指明旧审查；来源卡变化后还需显式 context_paths 保存重新检查的材料。未处理的意见不会仅因其来源卡变化就消失。

改稿影响读取旧审稿的不可变 packet/analysis，与指定的新稿比较；原句唯一且未变的段落给出映射候选，新增、修改和重复歧义单列。不会改写原稿、自动注册新稿或沿用旧审查批准。恢复到新 vault 后，来源卡按旧稿件位置推导的 vault-relative 路径重新解析。

本机首期已接入 5 个来源版本、17 条原文摘录、14 条候选观点，27 个正文块有映射。书籍与三份网页保存完整快照；PNAS 保存本轮网页读取取得的短摘录，capture_scope=excerpt，未保存全文或复算数据。来源卡和原稿未改写。四项既有语义意见均保留待处理，另有作者内容审阅待完成记录。

## 记录审稿处理并关联修订

对工作台中的具体意见记录处理意向，无需手写 review JSON：

```bash
pnpm creator:system --vault .local/creator-vault review-action \
  --draft DRAFT-ID --finding IR-F01 --action revise \
  --reason '说明选择的修订方案与仍需复查之处' --actor '实际处理者' \
  --candidate '40 内容项目/项目/修订候选.md'
```

`--action` 支持 revise（计划修订）、retain（保留原文）、defer（暂缓）。`--candidate` 可省略，仅 revise 可关联；原稿不会因此被覆盖。意见编号在本稿内必须唯一，否则用 --review 提供完整审查记录 ID。同一稿件/意见连续提交相同内容会复用记录；改变意向再改回会保留新的历史记录。人或助手身份均为调用者声明，处理记录不产生作者批准。

成功记录会刷新系统首页。页面显示最近处理、理由、记录者、候选链接及有效性；材料变化后显示需重新检查。处理意向始终不解除异议，后续仍需通过 review --spec 对具体目标作真实复查。保留原文可以有充分理由，但“保留”本身不等于问题已解决。

登记新稿时，默认以前一份最新登记稿件为 parent；同项目内需要分支时可在 draft-register spec 中明确 parent_draft_id。新稿保存父稿当时未解决审查的不可变引用；正文变化不会让这些意见丢失，旧 pass/作者批准也不会直接成为新稿批准。原有历史稿件不做追溯改写。

新稿的工作台将继承意见标为“旧稿意见，需对照新稿复查”，原句和行号明确属于旧稿。对新稿复查时，可用 supersedes 引用其 inherited_reviews 中的审查 ID，并覆盖旧检查名称；普通无关 pass 不能解除它们。一份分支的复查不会解决另一份分支的意见。旧稿的处理意向不会自动显示为新稿的当前处理。

原语义影响分析仍以其 packet/review 对应的稿件为基线。继承意见不表示已把旧分析重新绑定到新正文；需要新分段时重新生成材料。
