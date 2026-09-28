# 来源版本与可重放证据接口

实现位置：`scripts/creator_system/sources.py`。所有原文快照、解析单元及运行记录保存在指定私有 Obsidian vault 的 `.creator-system`；不复制到 Firefly 的 `src`、`public`。无联网、付费服务、OCR 服务或平台账号操作。资料内命令只作为文字，不执行；HTML 不加载资源，不执行脚本。

## 对象身份与不可变性

- `source` 是显式登记的来源身份，独立于作品；`work_id` 可选，不能从文件数量推断作品数。包含多版本、已知文件路径、当前 `active_version_id` 和撤回状态。
- `source_version` 不可变。ID 是 `SV-` 加以下规范 JSON 的 SHA-256：`source_id / source_sha256 / format / url / capture_scope / ocr`。同一来源、相同字节及捕获信息改名不产生新版本，只增加路径；不同来源即使字节相同也不串用标题、URL 或捕获范围。
- 原始字节 blob 单独按 SHA-256 去重。原文件后来改版、消失或改名，不删除旧快照；旧证据仍能回放，但不代表当前审查有效。
- `evidence` 不可变。ID 由 `source_version_id / locator / text_sha256` 决定，此处 `text_sha256` 是所选短摘录的哈希。另存完整原文单元的 `unit_sha256`，防止引用定位对应的上下文被替换。
- 重复创建相同证据先校验回放，再复用原记录。相同段落选择不同短摘录，会生成不同证据 ID。

## 公共函数

函数接收 `creator_system.store.Store` 实例，返回 JSON 可序列化数据。CLI 由上层统一接入；本模块不自行解析命令行。

```python
register_source(store, path, source_id, *, title=None, work_id=None,
                url=None, capture_scope="full", ocr=False, legacy_note=None)
# 返回 source_version record {kind,id,revision,digest,data}

list_units(store, source_version_id)
# [{locator, text_sha256, preview}]，preview 最多 240 字符

read_source(store, source_version_id, locator, *, context=1, max_chars=1200)
# 原文单元、truncated、原文哈希、parser_version、uncertainty、前后上下文
# context 0..3；max_chars 1..4000；各上下文单元最多 240 字符

search(store, query, *, source_version_id=None, topk=5)
# 默认仅当前未撤回版本；显式选择旧版允许历史检索，返回当前source_state
# topk 1..20；score 只是词频，不是事实可信度

create_evidence(store, source_version_id, locator, *, quote=None)
# quote 省略则取单元前 240 字符；显式值必须逐字包含于该单元，长度 1..240
# 返回 evidence record；不是人工核实或语义成立的证据

replay_evidence(store, evidence_id)
# valid=True 表示不可变快照字面回放成功，并返回 quote/locator/source_status

source_status(store, source_version_id)
withdraw_source(store, source_id, reason)

map_legacy_source(store, note_path, source_version_id, *, legacy_verification=None)
# 保留旧笔记文本及哈希，只新增映射；verification 永远 pending_review
```

`locator` 接受 `list_units` 返回的对象，或其 JSON 字符串。定位字段必须全部一致，不能只传章节号模糊匹配：

```json
{"kind":"epub","spine":2,"member":"OPS/chapter.xhtml","paragraph":3}
{"kind":"pdf","page":4,"paragraph":2}
{"kind":"html","paragraph":3}
{"kind":"md","paragraph":1}
{"kind":"txt","paragraph":2}
```

EPUB 按 OPF 的真实 spine 阅读顺序解析，避免按 ZIP 文件名排序误认章节；PDF 用系统已有 `pdftotext -layout` 保留页码；HTML 提取可见文本段落，排除 script/style/head 等；Markdown/TXT 以空行分段。解析单元的段落号属于当前 `parser_version`，不是出版社印刷页码。PDF 没有文本时记录 `requires_ocr`，不能建立假证据。显式登记人工 OCR 文本可用 `ocr=True`，证据一直保留 `ocr_unverified`，需要人工对照原图。

