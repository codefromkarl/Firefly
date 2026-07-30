# 书单与书籍知识图谱技术设计

## 1. 设计目标

在 Firefly 的 Astro 静态构建中增加一个独立的书籍领域：

- `/books/` 提供可搜索、可筛选的想读书单；
- `/books/<slug>/` 提供静态可索引的书籍详情页；
- 每个详情页包含一个 Svelte 5 可探索知识图谱；
- 所有书籍与图谱在构建期校验，不引入数据库、服务端 API 或运行时 AI；
- 首版内容透明标记为预读知识地图，不冒充用户读后总结。

## 2. 架构边界

### 2.1 构建时职责

Astro 负责：

- 从 EPUB 一次性整理元数据、封面和候选内容；
- 通过 Content Collections 加载并验证书籍 Markdown 与图谱 JSON；
- 生成书单和详情静态页面；
- 优化封面、输出 SEO 元数据、Book JSON-LD 和 Pagefind 可索引文本；
- 把最小、已验证的普通对象传给 Svelte 岛。

### 2.2 浏览器职责

Svelte/Cytoscape.js 负责：

- 书单的关键词和主题筛选；
- 图谱节点选择、邻居高亮、节点类型与关系类型筛选；
- 平移、缩放、适配视图和重置；
- 将画布选择与 HTML 节点详情/列表同步；
- 监听容器和主题变化，并在组件销毁时完整清理。

浏览器不负责：

- 读取 EPUB；
- 调用 AI 或外部书籍 API；
- 校验图谱引用；
- 保存阅读状态或修改图谱。

## 3. 文件布局

```text
src/
├── content/
│   └── books/
│       ├── thinking-fast-and-slow/
│       │   ├── index.md
│       │   ├── graph.json
│       │   └── cover.webp
│       └── <book-slug>/
│           ├── index.md
│           ├── graph.json
│           └── cover.webp
├── components/
│   └── pages/
│       └── books/
│           ├── BookLibrary.svelte
│           ├── BookCard.svelte
│           └── BookKnowledgeGraph.svelte
├── pages/
│   └── books/
│       ├── index.astro
│       └── [...slug].astro
├── types/
│   └── book.ts
└── utils/
    └── book-utils.ts
```

`graph.json` 和 `index.md` 分离，以保持长文笔记与结构化图数据各自易维护。
二者由 collection reference 建立显式关联。

## 4. 内容集合

### 4.1 `books`

使用 `glob({ pattern: "**/index.{md,mdx}" })`，稳定 ID 为书籍目录 slug。
schema 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `title` | string | 中文展示书名 |
| `originalTitle` | string optional | 原文书名 |
| `authors` | string[] | 一名或多名作者 |
| `description` | string | 中性书籍简介 |
| `previewFocus` | string | 预读关注点，不声称是读后评价 |
| `status` | enum | `wishlist` / `reading` / `read` |
| `shelf` | enum | 每本书唯一的稳定主分类 |
| `topics` | string[] | 书单筛选主题 |
| `language` | string | BCP 47 风格语言 |
| `isbn` | string optional | 仅在 EPUB 元数据可靠时使用 |
| `cover` | image() | 与 Markdown 相邻的本地 WebP |
| `draft` | boolean default false | 生产构建过滤 |
| `graphStage` | enum | `preview` / `reading` / `reviewed` |
| `published` | date optional | 书籍出版信息可靠时使用 |

Markdown 正文允许包含：

- 内容说明；
- 预读关注点；
- 阅读问题；
- 后续逐步补充的阅读笔记。

首版不得写个人评分、已读结论或暗示用户已经阅读。

### 4.2 `bookGraphs`

使用 `glob({ pattern: "**/graph.json" })`。schema 字段：

```text
book: reference("books")
title: string
stage: "preview" | "reading" | "reviewed"
basis: ("metadata" | "toc" | "epub" | "notes")[]
aiAssisted: boolean
layout: "cose" | "breadthfirst" | "circle"
summary: string
nodes: BookGraphNode[]
edges: BookGraphEdge[]
```

