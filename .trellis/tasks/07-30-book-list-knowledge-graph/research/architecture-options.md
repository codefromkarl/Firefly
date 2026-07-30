# 书单与书籍知识图谱技术调研

## 当前仓库证据

- `src/content.config.ts` 已用 Astro Content Collections、glob loader 和 Zod
  schema 管理 Markdown/MDX 内容，适合增加独立 `books` 集合。
- `src/pages/posts/[...slug].astro` 证明仓库已有“集合条目 → 静态路径 →
  详情页”的成熟模式。
- `src/components/pages/anime/AnimeGrid.svelte` 已提供 Svelte 5 的搜索、筛选、
  排序、分页和详情交互范式，可复用书单页的交互组织方式。
- 仓库还保留已停用的 Bangumi 书籍分类、阅读状态、卡片和分页组件，但
  `siteConfig.pages.bangumi` 为关闭状态且公开路由已移除。配置账户的公开
  API 当前仅返回 3 条书籍记录，不足以成为知识书单的主要数据源；实现时应
  复用交互模式而不是恢复运行时 Bangumi 依赖。
- `astro.config.mjs` 集成 Swup，交互图谱必须在 Svelte 生命周期中创建和销毁，
  不能依赖一次性全局脚本初始化。
- 现有 Mermaid/PlantUML 管线擅长构建期静态 SVG、缩放和全屏，但没有知识图谱
  所需的节点选择、邻居高亮、关系过滤和详情面板。
- 站点支持根路径和子路径部署，书籍详情、封面和图谱中的内部链接必须使用现有
  URL 解析约定。

## 内容存储选项

### A. 单个 Markdown/MDX 条目，图谱位于 frontmatter

优点：

- 单本书的元数据、图谱和长文笔记位于同一个版本化文件。
- 可直接使用 Astro glob loader 和 schema。
- 构建时可检查节点 ID、边端点、状态和日期。

缺点：

- 大图谱的 YAML frontmatter 可读性会下降。
- 不能直接用可视化画布编辑器维护。

适合约 10-50 个节点的人工策展型图谱。

### B. Markdown 书籍条目 + 相邻 JSON Canvas `.canvas`

JSON Canvas 1.0 是开放、MIT 授权的文件格式，顶层为 `nodes` 和 `edges`；
节点带稳定 ID、位置和尺寸，边带起点、终点、方向和标签。它最初为 Obsidian
创建，也允许其他工具自由实现导入、导出和存储。

优点：

- 可以在 Obsidian 等支持 JSON Canvas 的工具里可视化编辑。
- 已保存节点位置，网页无需每次运行力导向布局。
- 文件可读、可版本控制、可迁移。

缺点：

- 标准节点偏“无限画布卡片”，不是语义知识图谱；节点类型、关系类型、章节锚点
  等领域信息需要约定扩展字段或单独元数据。
- Astro 默认 glob 示例主要覆盖 Markdown/JSON/YAML/TOML；`.canvas` 需要通过
  `import.meta.glob`、构建脚本或自定义 loader 接入。

适合用户已有 Obsidian Canvas 工作流、重视手工排版的情况。

### C. 每本书独立 JSON/YAML 图谱 + Markdown 书籍条目

优点：

- 图谱 schema 清晰，便于 AI 生成、程序检查和未来复用。
- 可将展示布局与领域数据分开。

缺点：

- 同一本书分成两个来源，需要显式定义关联和一致性检查。
- 手工编辑体验不如 JSON Canvas。

适合图谱较大或未来需要批量处理、AI 辅助生成的情况。

## 渲染方案比较

| 方案 | 优势 | 主要限制 | 适合范围 |
| --- | --- | --- | --- |
| 复用 Mermaid/现有 SVG 管线 | 不增依赖、构建期输出、首屏与 SEO 好 | 节点详情、邻居高亮、关系筛选弱 | 只读关系图 |
| D3 force + SVG | 完全可定制，`d3-force` 和 `d3-zoom` 能覆盖布局与交互 | 需要自行实现选择、样式、标签、碰撞、销毁和无障碍 | 强定制的小图 |
| Cytoscape.js | JSON 可序列化、内置触控手势、事件、样式、图算法和多种布局 | Canvas 渲染仍需 HTML 文本替代；新增客户端依赖 | 10-500 节点的可探索图谱 |
| Sigma.js + Graphology | WebGL 面向数千节点，适合大网络 | 双依赖、布局和内容面板需额外实现，小图收益有限 | 千级以上全站网络 |

初步推荐 Cytoscape.js：单本书图谱通常不会达到 Sigma.js 的大图规模，但比
Mermaid 需要更强的选择、过滤和邻居探索能力；相较 D3，它减少自建图交互和
布局的维护面。

## 推荐的静态数据流

