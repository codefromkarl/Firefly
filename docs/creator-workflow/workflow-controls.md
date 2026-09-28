# 任务、审查与交付控制

本地显式运行的记录引擎位于 `scripts/creator_system/workflow.py`，使用共享 Store 保存记录历史与按内容哈希寻址的私有快照。它不调用模型、不执行来源中的命令、不联网提交内容，也不安装后台任务、hooks 或全局强制机制。CLI 和系统首页是这一引擎的入口；系统设计与唯一验收清单仍在 [system-design.md](system-design.md)。

## 输入与项目范围

项目必须明确稳定 ID、目标、`scope.read_paths`、`scope.write_paths`、允许的 `tools`、是否允许联网以及 `max_attempts`。路径是 vault 内相对路径；绝对路径、上级目录跳转和符号链接被拒绝。`.` 可作为项目范围前缀，表示整个 vault。来源文件由来源接口登记为明确版本；引用必须逐一列出 evidence ID，不能只写书名或 URL。

scope 控制这些显式接口可读的笔记和可收集的产物位置。它不改变操作系统权限，不能限制本会话其他具有文件访问能力的工具，也不是强安全隔离。程序不会因为 network=true 就自行联网；它只保存作者规定的范围。

每次输入快照同时记录：

- vault-relative 笔记路径及原始文件 SHA-256；
- Store 对象的 kind、稳定 ID、revision、digest；
- 项目记录，及对象已有的递归依赖。

依赖变化后 `inspect` 派生 `stale`，不会篡改历史审查或以前发布的事实。证据仍能在旧快照中重放，不代表适合当前继续引用：来源被撤回、活动版本改变、原文件变动或所有原始位置不可用，都会使相关当前用途过期。

显式网页访问检查最近记录为 unavailable 时，也会使该来源的依赖用途需复查；unknown/not_checked 保留不确定性，不被改写成可访问。HEAD可访问不证明正文一致。

## 运行与恢复

`begin_run(project_id, stage, inputs, idempotency_key, tools=[], model=None)` 按项目、阶段、输入快照、幂等键生成同一个运行 ID。完全相同的运行重复 begin 返回原记录，不产生第二次执行；相同幂等身份却改变 tools 或 model 会拒绝复用，必须明确新键与允许范围。**这个接口本身从来不执行工具**。

运行只用三个状态：`running → completed / failed`。工具版本和模型可由调用方写入；无法取得的费用是 `cost: null / cost_status: unknown`，不估算成零成本。

- `finish_run` 保存结果回执及耗时，结束前重新检查输入是否仍一致。
- `fail_run` 保留错误回执；失败材料和过去尝试不会消失。
- 进程中断后，对仍为 running 的记录调用 `resume_run`，保留原尝试次数并记录恢复位置；不会自动重复上次工具调用。
- 对明确 failed 的记录 resume 算一次新尝试。限制按同项目、同阶段、同输入汇总，不能换幂等键绕过次数上限。
- 有外部副作用的交付使用后文独立状态，不能用普通 run 恢复推断“可以重发”。

候选写回由主控接口承担：读取版本与当前原稿不一致时保留候选及冲突信息；默认不覆盖作者的原文件。

## 观点、稿件与审查

`register_claim` 接受明确 `claim_type`：`paraphrase / quotation / empirical / synthesis / personal_judgment`。证据关系必须分别记录 `supports / contradicts / limits / unrelated`。只有个人判断可以没有证据链接；有链接也不自动表示论证充分。程序不做语义判断，不把“引用齐全”叫事实正确。

观点更新必须传 `expected_digest`；并行修改发生冲突时拒绝覆盖。候选观点永远不会因为登记成功而变成作者认可。

`register_draft` 每次生成独立版本，保存原稿字节快照与 claim IDs。段落映射为：

```json
[{"paragraph": 2, "claim_ids": ["C1"]}]
```

`paragraph` 是剥离文件开头 frontmatter 后，按空行分块的 1-based 序号，标题也算一个块。登记时保存每块的 hash，拒绝越界位置、未登记观点和未被使用的 claim ID。这个映射能帮助定位审查问题；它并不自动发现未被作者列入映射的新事实。

`record_review` 绑定精确目标记录和递归依赖；检查项形如 `{"name":"引用字面核对","passed":true,"details":"..."}`。审查者可声明 ai、program 或 human，但记录明确标为 caller-declared，身份没有被认证。所有 review 的 `author_approved` 固定为 false，检查结论不能充当交付决定。结论枚举为 `pass / needs_review / fail`；即使所有局部检查都为 true，needs_review 仍不能进入发布包。

后续出现同版本观点、稿件或发布包的 negative/pending 审查，会阻止旧发布包继续交付。新 positive 审查不会静默抹去旧异议。解决异议时，必须记录一份 `pass` 重查，通过 `supersedes: [review_id]` 明确覆盖旧记录，并包含旧记录的全部检查名称；历史异议仍保留。新的异议及其解决记录构成作者决定的 review frontier：即使解决后旧发布包又可用，早先的作者批准仍过期，必须在处理结果明确后重新确认。无关的新 positive 审查不会使作者决定失效。

有效性规则：

- 改动稿件文件，关联稿件、审查、发布包与作者决定均 stale。
- 修改某条观点，只影响依赖该观点的记录，不影响无关观点的审查。
- 来源撤回或换版，经证据依赖传播到稿件与发布包。
- 内容完全改回原字节，且全部依赖也恢复到原内容，原审查可以重新 valid。这是按内容哈希复用的明确设计，不依据“后来发生过编辑”永久作废。历史修订和运行日志仍保留；如果新发现的异议没有体现为来源撤回或内容变更，必须另外登记审查/问题。