节点：

```text
id: stable kebab-case string
label: string
kind: "core" | "concept" | "model" | "bias" | "practice" | "outcome" | "chapter"
summary: string
chapter?: string
anchor?: string
importance?: 1 | 2 | 3
```

边：

```text
id: stable kebab-case string
source: node id
target: node id
relation:
  "part_of" | "explains" | "contrasts" | "causes" |
  "supports" | "applies_to" | "leads_to"
directed: boolean
summary?: string
```

内部 ID 与关系类型使用稳定英文值；用户界面显示中文标签。

### 4.3 完整性校验

图谱对象级 schema 追加 `superRefine`：

- 节点 ID 唯一；
- 边 ID 唯一；
- 每条边的 `source` 和 `target` 均存在；
- 不允许自环，除非未来需求明确开放；
- 至少一个 `core` 节点；
- `anchor` 必须为页面内 slug 形式；
- `stage=preview` 时不能声明 `basis=["notes"]` 为唯一来源；
- `stage=reviewed` 需要 `notes` 来源。

跨集合使用 `reference("books")` 保证图谱不会指向不存在的书籍。

## 5. 首版内容范围

| 书籍 | 图谱依据 | 目标规模 | 用途 |
| --- | --- | --- | --- |
| 《思考，快与慢》 | metadata + toc + epub | 约 25–40 节点 | 完整交互样本 |
| 《金钱心理学》 | metadata + toc | 约 8–15 节点 | 中小型概念图 |
| 《被讨厌的勇气》 | metadata + toc | 约 8–15 节点 | 章节定位样本 |
| 《纳瓦尔宝典》 | metadata + toc | 约 6–12 节点 | 双主题小图 |
| 《爱的艺术》 | metadata + toc | 约 6–12 节点 | 紧凑小图 |

节点数量是内容预算，不是质量替代指标。每条公开关系都应能由目录结构或本地
EPUB 内容支持，不发布长篇摘录。

## 6. 页面设计

### 6.1 书单页

`books/index.astro`：

- 构建时加载非草稿书籍；
- 使用 Astro 图片管线生成卡片封面 URL；
- 通过布局输出 SEO 标题和说明；正文不额外渲染重复的书单介绍卡，筛选区直接
  作为主内容入口；
- 将书籍卡片投影传给 `BookLibrary.svelte client:load`。

`BookLibrary.svelte`：

- 搜索范围：书名、作者、主题；
- 筛选：阅读状态、主题；
- 默认顺序：状态优先级后按书名；
- URL 查询参数可选作为增强，不作为首版阻塞项；
- 无结果状态与清除筛选按钮；
- 书卡始终链接到稳定详情 URL。

首版 5 本均为 `wishlist`，但保留状态筛选合同以支持用户之后更新。

### 6.2 详情页

`books/[...slug].astro`：

- `getStaticPaths()` 从 `books` 集合生成；
- 读取匹配的 `bookGraphs` 条目；
- 使用 `MainGridLayout` 和 `Markdown` 渲染；
- 显示封面、作者、想读状态、主题、预读关注点和图谱来源说明；
- 输出 Schema.org `Book` JSON-LD；
- 挂载 `BookKnowledgeGraph.svelte client:visible`；
- Markdown 与图谱 HTML 文本参与 Pagefind 索引。

找不到匹配图谱属于构建错误，而不是运行时空白状态。

## 7. 图谱交互

采用 Cytoscape.js 3.x；调研时 npm 当前版本为 3.34.0、MIT License。依赖只在
图谱岛可见时加载，避免进入首页或书单页就下载图谱运行时代码。

### 7.1 可视交互

- 点击节点：选中节点、突出一阶邻居和连接边、降低其他元素透明度；
- 点击空白或“清除选择”：恢复全图；
- 节点类型筛选与关系类型筛选；
- 放大、缩小、适配视图；
- 节点可拖动，画布可平移，触屏可双指缩放；
- 详情面板显示节点说明、类型和关联关系；
- 有 `anchor` 时提供“前往相关章节”链接。