```text
books Markdown/MDX + graph data
            |
            v
Astro Content Collection schema
            |
            +--> 书单静态数据 --> Svelte 筛选岛
            |
            +--> getStaticPaths --> 单本书静态详情页
                                  |
                                  +--> HTML 元数据、笔记、关系文本列表
                                  |
                                  +--> Svelte 图谱岛 --> Cytoscape.js
```

领域 schema 至少应包含：

- Book：`title`、`authors`、`status`、`rating`、`topics`、`cover`、
  `isbn`、`published`/`finishedAt`、`draft`、`summary`。
- Graph node：`id`、`label`、`kind`、`summary`，可选 `chapter`、
  `anchor`、`url`、`importance`。
- Graph edge：`id`、`source`、`target`、`relation`、可选 `directed`、
  `summary`。

在 schema 形状校验之外，还需要一次图完整性校验：

- 节点 ID 和边 ID 唯一；
- `source`/`target` 均指向存在节点；
- 内部锚点和内部 URL 可解析；
- 至少存在一个核心节点；
- 生产环境排除草稿。

## 无障碍与降级

Cytoscape.js 和 Sigma.js 都以 Canvas/WebGL 为主。HTML Canvas 规范指出，
交互区域需要与可聚焦的回退内容建立一一对应关系。因此图谱不能是知识内容的
唯一呈现方式：

- 图谱旁提供可键盘操作的节点列表或关系列表；
- 选择列表项时同步高亮图中节点；
- 每个节点说明以普通 HTML 呈现；
- 图谱容器提供名称、操作说明、重置视图按钮；
- 尊重 `prefers-reduced-motion`，避免持续力导向运动；
- 小屏默认降低标签密度，并允许切换到“结构列表”。

## 搜索与 SEO

- 单本书详情页输出 Schema.org `Book` JSON-LD，包括书名、作者、ISBN、语言、
  封面和简介等存在的字段。
- 书单页内部的即时筛选可以直接使用构建时传入 Svelte 的书籍数组；无需为了
  几十或几百本书调用 Pagefind。
- 详情页应纳入现有 Pagefind 索引；如需全站搜索按主题或阅读状态过滤，可通过
  `data-pagefind-filter` 增加过滤元数据。
- 图谱文本摘要和关系列表应存在于静态 HTML 中，确保可索引和无脚本可读。

## 内容生产策略

### 人工策展

精度和表达最好，维护成本最高。适合首批 5-10 本代表性书籍。

### AI 辅助、人工发布

AI 从目录、读书笔记或合法持有的摘录生成候选节点和边；构建前由人检查命名、
重复概念、关系方向和证据。适合规模化，且不会把模型推断直接当成事实。

### 全自动

上线最快，但容易生成过密、重复、缺乏证据或误解作者论点的关系。首版不建议。

推荐采用“人工定义核心节点和关系词表 + AI 生成候选 + 人工校对发布”。

## 本地 EPUB 书库评估

用户提供的 `/home/yuanzhi/下载` 中有 15 个 EPUB 文件、14 本独立书；
《金钱心理学》的两个文件 SHA-256 摘要一致，可视为重复文件。读取 EPUB 的
OPF 与目录后，以下书籍最适合首版可探索图谱：

1. 《思考，快与慢》：目录天然形成“系统 1/系统 2 → 启发式与偏见 →
   过度自信 → 选择与风险”的层次，适合作为首本完整图谱。
2. 《金钱心理学》：章节围绕运气、风险、复利、致富/守富、自由、容错空间等
   独立又相关的概念，适合中等规模关系图。
3. 《被讨厌的勇气》：对话结构下有目的论、人际关系、自卑、课题分离等明确
   概念，适合展示节点到笔记章节的跳转。
4. 《纳瓦尔宝典》：财富与幸福两条主题线清晰，内容规模适合小型图谱。
5. 《爱的艺术》：篇幅较小，可作为验证“小图谱也能获得完整体验”的样本。

《经济学的思维方式》概念结构很强，但套装规模大，更适合第二阶段；传记类和
自传类书籍更适合时间线或人物关系图，不优先用于验证首版概念图谱。

## 来源

- Astro Content Collections:
  https://docs.astro.build/en/guides/content-collections/
- Cytoscape.js:
  https://js.cytoscape.org/
- Sigma.js:
  https://www.sigmajs.org/docs/
- D3 force:
  https://d3js.org/d3-force/simulation
- D3 zoom:
  https://d3js.org/d3-zoom
- JSON Canvas 1.0:
  https://jsoncanvas.org/spec/1.0/
- Pagefind filtering:
  https://pagefind.app/docs/filtering/
- Schema.org Book:
  https://schema.org/Book
- HTML Canvas fallback:
  https://dev.w3.org/html5/spec-LC/the-canvas-element.html