项目流程状态由 `project_status(project_id)` 从事实派生，返回 status、stage、next_action 和 basis，不改写项目合同的 digest。它依次关注未回查的交付、调用方报告的发布/失败、未完成或失败运行、当前稿件与审查、作者决定和准备进度。`project.data.status=defined` 只是初始记录，不是工作台的当前状态；工作台应调用派生接口。报告 published 时仍明确 platform_verified=false。

项目所属的 claim、draft、review、release、decision、run、delivery 不能通过输入快照混入另一个项目，更新 claim 不能转移其所属项目。来源和证据可以由不同项目明确引用，保留跨项目资料复用。

`inspect(kind,id)` 给出 valid/stale 和具体原因。`impact(kind,id)` 查找间接依赖，可从 source、source_version、evidence、claim 一直追到稿件、审查和交付。

## 发布包与作者决定

`prepare_release(project_id, draft_id, artifact_dir, review_ids, release_id=None)` 只接受 `.creator-bilibili.json`，核对原始稿件身份、输入签名、公开 Markdown、标题、HTML/TXT 正文、delivery 与 asset-order、当前所有图片哈希。清单内图片必须齐全、顺序唯一且与 marker 一致；未选中的残留图片不纳入交付。旧格式不再进入准备或交付接口；历史记录保留但标记失效，必须重新生成并审查。原稿、依赖和至少一份对应审查必须有效，不能有失败检查或未解决异议。完整产物保存为独立私有 blob。B 站 release 保存格式与原交付目录；该目录中的登记文件变动使 release/decision stale，历史快照不丢失。

CLI 的 preview 只调用内部 B 站适配器；release-prepare 仅校验并登记既有产物，不自行导出。导出标记是本地一致性凭据，不是签名或外部安全认证；拥有同一文件系统权限的人可以修改脚本与数据库，不能声称本系统抵御这种主动篡改。普通导出只得到预览，prepare_release 得到 prepared，都不表示公开发布。

`record_decision` 必须在交互 TTY 中输入包含动作、release ID 和精确 release digest 的完整确认短语。普通字符串字段、AI审查结论、管道标准输入不能产生通过该接口的批准。系统保存 `local_interactive_tty_attestation` 和 `authenticated_identity: false`：这是本机作者声明，不是强身份认证，也无法从技术上区分有同等权限的自动化程序伪造终端。文档和界面必须维持这个边界。

决定绑定发布包及其全部依赖。变更后需要新的当前版本决定；仅修改 Markdown 中的“已批准”属性不会生效。最新明确 reject 会阻止继续交付。

## 交付与结果未知

`request_delivery` 保存本地交付请求记录，不发送网络请求；`tool_executed=false`、`platform_verified=false`。调用者须在它之外取得真实平台操作授权。`submitted` 表示该本地请求已登记，不是系统声称已向平台发出请求。

`record_delivery_result` 记录调用方报告的 `published / failed / outcome_unknown` 与明确 reference；即使状态是 published，也仍显示 `caller_reported_external_fact`，系统没有联网验真。不要把这条记录描述成已证明的平台发布事实。

同一项目同一渠道存在 submitted 或 outcome_unknown 时，新幂等键、新发布包也不能绕过它重发。unknown 后只能 `reconcile_delivery`，必须提供平台回查、人工核对或其他可追溯 reference；本地接口仅记录回查结果，本身不执行回查。记录确认 failed 后，才可以讨论新的请求。已记录 published 的相同产物不能重复提交；实际内容修订需要新的版本与决定。

测试只用合成来源、合成项目和 FakeTTY fixture 检验上述行为，不涉及真实内容、用户授权、平台调用或发布。

## 预览记录与语义审查附加材料

preview 保存 project/draft、产物目录、各产物 blob/hash 与依赖，是不可变记录。selection 是项目当前预览指针，以 expected digest 更新，独立于项目合同避免切换预览让研究资料全部过期。CLI 在导出前读取指针版本；完成包校验后才选择，失败保留旧选择。新指向的稿件、图片或标记变化会使预览失效，历史快照仍保留。

record_review 支持 context_paths、attachments、findings 与可选 review_id。来源上下文路径进入依赖快照，附加材料必须存在于经过校验的 blob。结构化意见必须锚定当前稿件原句与段落哈希；语义导入额外验证原始行号与分析身份。导入意见不生成 pass 或 author approval。未解决意见在同一目标版本上的阻止作用不会因外围来源卡变化而自动消失；显式新复查需要当前 context_paths 与同名检查及 supersedes。新稿必须重新审查，历史稿件意见单独保留。

数据库 audit/恢复校验包含 preview 产物和 review 附件，缺少任意引用数据均失败。项目所有权检查包含 preview/selection，不能跨项目混用。

## 修订传承与处理意向

register_draft 增加 parent_draft_id，可显式选择同项目父稿；省略时选择项目最后登记稿件。inherited_reviews 捕获父稿当时仍需处理的 review 引用，不作为旧稿依赖快照递归传播，避免改稿后的正常失效阻止登记新稿。引用身份和项目仍需校验。发布判断、项目状态和作者决定的 review frontier 包含这些意见；只有本稿明确覆盖同名检查并 supersedes 的有效 pass 才能处理它们，不能借另一分支的复查消除。

record_action（editorial.py）为当前稿件的一个未解决审查记录 revise/retain/defer、理由、声明者、可选候选文件快照和上下文版本。review_action 不可变；连续重复可复用，意向变化通过 previous_action_id 保留历史。它不进入解决异议集合，也不产生 author_approved。原候选被修改或丢失时记录失效，原候选字节仍保存在私有 blob。审计/恢复验证包含父稿、继承审查、处理历史和候选 blob。
