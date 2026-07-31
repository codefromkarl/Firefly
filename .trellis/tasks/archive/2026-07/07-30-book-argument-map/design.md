# 书籍论证结构与响应式知识导图技术设计

## 0. 最新公开展示合同

用户最新决策将单书详情收敛为静态三段式页面，并要求前两节全部以调研来源
为依据。阅读理由与声望背书分开存储，书籍 frontmatter 使用：

```ts
introductions: Array<{
  text: string;   // 1..240 字，出版社/官方介绍短译文或中文摘引
  source: string; // 1..120 字，含翻译性质说明
  url: string;    // 可核对的原始来源
}>;
readingReasons: Array<{
  title: string; // 1..60 字，编辑导航标题
  kind: "insight" | "scope" | "perspective" | "readability" | "application" | "boundary";
  text: string;
  source: string;
  url: string;
}>;
endorsements: Array<{
  text: string;
  source: string;
  url: string;
}>;
excerpts: Array<{
  text: string;   // 1..240 字，经原书核对
  source: string; // 1..120 字，原书定位
  url?: string;   // 无本地版本时，可公开核对的原文 URL
}>;
```

`introductions` 至少一项；`readingReasons` 为 2–4 项且同一本书的 `kind`
不可重复；`endorsements` 为 0–3 项；`excerpts` 可为空。当前 17 本策展
书目执行更高的编辑覆盖门槛：三条互补介绍、至少两条不同维度的阅读理由、
至少三处跨章节/论述阶段的短摘抄。页面不读取相邻图谱，也不渲染 Markdown
正文：

```text
外部来源 → 人工选择短段、翻译并记录署名/URL
  ├─ introductions → 整本书介绍 + 原始来源链接
  ├─ readingReasons → 具体读者价值 + 依据来源链接
  ├─ endorsements → 可选声望背书，视觉降级
  └─ excerpts     → 经典摘抄 + 可选公开核对链接 / 未核对空状态
```

`description` 继续服务 SEO/JSON-LD。书单卡片复用首条 `introductions`
作为预览，不再消费无来源 `whyRead`。逐书来源与选择规则记录在
`research/book-source-citations.md`。

第二节的公开标题为“这本书值得看的地方”。理由卡使用编辑短标题帮助扫描，
但正文和价值判断必须能回到来源；“作者很伟大”“必读经典”等泛赞誉只进入
`endorsements`，不能满足 `readingReasons` 的数量与维度门槛。

第一节采用“完整封面 + 连贯简介”的静态布局：

```text
移动端：2:3 封面容器，object-contain → 书名/作者 → 书籍简介 → 去重来源
桌面端：完整封面                         | 书名/作者/简介/来源
```

`introductions` 的三条文本仍分别覆盖起点、范围和落点，但渲染为连续段落，
不加引号、不重复卡片边框。来源通过 URL 去重后集中显示。详情封面允许出现
背景留白来兼容 0.62–0.75 的现有封面比例，不能使用 `object-cover` 换取
满铺效果。

`graph.json` 和已有图谱实现保留但不进入公开单书渲染路径。这样既落实“去掉
所有知识图谱”的展示要求，也避免在没有明确删除授权时不可逆销毁历史资料。

### 0.1 全站导航生命周期

页面动画拆成两个互斥阶段：

```text
真实 document 加载
  └─ .onload-animation 可执行一次

Swup 客户端导航
  ├─ visit:start: animation.animate = false
  ├─ fetch/cache/history/head 更新照常执行
  ├─ content:replace.before: 从待插入 document 移除 .onload-animation
  └─ 配置的所有容器不透明地原子替换
```

该策略由 `Layout.astro` 统一持有，不由书籍、文章或导航栏组件分别判断。
路由可以声明滚动特例，但不能重新引入退场/入场动画。这样消除两个独立动画
所有者叠加产生的空白帧，同时保留 Swup 的无刷新导航、缓存、进度条、历史和
DOM 生命周期。

## 1. 设计目标

在不改变 Firefly 静态内容架构和现有关系网络的前提下，为 `bookMap` 增加
部分级论证细节与成熟度，并让同一份数据同时驱动：

1. 桌面多栏长卷导图；
2. 移动端单列论证主线；
3. 现有 Cytoscape 概念关系探索；
4. 后续书籍的本地 AI 候选生成与人工审核。

首个复杂样例是《象与骑象人：幸福的假设》。图谱整体标记为
`reading`，只依据用户提供的笔记；四个部分均进入整书主线，前两个部分
深度展开，后两个部分标记为 `outline`。

## 2. 调研结论