### 7.2 布局

- 默认使用 Cytoscape 内置 `cose`，避免新增布局扩展；
- 小图可以在 `graph.json` 中选择 `circle` 或 `breadthfirst`；
- 初次布局不播放持续动画；
- `prefers-reduced-motion` 下所有过渡关闭；
- 容器 ResizeObserver 触发 `resize()` 与受控 `fit()`。

### 7.3 主题

Cytoscape Canvas 不能可靠直接消费 CSS 变量。组件在挂载时读取站点计算颜色，
并通过一个限定范围的 MutationObserver 监听根元素主题属性变化，重新应用
图谱样式。observer 在 `onDestroy` 中释放。

## 8. 无障碍与静态降级

图谱画布不是唯一内容入口：

- Svelte SSR 输出完整节点列表、关系列表和当前节点详情；
- 节点列表使用原生按钮，可通过键盘选择并同步画布；
- 所有图谱控制按钮有文字或可访问名称与可见焦点；
- 当前详情变化通过适度的 `aria-live` 区域提示；
- `<noscript>`/SSR 内容仍可阅读图谱摘要与关系；
- 颜色之外使用节点形状、文字类型和关系标签区分类别；
- 移动端提供“图谱 / 结构列表”切换，默认不产生横向页面溢出。

## 9. SEO 与搜索

详情页输出：

- 页面 `title`、description 和 `og:url`（沿用 Layout）；
- Schema.org `Book` JSON-LD：`name`、`author`、`inLanguage`、`isbn`、
  `image` 和 description，仅输出存在且可靠的字段；
- 图谱阶段与来源的可见说明；
- Pagefind 可索引的预读关注点、节点摘要与关系文本。

书单即时筛选使用传入数组，不调用 Pagefind。全站搜索仍可找到书籍详情页。

## 10. EPUB 处理与内容边界

EPUB 只作为一次性的本地输入：

- 读取 OPF 元数据与 NCX/nav 目录；
- 提取选定封面并转为低分辨率 WebP；
- 《思考，快与慢》允许读取正文以整理原创概念摘要；
- 其他四本只使用元数据、目录和简介；
- 不把 EPUB、完整章节、可还原原书的大段摘录或临时解包文件提交到仓库；
- 图谱摘要用重新组织的短文本，不以连续原文摘录构成。

## 11. 兼容性与迁移

- 新功能不恢复已移除的 Bangumi 路由或运行时 API；
- 可复用现有状态文案、分页和卡片视觉模式，但不让 `UserSubjectCollection`
  泄漏到新书籍领域；
- 所有内部链接通过 `url()` 或基于 Astro `base` 的构建时 URL；
- 根域构建与 `/Firefly/` 子路径构建均必须正确；
- 未来从 `wishlist` 更新到 `reading/read` 只需修改内容元数据；
- 从预读图谱升级为正式图谱时修改 `stage`、`basis` 和节点内容，不改 URL。

## 12. 失败与回滚

- schema、引用或图完整性错误：构建失败，不生成部分错误页面；
- Cytoscape 加载失败：保留 SSR 节点与关系列表并显示非阻塞错误提示；
- 封面处理失败：构建失败并定位具体书籍，不静默发布破图；
- 图谱性能或交互不可接受：可移除 Cytoscape 岛，保留书单、详情页和静态关系
  列表作为可回滚的最小产品；
- 不修改现有 posts、Bangumi API 或全站搜索合同，降低回滚影响面。

## 13. 本地思维导图制作工具

当前 Cytoscape 岛是读者侧的展示器，不承担 EPUB 导入、节点编辑和关系编排。
首阶段的制作工具应放在 Firefly 仓库内，例如 `tools/book-map-studio/`，并通过
`pnpm book-map` 仅在本地启动：

- 读取本地 EPUB、目录、笔记或现有 `graph.json`；
- 提供树形分支编辑、节点搜索、关系编辑和构建期校验反馈；
- 将人工确认后的结果写回
  `src/content/books/<slug>/graph.json`；
