# Obsidian 接入与日常使用

本次使用系统已安装的 Obsidian 1.13.7。初次检查没有已注册仓库；已在项目私有目录 `.local/creator-vault` 创建“读书与创作”库，并通过应用的 **Open folder as vault** 动作打开。未安装社区插件，未手工改写全局仓库注册表。应用已自行登记仓库 ID `9bde926564fd9baa`。

当前本机绝对路径：`/home/yuanzhi/develop/ai-research/Firefly/.local/creator-vault`。以后移动仓库时，在 Obsidian 重新选择移动后的文件夹；不用修改网站源码。

## 已完成的应用验证

- 应用实际读取 `首页.md`，打开主页，并通过 `app.vault.create` 创建 `00 收件箱/连接验证.md`，回读内容一致。
- 打开 `书单.base` 后，原生 Bases 显示 **17 results**，表格显示中文书名、作者和原始阅读状态。
- 主稿实际在 Obsidian 阅读视图打开，标题为 `主稿 - creator-vault - Obsidian 1.13.7`。
- 核心 Templates 与 Bases 均已启用，`.obsidian/templates.json` 持久配置为 `{"folder":"90 模板"}`。
- 应用截图保存在项目私有 `.local/validation/obsidian-home.png`、`obsidian-books.png`、`obsidian-article.png`。临时调试连接只用于本机应用验收，完成后正常重启应用撤去调试端口。

可用 `obsidian://open?vault=9bde926564fd9baa&file=%E9%A6%96%E9%A1%B5` 回到主页；也可以在仓库文件列表点击“首页” → “本期研究与稿件”进入创作导航。

## 本地桥接命令

从 Firefly 项目根目录运行。依赖 Python 3 与 PyYAML（本机已有 6.0.3）；本轮未安装依赖。

```bash
# 默认只计划，无写入。示范内容默认来自 docs/creator-workflow/example-vault。
python3 scripts/obsidian-bridge.py --vault .local/creator-vault

# 创建缺失文件；已有相同文件跳过；任一冲突则整批不写，退出码 2。
python3 scripts/obsidian-bridge.py --vault .local/creator-vault --apply

# 显式指定另一份示范目录。
python3 scripts/obsidian-bridge.py --vault .local/creator-vault \
  --seed docs/creator-workflow/example-vault --apply

# 只有需要刷新本机库存时，才追加 --inventory。
python3 scripts/obsidian-bridge.py --vault .local/creator-vault --inventory
python3 scripts/obsidian-bridge.py --vault .local/creator-vault --inventory --apply

PYTHONDONTWRITEBYTECODE=1 python3 scripts/obsidian-bridge.test.py
```

`.base` 在 Obsidian 初次打开时可能自动重排 YAML 缩进。桥接按 YAML 语义判断这类变化，内容相同就跳过，绝不重写已有表格。其余文件按完整文本判断；任何个人新增笔记都不会被覆盖。源书单更新或示范模板更新后与本地笔记冲突，需人工合并来源变更；目前没有自动合并或双向同步。

本机已完成一次原始导入与示范 seed；最后重跑显示 0 创建、42 不变、0 冲突。之后在 Obsidian 修改笔记出现冲突是保留个人内容的预期行为，导出主稿仍可照常运行，不需要重新导入。

## 文件与字段的职责

| 位置 | 内容 | 日常维护者 |
| --- | --- | --- |
| `10 书籍/<slug>.md` | Firefly 全部 17 本：稳定 slug、作者、原阅读状态、原 graphStage、元数据中的来源标签、原笔记正文 | 初次导入后由用户维护 |
| `20 知识卡片/` | `id`、`claim_type`、支持与反例、核查状态 | 用户与研究助手 |
| `30 主题研究/` | 问题定义、读者、问题递进、跨书综合 | 用户与研究助手 |
| `40 内容项目/` | 项目卡、证据表、主稿、排版验收、发布与反馈 | 用户与编辑助手 |
| `50 来源/` | 网页/论文/书籍来源记录、私有文件库存 | 研究助手与用户核查 |
| `90 模板/` | 书籍、知识卡片、主题研究、来源、内容项目、主稿 | 原生 Templates 插入 |