长书不能可靠地压成一次提示词中的一组名词关系。BookSum 把长文本总结明确
划分为段落、章节和整书三个粒度，并指出跨全书的因果、时间与篇章结构是核心
难点；递归式书籍总结研究同样采用分解后再汇总的路径：

- https://arxiv.org/abs/2105.08209
- https://arxiv.org/abs/2109.10862

知识图谱生成也应保留来源单元，并将提取、归并和总结拆开。GraphRAG 的索引
数据流先从文本单元提取实体、关系和主张，再归并描述；Tree-KG 则先利用教材
本身的树形结构建立显式图谱，再逐步扩展。EDC 进一步表明“提取—定义—
规范化”比无约束地一次生成大图更适合复杂 schema：

- https://microsoft.github.io/graphrag/index/default_dataflow/
- https://aclanthology.org/2025.acl-long.907/
- https://aclanthology.org/2024.emnlp-main.548/

因此本项目采用“结构先行、逐层生成、来源回指、最终规范化”的本地流程，
不直接引入 GraphRAG、向量数据库或运行时模型依赖。

## 3. 数据模型

### 3.1 保留的三层结构

```text
BookMapData
  └─ parts / transitions       作者顺序和整书认知推进
       └─ argumentCards        部分内部的机制、证据、表现、方法和边界

BookGraphData
  └─ nodes / edges             跨部分复用的概念网络
```

现有字段继续是“问—答—接”的唯一来源：

- `part.question` → 问；
- `part.thesis` → 答；
- `BookMapTransition` → 接。

新增 `argumentCards` 只承载不会与上述字段重复的五类细节：

```ts
type BookArgumentCardKind =
  | "mechanism"       // 机
  | "evidence"        // 证
  | "manifestation"   // 症
  | "practice"        // 法
  | "boundary";       // 界
```

渲染层把三类主干字段与五类细节合并为“问—答—机—证—症—法—界—接”
八种视觉语义，避免同一问题、答案和交接在 JSON 中重复维护。

### 3.2 部分成熟度

```ts
type BookMapPartMaturity = "outline" | "developing" | "developed";
```

- `outline`：只有总纲，明确显示“待补充”；
- `developing`：已有部分论证卡，但尚未形成较完整闭环；
- `developed`：问题、回答、细节卡和交接已经可读。

`BookMapPart.maturity` 在 schema 中默认 `developed`，
`argumentCards` 默认空数组，从而兼容《爱的艺术》和未来旧数据。

### 3.3 论证卡

```ts
interface BookArgumentCard {
  id: string;
  kind: BookArgumentCardKind;
  title: string;
  summary: string;
  context: BookArgumentContext;
  conceptNodeIds: string[];
  provenance: BookGraphProvenance;
  sourceRefs: BookGraphSourceRef[];
}

type BookArgumentContext =
  | "book_argument"
  | "external_research"
  | "cross_book"
  | "personal_reflection";
```

`context` 回答“这张卡在当前分析中扮演什么来源范围”，
`provenance` 回答“这段公开文字是如何形成的”。两者正交：

| context | 用途 | 示例 |
| --- | --- | --- |
| `book_argument` | 当前书及其笔记中的论证 | 负面偏好、互惠 |
| `external_research` | 笔记引入的外部研究 | 双胞胎研究、暴力研究 |
| `cross_book` | 与其他书的概念关联 | 《思考，快与慢》 |
| `personal_reflection` | 阅读者实践或反思 | 冥想体验、信息环境观察 |

首版不扩展图谱顶层 `basis`。所有样例卡仍回指用户提供的 `notes` 定位；
在没有原始论文或原书文件时，`context=external_research` 只表示笔记中的
外部研究线索，不表示本站已经核验该研究。

### 3.4 构建期校验

扩展现有 `bookMap` 的 `superRefine`：

- 全图范围内论证卡 ID 唯一；
- `argumentCards[].conceptNodeIds` 全部指向现有节点；
- 每张卡至少关联一个概念节点和一个来源引用；
- 来源依据继续复用现有 `validateEvidence`；
- `outline` 部分不得包含论证卡，防止“待补充”与已展开内容矛盾；
- 新编写并标记为 `developed` 的部分应包含论证卡；旧图谱通过 schema
  默认值保持兼容，不追溯强制旧的 `developed + []` 数据补卡；
- 旧 JSON 未声明新字段时由 schema 默认值保持兼容。

共享常量、TypeScript 类型、Zod schema 和 UI 标签分别由当前既有边界持有：

- `src/types/book.ts`：领域常量、类型与显示标签；
- `src/content.config.ts`：运行时内容校验；
- Svelte 组件只消费已校验数据，不自行解析原始 JSON。