网页只接受**调用者已经取得的 HTML/TXT 文件**与显式 URL。记录 `capture_method=supplied_snapshot`、`network_fetched_by_system=False`、捕获范围 `full/excerpt/unknown`；页面 URL 当前是否可访问是 `web_live_status=not_checked`。系统没有自动联网抓取，也不以一份旧快照宣称网页当前仍然有效。

## 回放与当前适用性分开

回放会重新读取并校验原始 blob、解析 blob，使用指定解析器重新解析原始快照，再核对单元位置、完整单元哈希、短摘录字面和 evidence ID。解析失败、快照损坏、版本不符、错误章节/页码以及字面不一致会抛出 `ControlError`，不返回伪造成功。

`source_status` 返回：

| 字段 | 含义 |
| --- | --- |
| `current_source_changed` | 某个已知原路径仍可读但字节已改变 |
| `active_version_changed` | 来源登记的当前版本已不是此证据采用的版本 |
| `withdrawn` | 用户已显式撤回该来源 |
| `current_source_unavailable` | 所有已知路径都没有读到原版本字节；改名后登记新路径可恢复 |
| `locations` | 每个路径为 unchanged/current_source_changed/missing_or_unreadable |
| `snapshot_available` | 已确认保存的原始快照可读且哈希正确 |
| `parse_status` | parsed/parse_failed/requires_ocr/no_text/extractor_unavailable |
| `web_live_status` | 默认 not_checked/not_applicable；显式web-check后为reachable/unavailable/unknown，带web_checked_at |

`web_access.check_web_source` 是独立的显式 HEAD 探测，不属于原文抓取。它的结果只表明检查时的可访问性，不证明正文未改或观点正确；网络限制与命令入口见 system-operations.md。来源登记拒绝撤回或作品映射冲突时，在创建新版本前退出，避免留下可检索的孤立版本。

`replay_evidence.valid` 只证明历史快照可重放。审查/交付层必须另外检查 `withdrawn`、`active_version_changed`、`current_source_changed`，并处理来源不可用及 OCR 不确定性；不能把历史字面回放成功升级成当前事实正确。改变来源文件后重新登记产生新版本，旧证据仍指旧版。撤回不删除历史记录。

文件捕获前后比较 inode、大小与纳秒修改时间；中途变化会拒绝登记。源文件全程只读。解析错误仍保存真实字节与明确失败状态，方便调查，不生成证据单元。输入上限 128 MiB；EPUB 还有压缩展开上限，不支持路径含 `..` 的章节引用，会明确报解析失败。索引为可从快照重建的解析单元；当前是标准库词频检索，没有向量检索或事实准确率指标。

## 原文件丢失后的恢复

`recovery.recover_source(store, source_version_id, destination=None)` 将校验过的原始字节恢复到新的 vault-relative 文件，并给原source增加该版本的可用位置。默认路径在 `.creator-system/recovered/`。恢复是独立文件，不与不可变blob共用可写inode；同一请求可以复用相同恢复凭据。不同内容的既有目标、越界路径和符号链接均拒绝。

恢复不会重新激活旧版本、解除withdrawn状态或覆盖原始外部路径。历史快照可恢复不等于现在允许继续引用；`source_status` 中原版被替代、原文件改版和来源撤回等事实仍保留。没有这些异议且只是原文件丢失时，找回同一版本字节可使其可用性恢复；没有创建新的审查或作者决定。

## 迁移与验证

旧笔记映射只新增 `source_mapping`，记录相对路径、原文件哈希、对应版本及旧状态标签。即使旧值为 `text_checked`，映射也不会生成 evidence、review 或作者决定，不改写个人笔记。主会话决定实际映射范围并调用接口。

测试使用合成 TXT/HTML/EPUB/PDF，无真实书籍或 provider 请求：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s scripts/creator_system -t scripts -p 'test_sources.py'
```

覆盖真实 EPUB spine、错误章节、来源改版、改名、同字节不同来源、字面引用与长度、损坏 EPUB、HTML 惰性解析、OCR 不确定性、旧笔记保留、撤回、快照调包，以及本机 Poppler 的真实 PDF 页码/无文本检测。缺少 `pdftotext` 时 PDF 集成测试明确 skip，运行接口返回 extractor_unavailable。
