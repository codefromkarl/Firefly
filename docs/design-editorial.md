# Editorial 暗色先锋设计系统（Redesign Notes）

本次重构把 Firefly 主题（CodeFromKarl）从"色相驱动的柔和卡片风"改造为
**暗色先锋 Editorial**：近黑画布、发丝线分隔、克制圆角、巨幅字标、克制动效。

## 设计原则

- **暗色优先**：`siteConfig.themeColor.defaultMode = "dark"`；浅色模式为"纸面暖灰"变体，同一令牌双模式自动适配。
- **中性面与色相解耦**：`--hue` 只作用于强调色（`--primary`），所有中性面固定近黑（258° 零彩度）或暖纸面。
- **发丝线 > 阴影**：分隔优先 `1px var(--line-divider)`；阴影仅用于悬浮层。
- **圆角收敛**：卡片 16px → 6px（`--radius-large`），微件/方章 2–4px。
- **图标统一 Lucide、界面零 emoji**（见"图标系统"节）。

## 令牌层（src/styles/variables.styl）

保留全部 169 个历史变量名，仅重铸取值；新增语义均通过 color-mix 派生：

- 暗：`--page-bg oklch(.135 .005 258)`、`--card-bg oklch(.163 …)`、墨色 `--deep-text oklch(.925 …)`
- 浅：纸面 `oklch(.972 .0035 90)`、暖墨 `oklch(.21 .012 70)`
- 强调：暗 `.76 .15 var(--hue)` / 浅 `.52 .15 var(--hue)`

## 字体体系（src/config/fontConfig.ts）

- **正文**：Inter（拉丁）+ 系统中文字体栈
- **显示/字标**：Space Grotesk（导航标题、Hero、横幅）
- **代码/眉标/序号**：JetBrains Mono
- 由 Astro Font API 构建期下载并子集化（18 个字体文件）

## Editorial 样式层（按加载序追加于 main.css）

| 文件 | 职责 |
|---|---|
| `editorial.css` | 基底：画布色、电影颗粒（body::after 静态噪点）、选区、焦点环、眉标/发丝线/上升入场工具类、链接基态、view() 滚动入场 |
| `editorial-components.css` | 导航字标、首页 Hero 单色巨字、文章索引行式目录（CSS 计数器序号 + 发丝线）、页脚配套 |
| `editorial-content.css` | 文章版心 46rem、正文排版（h2 发丝线锚、引用左竖线、代码/表格/链接）、文章横幅 |
| `editorial-books.css` | neutral-* 灰阶 → 令牌映射（全站）、图书卡、引文块、封面褪色 hover |
| `editorial-widgets.css` | Widget 外壳去卡化 + 眉标标题、分类条药丸、分页、PostMeta 去图标圆块 |

## 关键页面处理

- **首页**：Hero 壁纸灰度化（`grayscale .62` 双模式变体）+ Space Grotesk 大写巨字
  （10.5cqw 容器等比，1440px 下单行精确贴合）；下方文章列表为发丝线行式目录（01/02/03 计数器）。
- **文章页**：banner 灰度同族；阅读版心 46rem；正文 17px/1.95；引用/表格/代码全部发丝线化。
- **图书库**：透明图书卡 + 4px 描边、封面褪色 hover、mono 眉标；详情页引文块无色块化。
- **404**：巨型描边数字（JetBrains Mono + 1px 发丝描边）。

## 图标系统

- 全站唯一来源 **Lucide**（`@iconify-json/lucide`），经两条渲染路径：`astro-icon`（.astro）与本地离线 `Icon.svelte`。
- 语义级映射表见迁移脚本历史；`scripts/generate-icons-data.ts` 扫描源码自动精简生成
  `src/constants/icons-data.json`（当前 106 图标），已接入 `pnpm build`；`pnpm icons` 可手动再生成。
- 品牌图形（GitHub 等）一律收敛为 Lucide 或纯文字。

## 质量门

- `pnpm type-check` / `pnpm check` / `pnpm build`（LQIP → icons → Astro → 字体子集 → Pagefind）
- `pnpm visual-check`：无头 Chrome 计算样式断言（暗色类、颗粒层、令牌解析、圆角、字体加载、零 emoji、无 console 错误），覆盖 `/` `/books/` `/posts/*` `/404`；截图输出至 `.redesign-shots/`（已 gitignore）。
- 移动端与浅色模式以 Playwright 视口/令牌探测复核。

> 已知取舍：light 模式为"纸面变体"而非独立设计；动效（view timeline 入场）对不支持滚动时间线的浏览器自动降级为静态。