## 4. 展示架构

### 4.1 单一语义 DOM

继续扩展 `BookMapSpine.svelte`，不创建第二套“海报组件”。同一组有序部分在
窄屏是单列，在桌面通过 CSS Grid 变为横向栏道，避免重复 DOM、重复来源标记
和不一致的屏幕阅读器顺序。

```text
核心问题 + 全书主张
        ↓
┌─────────┬─────────┬─────────┬─────────┐
│ 内部协调 │ 社会互动 │ 追寻幸福 │ 精神超越 │
│ 问 / 答  │ 问 / 答  │  总纲   │  总纲   │
│ 细节卡   │ 细节卡   │ 待补充  │ 待补充  │
│ 交接     │ 交接     │ 交接    │         │
└─────────┴─────────┴─────────┴─────────┘
        ↓
全书阶段性结论
```

### 4.2 响应式策略

- `< 1024px`：保持当前纵向时间线；卡片按问题、回答、细节、交接顺序阅读。
- `≥ 1024px`：部分容器使用横向 grid，每个栏道具有可读最小宽度；
  当部分过多时只允许导图容器内部水平滚动，不让页面根节点溢出。
- 连接线由 CSS 伪元素/边框绘制并标记为装饰；移除连接线后，标题与文本顺序
  仍能表达关系。
- `prefers-reduced-motion` 下不增加滚动或强调动画。

### 4.3 视觉层级

- 书级问题/主张：高对比主卡；
- 部分标题：编号、论述角色、成熟度；
- 问/答：固定的主干色；
- 五类细节：使用可控标签色与短标题，不用装饰性 AI 图片承载含义；
- 外部研究、跨书关联、个人反思：显示 `context` 标签；
- 来源与可选短摘录：继续复用 `BookGraphEvidence`，默认折叠；
- `outline`：显示真实的空状态和所缺内容，不渲染空卡片骨架。

关系探索仍由现有 Cytoscape 页签按需加载。默认打开全书主线时不 import
Cytoscape，也不把长卷实现为 canvas 或静态位图。

## 5. 样例内容

新增目录：

```text
src/content/books/the-happiness-hypothesis/
  index.md
  graph.json
  cover.webp
```

元数据：

- 标题：《象与骑象人：幸福的假设》
- 原名：The Happiness Hypothesis
- 作者：乔纳森·海特
- 状态：`reading`
- 图谱阶段：`reading`
- 分类：`psychology-and-relationships`
- 内容依据：`notes`
- AI 辅助：`true`

封面不复制未知授权的出版社图片；制作一张原创的简洁象/骑象人抽象封面，
只承担书单识别用途。

四个整书部分：

1. 内部协调：`developed`
2. 社会互动：`developed`
3. 追寻幸福：`outline`
4. 精神与超越：`outline`

内容压缩原则：

- 不把用户粘贴的每一段变成卡片；
- 合并同层重复内容，保留“机制—证据—表现—方法—边界”的最短闭环；
- “《思考，快与慢》”“鲍迈斯特研究”等标为跨书或外部研究线索；
- 药物与心理治疗内容只做书中/笔记观点的概括，并保留“需咨询专业人员”
  的边界，不提供个体医疗建议；
- 个人冥想实践和媒体观察使用 `personal_reflection`，不并入作者论证。

## 6. 书单分类与基础书目导入

### 6.1 第四个主分类

在 `BOOK_SHELF_VALUES` 与 `BOOK_SHELF_LABELS` 增加：

```ts
"literature-and-life": "文学与人生"
```

该分类承载叙事、回忆录和文学性人生书写，包括《蛤蟆的油》《小王子》和
《风沙星辰》。书单筛选、左侧目录和 URL 状态继续从共享常量派生，不在组件
中维护第二份分类列表。新增分类不会改变既有三类 slug 或公开 URL。

### 6.2 下载目录导入边界

`/home/yuanzhi/下载` 只作为本地只读输入，不进入仓库。先按文件哈希、作品名
和格式关系整理 14 本独立书籍：

- 已有 5 本复用现有条目；
- 新增 9 本创建独立内容目录；
- 《金钱心理学》的重复 EPUB 不重复导入；
- 《斑马为什么不得胃溃疡》的 PDF/EPUB 合并为同一作品；
- 1 页工作材料和 3 页个人笔记不作为书籍。

每本新增书只提交以下派生产物：

```text
src/content/books/<stable-slug>/
  index.md
  graph.json
  cover.webp
```