- 不进入线上构建，不提供公网写接口，也不需要数据库、账户或 API 鉴权。

同仓库能让编辑器与 `src/content.config.ts` 共用一份 schema，并让内容变更与
站点预览在同一个 Git 提交中审查。只有当工具需要服务多个仓库、形成独立产品、
独立发布版本或支持多人协作时，才抽为独立仓库/package；届时仍以带版本的
graph schema 文件为边界，而不是让网站运行时调用编辑服务。

## 14. 书籍目录型左侧栏

`MainGridLayout` 提供可选的 `left-sidebar` 命名插槽。存在该插槽时：

- 隐藏全局 Profile/Categories/Tags 左栏；
- 在 Swup 管理的 `#left-sidebar-dynamic` 容器中渲染页面目录；
- 书单首页按主分类提供可折叠的全部书籍目录；
- 单书详情显示全部书籍、当前书籍位置和本页区块/Markdown 章节；
- 768px 及以下沿用站点单栏布局，不额外渲染底部重复目录。

由于全局左栏是静态 DOM，而自定义左栏属于 Swup 动态容器，Layout 的生命周期
逻辑必须在初次加载、内容替换和历史返回后，根据动态目录标记切换全局左栏。

## 15. 书单分类与筛选方案

### 15.1 信息模型

分类、主题和阅读状态使用三个正交维度：

- `shelf`：稳定的主分类，建议每本书只选择一个，用于左侧目录分组；
- `topics`：一本书可拥有多个细粒度主题标签，用于交叉筛选；
- `status`：`wishlist`、`reading`、`read` 等阅读状态，不参与内容分类。

首批 5 本书建议采用三个主分类：

| 主分类 | 书籍 |
| --- | --- |
| 认知与决策 | 《思考，快与慢》 |
| 财富与成长 | 《金钱心理学》《纳瓦尔宝典》 |
| 心理与关系 | 《被讨厌的勇气》《爱的艺术》 |

这样可以避免为 5 本书建立 5 个近似标签式分类。现有“认知科学”“财富”
“心理学”“哲学”等继续保留为可多选主题。

### 15.2 左侧目录

书单首页左侧栏只承担稳定导航：

1. “全部书籍”返回未筛选的书单首页并显示总数；
2. 各主分类使用原生 `details/summary` 折叠分组，显示分类数量和该分类下的全部
   书籍；
3. 书单筛选不会隐藏或删除目录书目；当前分类只使用轻量描边/底色提示；
4. 单书详情自动展开当前书籍所在分类，以更强的左侧标记和底色标识当前书籍，
   并在下方继续显示“本页目录”。

左侧不再重复阅读状态、主题和清除筛选控件，避免稳定导航与临时结果集混在同一
视觉层级。

### 15.3 单一筛选状态

筛选条件以 URL 查询参数作为唯一状态来源，例如：

```text
/books/?shelf=wealth-and-growth&status=wishlist&topic=心理学&q=风险
```

- 主区域的搜索框和分类/状态/主题下拉控件读写同一组查询参数；
- 初次加载、刷新、Swup 导航及浏览器前进/后退都从 URL 恢复状态；
- 左侧目录不持有筛选状态，只根据主分类参数展开并轻量提示对应目录分组；
- 不使用独立 DOM 事件或全局 store 同步两个界面，避免重复状态和生命周期漂移；
- 空参数表示“全部”，清除筛选移除所有书单查询参数。

### 15.4 主区域控件

书单主区域保留关键词搜索，并按“主分类、主题、阅读状态”提供筛选控件。结果区
明确显示“符合条件的书籍数量”和当前条件；窄屏下主区域控件承担完整操作能力，
不依赖桌面左侧栏。主区域是筛选的唯一交互入口。

### 15.5 已确认决策

用户确认每本书只有一个 `shelf`，同时保留多个 `topics`。这避免目录出现重复
书籍和重叠计数，并保持分类与标签的语义边界。左栏目录与结果筛选分工明确：
目录保持完整、可预测，主区域负责改变结果集。