所有预读标记和阅读状态沿用原记录，导入不把 AI 预读改成人工已读。书籍笔记 `book_id` 使用 Firefly slug；来源、知识卡片、主题与项目使用 `id`。原书单完整元数据放在笔记 YAML 代码块中，方便回查署名、链接、摘录与状态；原电子书正文没有复制进仓库。

模板中新建的 ID、定位和来源必须填写，状态不要因自动导入升级。来源核对、本人认可、稿件审阅和平台发布是四种不同状态。`claim_type` 根据主张性质选择，例如作者观点或综合推论；与本期示例保持同一命名。公开主稿正文使用公开 HTTPS 引用，私有卡片链接放在 frontmatter 或研究页，避免进入最终专栏。

## 全部本地书籍库存

桥接仅扫描以下两个授权范围，排除非电子书扩展名和符号链接；不会扫描整台机器：

- `~/下载/书单`
- `~/Downloads/心理与人文书单`

读取 EPUB ZIP CRC、mimetype、container、OPF 元数据，保存标题、作者、标识符、文件格式、SHA-256 与可读性。PDF/TXT/MOBI 等只登记文件与哈希，其正文/元数据不宣称已检查。SHA-256 相同可证明字节相同；不同文件可能是同一作品的另一版，绝不按文件数自动生成“已读作品数”。

本轮使用已完成的 `本地库存-052e44915b7e` 快照，文件落盘时间为 2026-09-22 11:30:11（Asia/Shanghai）：**376 个电子书文件，87 组字节相同副本，343 个 EPUB 通过基础可读性检查，4 个 EPUB 无法读取，29 个其他格式未做内容有效性检查**。扫描期间目录数量发生变化，因此这个快照不能解释为书库永久总数。初版快照没有内嵌扫描起止时间；新脚本刷新时会写 `scan_started_at`、`scan_finished_at` 与扫描根路径，并对读前读后大小/修改时间变化标记 `unstable_during_scan`，不保留有效哈希判断。

快照 JSON 与可在 Obsidian 搜索的 Markdown 表均只位于私有 `50 来源/`，不会进入 `src`、`public` 或 Git。它们保存文件位置，未把 EPUB/PDF 复制进 Obsidian。4 个损坏文件保留错误状态，不自动修复、删除或用另一副本冒充验证。全库存下一步是按作品/版本人工确认关联到书籍笔记，不能仅按数量推断去重结果。

## 从 Obsidian 到可发布稿件

正文以真实仓库为准，避免编辑完个人库后误导出示范目录的旧稿：

```bash
node scripts/creator-validate.mjs --vault .local/creator-vault
pnpm creator:system --vault .local/creator-vault preview \
  --draft DRAFT-ID --assets '.creator-system/assets/PROJECT-v1/assets.json'
```

先按 [系统操作](system-operations.md) 登记实际主稿版本；DRAFT-ID 使用真实返回值，无图时省略 --assets。默认输出 B 站标题、HTML/TXT 正文及图片上传清单。成功预览会登记版本并更新项目选择，由系统首页显示当前交付目录；打开 bilibili.html 检查窄屏/宽屏。完成审查后 release-prepare，再由作者确认最终包并在平台粘贴、逐张上传图片、检查排版。B 站编辑器能否保留全部格式，以实际平台预览为准。发布后回填真实链接、版本、反馈和纠错；本地预览不表示已发布。

## 日常备份与能力边界

本地文件读写已经接通，不依赖 Obsidian Sync 或付费 API。跨设备同步、独立备份、云盘及自动发布尚未配置；`.local` 被 Git 忽略不等于备份，Obsidian 文件恢复也不等于另一份独立副本。后续选择用户已有备份位置后，可备份整个 vault（包含 `.obsidian`、附件和库存）并做恢复抽查。本次没有自行开通订阅或选择云服务。

官方支持的 [URI](https://obsidian.md/help/uri) 可打开已注册仓库和笔记；[Bases](https://obsidian.md/help/bases) 使用本地笔记属性；[CLI](https://obsidian.md/help/cli) 还需要在应用设置中启用命令行入口。本次不依赖 CLI，也没有安装第三方 REST 插件。已安装应用不等于已注册仓库，本次的完成依据是上面的应用实际读取、写回和界面表格证据。
