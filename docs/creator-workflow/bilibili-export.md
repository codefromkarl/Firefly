# B 站文字专栏交付适配

适配器把已完成的 Markdown 稿件转为标题独立、正文可复制、插图有清单的本地图文包。它不继续研究观点，不登录、上传或发布。正文清理与图文排版由 scripts/creator_system 内部模块承担。

当前官方专栏入口为 [B 站专栏编辑器](https://member.bilibili.com/york/read-editor)。本轮只读打开入口，未在登录态编辑器写入草稿，未把网络上的字数/图片限制当成平台硬性约束。旧链接是否跳转、平台粘贴结果和图片上传行为，以作者实际打开当前编辑器的结果为准。

## 输入与命令

日常使用 `pnpm creator:system --vault ... preview --draft DRAFT-ID [--assets vault-relative/assets.json]`，调用内部适配器；再按 [系统操作](system-operations.md#预览决定和交付) 完成 release-prepare、作者决定与回填。系统首页根据项目选择显示当前预览，项目卡链接系统首页。未登记的稿件应先建立待审版本；预览不自动产生审查通过记录。

稿件需有且只有一个一级标题。其余正文使用普通段落、二三级标题、加粗、引用、列表和完整公开 HTTPS 来源链接。主稿里的私有 frontmatter 会被剥离；私有双链、本地路径、主动 HTML 和未登记的 Markdown 图片会被拒绝。

```bash
pnpm creator:system --vault '.local/creator-vault' preview \
  --draft 'EP-001-DRAFT-001' \
  --output '.creator-system/exports/EP-001-bilibili-v1' \
  --assets '.creator-system/assets/EP-001-v1/assets.json'
```

`--assets` 无图时可省略；manifest 与原图必须在项目可读范围。`--output` 是 vault-relative 路径，必须在项目可写范围；省略则自动按稿件和素材身份选择版本目录。项目内 vault 只能位于私有 `.local`，产物不进入网站源码。

图片清单：

```json
{
  "schema": 1,
  "images": [
    {
      "id": "book-cover",
      "path": "assets/book-cover.webp",
      "caption": "本期参考书封面",
      "after_heading": "钱可以怎样增加自由",
      "source": "local_catalog"
    }
  ]
}
```

- `path` 相对于 manifest 所在目录，不能用绝对路径、`..` 或符号链接。先把选定图片放在该目录下；适配器不远程下载任何素材。
- `id` 唯一，只用字母、数字、连字符或下划线；`caption` 必填且必须可公开。
- `after_heading` 精确匹配正文中唯一一个标题，在该标题后插入图片；不匹配或有重名时停止并指出问题。省略该字段则放在正文末尾。多个图片在同一位置时按 manifest 顺序排列。
- `source` 为 `provided`（默认，作者提供）或 `local_catalog`（本地书目提供）。这是来源说明，不是许可证明；本机拥有书籍封面文件不代表拥有发行许可。发布前由作者确认使用依据。
- 只接受静态 PNG、JPEG、WebP。每张输入和转换结果上限 20MiB、最多 40 百万像素、每包最多 30 张；这些是本地处理保护，**不是 B 站官方限制**。
- 素材会解码、按方向旋转、去除原始元数据，并输出 JPEG 或 PNG。损坏文件、动画、伪装文件和超限素材均停止处理。

## 产物分别怎么用

| 文件 | 用途 |
| --- | --- |
| `bilibili.html` | 浏览器预览、复制正文富文本、复制标题；预览显示本地图片 |
| `bilibili.txt` | 正文纯文本备用，保留完整来源 URL 与图片位置占位，不包含一级标题 |
| `title.txt` | 单独填写平台标题 |
| `article.md` | 剥离私有元数据的原稿，保留原来的一级标题，供留档 |
| `images/` | 可人工上传的转换后素材；只上传当前 asset-order 列出的图片 |
| `asset-order.json` | 图片次序、相对文件名、插入标题、说明、输出哈希和来源类别；无原文件路径 |
| `delivery.json` | `local_ready`、`platform_preview_pending`、`not_published` 等实际交付状态 |
| `.creator-bilibili.json` | 本地输入签名与生成文件哈希，用于重复导出保护，不需上传 |

表格在交付正文中降级为带表头名称的段落，仍保留单元格里的公开链接。代码块按字面转成引用段落，代码标记不要求平台解析。删除线、任务清单和 Markdown 脚注容易在编辑器中改变含义，因此需要作者先改为明确普通文字与来源链接再导出；工具不会静默丢掉勾选状态或将删除内容当作正常主张。

## 实际交付步骤

1. 浏览器打开 `bilibili.html`，检查标题、正文、来源链接、图片说明和插入位置。
2. 点击“复制标题”，在平台标题栏填写。点击“复制正文富文本”，在平台正文编辑区粘贴。
3. **复制的正文只包含图片文字占位。** 按 `asset-order.json` 的次序上传 `images/` 中的文件，放到对应占位处，再删除占位提示。适配器不把本地图偷塞进 Base64，也不会声称图片已经上传。
4. 检查平台是否保留标题、段落、加粗、引用、列表及可打开的来源链接。格式丢失时使用 `bilibili.txt`，重新设置标题和段落；完整 URL 可以手动保留。
5. 检查封面和插图使用依据、移动端预览以及标题与内容一致性，保存平台草稿后由作者决定是否发布。
6. 实际发布后再记录 URL、平台 ID 和时间。导出成功、复制成功、保存本地 HTML 都不表示平台发布成功。

浏览器禁止剪贴板 API 时，会显示并选中无本地图的正文，提示使用 Ctrl+C / Cmd+C 手动复制。页面还提供“显示手动复制正文”按钮，方便直接选择文字。复制与预览按钮属于交付界面，不会进入所复制的文章正文；来源说明和许可待确认信息也保留在交付说明区。

## 重复运行与验证边界

重复导出只更新本工具登记且未经手工修改的文件。marker保存输入内容哈希及签名，读取时核对其一致性；签名损坏或旧marker缺少输入描述时停止，并要求使用新目录。它是本地一致性检查，不是加密签名或强身份认证。发现同名手工文件、手工改动、符号链接或不安全输出位置时停止；换一个输出目录即可继续。移除图片的 manifest 不会删除旧目录中的文件；当前 `asset-order.json` 是本包应使用的图片清单，完整换稿时推荐新建输出目录。

本地自动检查：

```bash
node --test scripts/creator_system/article-source.test.mjs scripts/creator_system/bilibili-render.test.mjs
pnpm exec biome check scripts/creator_system/article-source.mjs scripts/creator_system/article-source.test.mjs scripts/creator_system/bilibili-render.mjs scripts/creator_system/bilibili-render.test.mjs
```

测试实际启动 Chromium，读取复制按钮产生的 HTML/纯文本 Blob，将 HTML 插入本地 contenteditable，检查标题、加粗、引用、列表、来源链接、图片占位和失败后的手动选择。它验证的是本地复制数据与浏览器 DOM；剪贴板接口在测试中受控，不是 B 站登录编辑器兼容性验收。平台粘贴、实际上传和发布保持待作者执行。