元数据优先读取 EPUB/PDF 内嵌信息，文件名只用于交叉检查。封面优先从合法
持有的本地 EPUB 提取，统一转换为适合列表和详情页的低分辨率 WebP；不提交
原始 EPUB/PDF、完整目录转储或连续正文。

新增 9 本默认 `status=wishlist`、`graphStage=preview`。最小图谱只依据
元数据和目录，以 `editorial_inference` 标记短摘要、节点和关系，不声称是
个人读后结论，也不生成细粒度论证卡。

### 6.3 《小王子》和《风沙星辰》

另行增加两个稳定目录：

```text
src/content/books/the-little-prince/
src/content/books/wind-sand-and-stars/
```

两本均属于 `literature-and-life`，作者规范为安托万·德·圣埃克苏佩里。
《小王子》的原名使用 `Le Petit Prince`；《风沙星辰》的法文原名使用
`Terre des hommes`，并在正文说明英文版名 `Wind, Sand and Stars`。

用户确认两本均已读过，因此书单使用 `status=read`。当前没有个人笔记或
人工复核图谱证据，图谱仍使用 `graphStage=preview`，节点采用
`editorial_inference`，页面明确区分阅读状态与图谱成熟度。两本只交付可访问
的基础详情和最小关系图，不扩展为本任务的细粒度论证卡样例。

两本没有指定中文版本，不写入可能错误的 ISBN、译者或出版社信息。封面使用
不复制商业版式的原创、版本中性视觉，并压缩为 WebP。

### 6.4 总量与一致性

实现后公开书目总数为 17 本：

- 既有 5 本；
- 《象与骑象人：幸福的假设》1 本；
- 下载目录新增 9 本；
- 《小王子》《风沙星辰》2 本。

每个非草稿书目必须恰好对应一个同 slug 图谱，且 `book.graphStage` 与
`graph.stage` 一致。`status` 表达用户阅读进度，不与图谱阶段强绑定。

## 7. 本地 AI 生成工作流

新增：

```text
docs/book-argument-map-ai-workflow.md
docs/templates/book-argument-map.candidate.json
scripts/validate-book-map.ts
```

工作流分五阶段，每阶段产生可人工查看的中间结果：

1. **来源清单**：按章节/笔记块编号，记录可用依据和缺失范围；
2. **整书骨架**：识别书型、核心问题、全书回答、部分顺序、认知输入/输出；
3. **论证展开**：只对依据充分的部分生成五类细节卡，并为每卡回指来源；
4. **概念规范化**：合并同义节点、生成关系、把卡片关联到稳定节点 ID；
5. **反向审计**：从每个公开结论返回来源，检查虚构、来源越界、层级混淆和
   不成熟部分。

提示词要求模型只输出候选 JSON，不输出最终图片。模型供应商只要能按给定
JSON 结构输出即可；严格结构化输出可用时优先使用，之后仍必须执行本地校验。

`scripts/validate-book-map.ts <slug>`：

- 校验 slug 和目标路径，禁止任意路径输入；
- 确认 `index.md` / `graph.json` 存在；
- 调用 Astro 内容同步/检查，使校验复用生产 schema，而不是复制一套规则；
- 只读验证，不改写候选内容。

## 8. 兼容、风险与回滚

### 兼容

- 新字段均由 schema 提供默认值；
- 没有 `bookMap` 的既有和新增基础书目仍进入原分组概览；
- 《爱的艺术》保持原 JSON 不变，也能进入新的响应式主线组件；
- 节点、关系、书单筛选、Swup 和 JSON-LD 不改变公共 URL 或状态合同。

### 风险

- 长卷信息过密：以卡片数量上限、短总结和详情折叠控制；
- 多栏在中等宽度难读：1024px 以下强制单列，桌面只在容器内滚动；
- 内容来源混淆：`context`、`provenance`、`sourceRefs` 三层共同展示；
- 医疗内容误导：保留边界卡和页面免责声明，不新增诊疗结论；
- AI 输出看似完整：成熟度与人工审核清单阻止缺失内容被隐藏。
- 批量书目元数据漂移：保留来源清单，未知 ISBN/译者不猜测，构建前检查
  标题、作者、slug、分类、阅读状态和图谱阶段。
- 商业封面版权与构建体积：只提交本地输入的压缩派生图或原创版本中性封面，
  不复制原始电子书和高清封面。

### 回滚

- 删除新增书目录、文档模板和校验脚本；
- 从共享书单常量移除 `literature-and-life`，前提是先移除属于该分类的
  新增书目录；
- 从 `BookMapPart` 移除新增可选字段；
- 恢复 `BookMapSpine.svelte` 的原单列样式。

三部分互不改变现有公开数据 ID，回滚不需要迁移数据库或外部状态。