## 16. 单书结构概览与内容证据

### 16.1 三种阅读方式

单书详情使用同一份 `BookGraphData`，提供三个互补视图：

1. “结构概览”是默认入口。先显示核心节点，并按 `chapter` 分组显示
   `importance=3` 的关键节点；每组允许按需展开其余节点。
2. “关系探索”使用现有 Cytoscape 画布，显示完整节点和带类型关系，继续支持
   筛选、邻居高亮、缩放和平移。
3. “结构列表”输出全部节点和关系，作为移动端、键盘、无脚本、搜索索引和图谱
   加载失败时的稳定文本入口。

书单首页继续承担目录、分类和筛选职责。全部书籍尚未形成经用户复核的正式图谱
前，不增加跨书语义网络。

### 16.2 内容分层

公开页面遵循“总结为主、原文为证、个人观点单独呈现”：

- `summary` 是默认可见的重新组织短文本；
- `sourceRefs` 提供来源类型和章节/位置；可选 `quote` 只能是短摘录，并在
  `<details>` 中按需展开；
- `provenance=source_summary` 表示基于正文或个人笔记重新表述；
- `provenance=editorial_inference` 表示根据目录、结构或概念关系作出的编辑整理
  判断，不冒充作者明确论证；
- `provenance=personal_note` 只用于用户阅读后的个人记录。

完整 EPUB、完整章节和连续长摘录仍不进入仓库或公开构建产物。

### 16.3 数据合同

节点增加：

```text
provenance: "source_summary" | "editorial_inference" | "personal_note"
sourceRefs:
  - basis: "metadata" | "toc" | "epub" | "notes"
    locator: string
    quote?: short string
```

关系增加同样的 `provenance`，并允许可选 `sourceRefs`。构建期校验：

- 每个 `sourceRefs[].basis` 必须包含在图谱顶层 `basis` 中；
- `source_summary` 至少引用 `epub` 或 `notes`；
- `personal_note` 至少引用 `notes`；
- `quote` 有严格长度上限，避免提交长篇原文；
- 关系没有直接文本证据时使用 `editorial_inference`。

首批迁移采取保守策略：《思考，快与慢》中依据 EPUB 整理的章节概念标记为
`source_summary`；其他四本只依据元数据和目录，节点与关系标记为
`editorial_inference`。所有关系在没有逐条原文位置前均视为整理推断。

## 17. 整书主线与概念网络分层

`graph.json` 可以增加可选 `bookMap`，在保留 `nodes` / `edges` 概念网络的同时，
显式描述作者的全书组织方式。没有 `bookMap` 的旧图谱继续使用章节/主题分组
概览；存在 `bookMap` 时，默认概览改为全书主线。

`bookMap` 包含：

- `archetype`：论证型专著、渐进式对话、主题短论集、编纂型文集或叙事作品；
- `coreQuestion`、`thesis`、`conclusion`：带来源性质和定位的书级陈述；
- `parts`：稳定 ID、顺序、论述角色、本部分问题与主张、进入/离开时的认识变化、
  关联概念节点和内容依据；
- `transitions`：部分间的方向、关系、交接理由和内容依据。

构建期必须校验部分/交接 ID、交接端点、关联概念节点和从首部分出发的可达性；
`bookMap` 的所有公开陈述继续遵守图谱级 `basis`、`provenance` 和短摘录约束。

读者侧继续由同一个 `BookKnowledgeGraph` 岛提供三种视图：

1. “全书主线”：按作者顺序展示核心问题、每部分的论述作用、认知推进和交接；
2. “关系探索”：使用 Cytoscape 浏览完整概念网络；
3. “结构列表”：提供所有概念与关系的 HTML 降级入口。

首个样板使用《爱的艺术》的四章目录，把原先缺失的第三章社会诊断补回主线。
由于该书首版内容依据仍为 metadata + toc，所有主线表述均标记为整理推断，不
声称来自逐段正文核验。
