# 书籍论证结构与响应式知识导图实施计划

## 1. 数据合同

- [x] 在 `src/types/book.ts` 增加部分成熟度、论证细节卡类型、内容范围类型和
  对应显示标签。
- [x] 在 `BookMapPart` 增加 `maturity` 与 `argumentCards`，保持现有字段为
  “问—答—接”的规范来源。
- [x] 在 `src/content.config.ts` 增加 Zod schema 默认值和跨引用校验：
  卡片 ID、节点引用、依据、成熟度与卡片存在性。
- [x] 为旧 `graph.json` 验证默认值兼容，不批量改写已有内容。

回滚点：此阶段只涉及共享类型和内容校验；若兼容性失败，撤回新增可选字段，
现有 `bookMap` 数据不需要迁移。

## 2. 书单分类与下载目录导入

- [x] 在 `src/types/book.ts` 增加 `literature-and-life` 与“文学与人生”
  标签，确认书单筛选、URL 恢复和左侧目录继续从共享常量派生。
- [x] 以只读方式整理 `/home/yuanzhi/下载`：按哈希与作品名去重 14 本独立
  书籍，复用已有 5 本，列出新增 9 本的规范标题、作者、语言、ISBN（如有）
  和稳定 slug。
- [x] 排除重复《金钱心理学》、合并《斑马为什么不得胃溃疡》的 PDF/EPUB，
  并排除 1 页工作材料和 3 页个人笔记。
- [x] 为新增 9 本分别建立 `index.md`、`graph.json`、`cover.webp`；默认
  `wishlist/preview`，最小图谱只使用元数据/目录与
  `editorial_inference`。
- [x] 从本地电子书提取并压缩封面派生图；不复制原始 EPUB/PDF、完整章节、
  连续正文或无关下载文件到仓库。
- [x] 核对每个新增书目与图谱同 slug、阶段一致，且每个最小图谱有核心节点、
  合法关系与可追溯来源定位。

回滚点：新增 9 本均位于独立 slug 目录；移除这些目录并撤回第四分类即可
恢复原书单，不需要迁移既有书目。

## 3. 《小王子》和《风沙星辰》

- [x] 新建 `the-little-prince` 与 `wind-sand-and-stars` 两个内容目录，
  使用规范标题、原名、作者和 `literature-and-life` 分类。
- [x] 两本均设置 `status: read`、`graphStage: preview`，相邻图谱的
  `stage` 同为 `preview`；详情明确说明图谱仍是编辑整理而非个人读后结论。
- [x] 为两本编写原创短摘要、详情正文和最小关系图，不生成细粒度论证卡，
  不猜测未指定版本的 ISBN、译者或出版社。
- [x] 制作版本中性原创封面并输出压缩 WebP，不复制未知授权的商业封面。
- [x] 验证两本可从书单卡片与左侧目录进入稳定详情 URL，并可按“文学与人生”
  和“读过”筛选。

回滚点：两本位于独立 slug 目录，可分别移除且不影响下载目录导入或论证图
样例。

## 4. 响应式长卷导图

- [x] 扩展 `BookMapSpine.svelte`，使用单一语义 DOM 呈现书级头部、部分栏道、
  问答主干、论证细节、交接与结论。
- [x] 增加成熟度和内容范围标签；所有来源继续使用
  `BookGraphEvidence.svelte`。
- [x] `< 1024px` 保持单列；桌面切换多栏 grid，溢出限制在导图内部。
- [x] 用 CSS 边框/伪元素绘制装饰连接，不引入新的画布或图形库。
- [x] 保持默认页签不加载 Cytoscape，关系探索与结构列表行为不变。

回滚点：组件可以恢复为原时间线，数据字段仍是可选增强，不影响构建。

## 5. 《象与骑象人：幸福的假设》样例

- [x] 新建 `src/content/books/the-happiness-hypothesis/index.md`，使用
  `reading` 状态和清楚的来源/完成度说明。
- [x] 制作原创 `cover.webp`，不下载或复制未知授权的商业封面。
- [x] 新建 `graph.json`：四部分全书主线，前两部分 `developed`，后两部分
  `outline`。
- [x] 从用户笔记压缩出有限的论证卡和概念节点；区分当前书论证、外部研究、
  跨书关联和个人反思。
- [x] 只把笔记中明确出现的内容写入卡片；不补写后两部分，不把外部研究线索
  标为已核验论文结论。
- [x] 为 Markdown 正文增加与核心概念对应的稳定锚点和“待补充”说明。

回滚点：新增书位于独立 slug 目录，可整体移除且不影响现有五本书。

## 6. 本地 AI 生成工作流

- [x] 编写 `docs/book-argument-map-ai-workflow.md`，包括五阶段流程、书型适配、
  分阶段提示词、来源规则和人工审核清单。
- [x] 增加 `docs/templates/book-argument-map.candidate.json`，演示完整主线、
  已展开部分和待补充部分。
- [x] 增加只读 `scripts/validate-book-map.ts <slug>`，校验输入 slug/文件并
  复用 Astro 内容同步检查。
- [x] 在 `package.json` 增加明确的本地验证命令。
- [x] 使用样例 slug 实跑该命令，并验证非法 slug 会安全失败。

回滚点：文档、模板、脚本和 package script 可独立删除；不影响网站运行时。

## 7. 质量检查

- [x] 对所有变更源文件运行 scoped Biome。
- [x] 运行 `pnpm check`。
- [x] 运行 `pnpm type-check`。
- [x] 运行 `pnpm build`，确认 17 本公开书籍页面和 Pagefind 输出生成。
- [x] 运行 `pnpm validate:book-map -- the-happiness-hypothesis`。
- [x] 校验每个非草稿书目恰好有一个同 slug 图谱，并核对 17 本总量、
  9 本下载目录新增项、两本“读过”基础书目及重复/非书籍排除项。
- [x] 检查 `git diff --check` 和 Trellis task validation。

## 8. 浏览器验证

- [x] 使用生产构建与 `pnpm preview`，直接打开新增单书详情。
- [x] 桌面视口（≥ 1024px）：
  - 默认页签是“全书主线”；
  - 四部分呈多栏长卷；
  - 前两部分卡片可读，后两部分显示待补充；
  - 来源、内容范围和成熟度可辨识；
  - 页面根节点无横向溢出。
- [x] 390px 视口：
  - 退化为单列；
  - 阅读顺序为问题 → 回答 → 细节 → 交接；
  - `scrollWidth <= clientWidth`。
- [x] 切换“关系探索 → 结构列表 → 关系探索”，确认 Cytoscape 按需加载、
  返回后画布尺寸非零。
- [x] 检查亮色/暗色、键盘焦点、封面加载、控制台错误和 Swup 往返导航。
- [x] 回归《爱的艺术》和一本没有 `bookMap` 的旧书。
- [x] 在书单验证第四分类，分别筛选“文学与人生”和“读过”；打开《小王子》
  与《风沙星辰》，确认状态显示为“读过”、图谱显示为“预读知识地图”。
- [x] 抽查新增 9 本的卡片、封面、详情、最小关系图与侧栏目录；确认查询参数
  恢复、清空筛选和无结果状态无回归。

## 9. 规格与交付

- [x] 使用 `trellis-check` 完成最终范围检查。
- [x] 将论证卡、成熟度、长卷响应式行为、第四书单分类、批量书目导入边界和
  AI 候选工作流的持久合同更新到 `.trellis/spec/frontend/`。
- [x] 更新本任务 PRD/设计/实施勾选与实际验证证据。
- [x] 不提交、不推送、不部署；这些生命周期动作等待用户单独授权。

## 10. 实施证据（2026-07-31）

- 数据与内容：公开书目、相邻图谱和封面均为 17 份；新增 9 本下载目录书籍
  均为 `wishlist/preview` 最小图谱；《小王子》《风沙星辰》均为
  `read/preview`；仓库内容与 `dist` 中没有 EPUB/PDF。
- 样例图谱：《象与骑象人》包含 4 个有序部分、14 张有来源的论证卡，
  前两部分为 `developed`，后两部分为 `outline`；旧《爱的艺术》
  `developed + []` 和无 `bookMap` 图谱均通过回归。
- 静态门禁：scoped Biome、`pnpm validate:book-map --
  the-happiness-hypothesis`、非法 slug 拒绝、`pnpm check`（185 文件、
  0 错误/警告/提示）、`pnpm type-check`、`pnpm build`（31 页面、
  17 本单书详情）与 `git diff --check` 通过。
- 浏览器门禁：1440px 为 4 栏内滚长卷（内部 `925/1392px`），390px
  为单列且根节点 `390/390px`；关系图只在点击后增加 1 个资源，画布
  `622.8×704px`，列表往返后尺寸不变；筛选 URL、清空、无结果、暗色、
  Swup 往返与旧书回归通过，运行时错误为 0。
- 视觉证据：本地截图位于 `/tmp/firefly-book-map-desktop.png` 和
  `/tmp/firefly-book-map-mobile.png`。截图仅证明渲染就绪，不代替人工审美验收。
- 生命周期：未提交、未推送、未部署。

## 17. 阅读价值与声望背书分离（用户后续变更）

- [x] 将第二节标题改为“这本书值得看的地方”，同步固定侧栏与浮动目录。
- [x] 将 `reviews[]` 迁移为 2–4 条 `readingReasons[]`，新增编辑标题和
  六类读者价值维度；同一本书的维度不得重复。
- [x] 新增可选 `endorsements[]`，把不能说明具体读者收益的声望赞誉降级。
- [x] 逐本复核 17 份 frontmatter，补齐至少两条来源化阅读理由。
- [x] 《解压手册》展示压力机制、内容范围和可读性三张卡，奥利弗·萨克斯
  评价改到卡片下方。
- [x] 运行 scoped Biome、`pnpm check`、`pnpm type-check`、`pnpm build`
  和内容/构建产物审计。
- [x] 在 1440px 与 390px 真实浏览器检查三卡布局、次要背书、来源链接和
  页面溢出。
- [x] 更新 frontend code-spec、PRD、设计、调研和实施记录。

### 实施证据（2026-07-31）

- 数据合同：17 本书均有 2–3 条 `readingReasons`，同一本书的 `kind`
  唯一；`endorsements` 为可选且最多三项。旧 `reviews` 字段和旧栏目名
  不再被 `src/` 消费。
- 样例内容：《解压手册》三张理由卡分别依据《华盛顿邮报》、Macmillan
  Academic 第三版介绍和 Kirkus Reviews；奥利弗·萨克斯评价仅作次要背书。
- 静态门禁：scoped Biome、`pnpm check`、`pnpm type-check`、
  `pnpm build` 与 `git diff --check` 通过。
- 浏览器门禁：1440px 三卡并列，390px 单列；来源与背书层级可辨，未发现
  横向溢出或知识图谱内容。
- 视觉证据：`/tmp/firefly-reading-reasons-desktop-full.png` 与
  `/tmp/firefly-reading-reasons-mobile-full.png`。截图用于确认渲染，
  最终文案感受仍以用户审阅为准。
- 生命周期：本地开发服务运行于 4321；未推送、未部署。

## 18. 完整封面与连续书籍简介（用户后续变更）

- [x] 将详情封面从 `object-cover` 改为带内边距的 `object-contain`。
- [x] 手机使用 `2:3` 封面容器，桌面使用自适应行高和最小高度。
- [x] 将三张来源介绍卡改为“书籍简介”标题下的三个连续段落。
- [x] 按 URL 去重简介来源，在正文下集中显示来源名称和核对链接。
- [x] 抽查 Macmillan、Penguin Random House、Simon & Schuster 和
  Bloomsbury 官方书页。
- [x] 运行 scoped Biome、`pnpm check`、`pnpm type-check`、
  `pnpm build` 和 `git diff --check`。
- [x] 检查 1440px 与 390px 的完整封面、简介换行、来源和页面溢出。

### 实施证据（2026-07-31）

- 视觉：`/tmp/firefly-book-intro-desktop.png` 和
  `/tmp/firefly-book-intro-mobile.png` 中封面四边完整可见，简介为连续
  正文，Macmillan Academic 来源集中显示一次。
- 静态门禁：scoped Biome、Astro check（185 文件，0 错误/警告/提示）、
  `pnpm type-check` 和 `pnpm build`（31 页面）通过。
- 生命周期：本地开发服务继续运行于 4321；未提交、未推送、未部署。

## 12. 三段式书籍介绍（用户后续变更）

- [x] 将 `previewFocus` 迁移为 `whyRead`，新增带长度限制的 `excerpts`
  schema 和共享类型。
- [x] 从书单卡片移除图谱阶段标签，卡片摘要改为 `whyRead`。
- [x] 单书详情移除图谱岛、图谱读取与 Markdown 笔记，只渲染三个语义区。
- [x] 本页目录固定为“整本书介绍 / 为什么需要看这本书 / 经典摘抄”。
- [x] 为有本地 EPUB 且能够核对原文的书添加短摘抄；其余书显示待补充，
  不猜测版本或 AI 编造名句。
- [x] 验证 17 个详情构建产物均只有三个内容区，且不含公开图谱标签。
- [x] 验证桌面、390px、摘抄页、空状态页、书单卡片与 Swup 往返。
- [x] 运行 scoped Biome、`pnpm check`、`pnpm type-check`、`pnpm build`、
  `git diff --check` 和 Trellis task validation。
- [x] 更新 `.trellis/spec/frontend/` 中的书籍内容与组件合同。
- [x] 不提交、不推送、不部署；等待用户单独授权。

### 实施证据（2026-07-31）

- 内容合同：17 本书全部使用 `description`、`whyRead` 和 `excerpts`；
  12 本已加入经本地 EPUB 核对的短摘抄，5 本显示明确的待核对空状态。
- 公开产物：17 个详情页都只有 `book-introduction`、`why-read`、
  `classic-excerpts` 三个一级内容区；没有知识图谱标题、阶段标签、
  `BookKnowledgeGraph`、Cytoscape 或其他图谱运行时引用。
- 静态门禁：scoped Biome、`pnpm check`（185 文件，0 错误/警告/提示）、
  `pnpm type-check`、`pnpm build`（31 页面、17 个书籍详情）、
  `git diff --check` 与 Trellis task validation 通过。
- 浏览器门禁：1440px 摘抄页和 390px 空状态页均为三段式且根节点无横向
  溢出；17 张书单卡片、筛选、Swup 详情往返可用，运行时错误为 0，
  已加载资源中没有图谱运行时。
- 视觉证据：`/tmp/firefly-book-three-sections-desktop.png`。截图只证明
  渲染就绪，不代替人工审美验收。
- 生命周期：未提交、未推送、未部署；本地开发服务继续运行。

## 11. 左侧书单切换滚动修复（2026-07-31）

- 根因分类：跨层合同缺失。左侧书名链接、Swup 核心 `scroll.reset` 与
  `Layout.astro` 的 `visit:start` 手动回顶分别拥有滚动行为，先前没有定义
  “书到书切换应保留阅读高度”的统一合同。
- 修复：书名链接增加 `data-book-directory-navigation`；对应 Swup visit
  同时关闭核心回顶并标记布局跳过手动回顶。普通卡片、顶部导航和直接访问
  仍按原规则回顶。
- 回归：干净临时 worktree 的 scoped Biome、`pnpm check`、顺序执行的
  `pnpm type-check` 与 `pnpm build` 通过。浏览器连续切书时桌面
  `620→620px`、`480→480px`，390px 为 `420→420px`；普通书单卡片仍
  `800→0px`，控制台错误为 0。
- 共享工作树中的书籍卡片/schema 改造曾短暂处于 `whyRead` 未迁移完成的
  中间态；等待其补齐 17 本内容后，主工作树重新通过 `pnpm check`、
  `pnpm type-check` 和 `pnpm build`（31 页面），未放宽 schema 或覆盖
  并发改动。

## 13. 左侧书单切换闪烁修复（2026-07-31）

- 根因分类：跨层合同与浏览器集成测试缺口。书籍切换本身已由 Swup 拦截，
  但全局过渡会让主内容、书籍目录和其他动态容器同时降到
  `opacity: 0` 并位移 120ms，因此产生类似整页刷新的空白闪烁。
- 修复：标记的书籍目录导航设置 `visit.animation.animate = false`，继续使用
  Swup 获取页面、更新历史和替换容器，同时沿用滚动位置保留合同。随后根据
  用户实测反馈继续定位到第二层：新插入的 `#content-wrapper` 会重播
  `.onload-animation`，即使父容器透明度为 1，也会先以 `opacity: 0`
  渲染。最终在 `content:replace` 默认替换前，从待插入文档移除这次首屏
  动画。普通书单卡片与其他未标记导航保留全局动画和回顶行为。
- 浏览器证据：切换前后的自定义 document 标识不变，Navigation Timing
  记录保持 1 条；标记导航触发 `animation:skip` 而不触发
  `animation:out:start`。逐帧采样确认第一版修复后父容器透明度为 1、但
  `#content-wrapper` 最低为 0；最终修复后主容器、内容根和左侧目录最低
  透明度均为 1，内容根没有非零位移。390px 下连续两次切书均为
  `420→420px`、无根节点横向溢出；普通卡片仍 `800→0px` 并执行原有
  退场/入场和首屏动画。
- 静态门禁：scoped Biome、`pnpm check`（185 文件，0
  错误/警告/提示）、`pnpm type-check`、`pnpm build`（31 页面）通过。
  未提交、未推送、未部署。
- 本节记录局部修复的诊断过程；动画所有权的最终合同由第 16 节全站方案
  覆盖。

## 14. 来源化介绍与经典评论（用户后续变更）

- [x] 调研 17 本书的出版社、作者官网、官方书站、媒体或专业书评来源。
- [x] 新增共享 `BookSourceCitation`，将公开 `whyRead` 替换为必填的
  `introductions[]` 和 `reviews[]`。
- [x] 为来源文本、署名和 URL 增加 Zod 校验，两个来源数组均至少一项。
- [x] 书单卡片使用首条来源介绍作为预览。
- [x] 第一节显示来源介绍与原始链接，第二节显示经典评论与原始链接。
- [x] 外文译文明确标注翻译性质，第三节原书摘抄不与评论混用。
- [x] 将逐书来源和选择规则记录到 `research/book-source-citations.md`。
- [x] 运行 scoped Biome、`pnpm check`、`pnpm type-check` 和 `pnpm build`。
- [x] 浏览器验证桌面、390px、17 张卡片、来源链接、无图谱资源和零控制台错误。
- [x] 不提交、不推送、不部署；等待用户单独授权。

### 实施证据（2026-07-31）

- 数据：17 本书均包含至少一条 `introductions` 和一条 `reviews`，每条都有
  240 字以内短译文/中文摘引、明确署名和可校验 URL；公开内容中不再存在
  `whyRead`。
- 来源：优先使用 Basic Books、Penguin Random House、Bloomsbury、
  Simon & Schuster、Macmillan、Harriman House、作者官网等原始书页，
  评论使用《纽约时报书评》《华尔街日报》《卫报》《自然》、Kirkus、
  Publishers Weekly、CFA Institute 或具名评论。
- 静态门禁：scoped Biome、`pnpm check`、`pnpm type-check`、
  `pnpm build`（31 页面、17 个详情）通过。
- 浏览器门禁：1440px《金钱心理学》和 390px《小王子》均保持三个一级区块，
  介绍/评论来源链接可见，根节点横向溢出为 0；书单 17 张卡片显示来源介绍，
  图谱资源 0，运行时错误 0。
- 视觉证据：`/tmp/firefly-book-sourced-reviews-desktop.png`。截图只证明
  渲染就绪，不代替人工审美验收。
- 生命周期：未提交、未推送、未部署；本地开发服务 PID 746999 继续运行。

## 15. 公开文案去模板化（用户后续变更）

- [x] 删除 `BOOK INTRODUCTION`、`WHY READ IT` 和 `SELECTED EXCERPTS`
  三个通用英文眉题。
- [x] 删除详情页关于本站立场和 AI 生成的过程性说明。
- [x] 逐本改写 17 本书的来源介绍与评论短译，使句子更自然，来源、URL 与
  翻译标识保持不变。
- [x] 对页面源文件和 17 本内容运行 scoped Biome。
- [x] 运行 `pnpm check`、`pnpm type-check`、`pnpm build`、
  `git diff --check` 与 Trellis task validation。
- [x] 审计 17 个构建详情页：三个区块顺序不变、来源链接仍在、旧模板眉题和
  过程性 AI 说明均不存在。
- [x] 检查 1440px《思考，快与慢》和 390px《小王子》实际截图，版式和长句
  换行正常。
- [x] 未提交、未推送、未部署；本地开发服务继续运行。

### 实施证据（2026-07-31）

- 内容：17 本书的 `introductions` 与 `reviews` 完成自然中文润色；没有
  改动署名、翻译标识、URL 或原书摘抄。
- 公开产物：英文模板眉题、`不由本站代替你下结论` 和
  `这里不会用 AI 编造名句` 均不再出现在书籍详情页。
- 静态门禁：scoped Biome、`pnpm check`（185 文件，0
  错误/警告/提示）、`pnpm type-check`、`pnpm build`（31 页面、
  17 个详情）、`git diff --check` 与任务校验通过。
- 视觉证据：`/tmp/firefly-books-no-ai-tone-desktop.png` 与
  `/tmp/firefly-books-no-ai-tone-mobile.png`。截图用于确认渲染，
  最终文案感受仍以用户审阅为准。
- 生命周期：未提交、未推送、未部署；本地开发服务继续运行。

## 16. 全站 Swup 导航连续性（用户后续变更）

- [x] 将书籍专用的动画关闭提升到 `visit:start` 全局生命周期，覆盖普通链接、
  缓存导航、上下文目录和浏览器历史导航。
- [x] 将 `.onload-animation` 清理提升为所有 `content:replace` 的替换前
  处理；直接文档加载仍保留首屏动画。
- [x] 书籍目录标记只负责 `scroll.reset` 和布局手动回顶的例外，不再持有
  动画策略。
- [x] 逐帧验证书单卡片、书到书切换、顶部导航和浏览器返回时，六个动态
  容器/内容根最低透明度均为 1。
- [x] 验证 document 标识和 Navigation Timing 记录保持不变，所有路径触发
  `animation:skip` 而不触发 `animation:out:start`。
- [x] 验证普通导航回顶、书籍目录保留滚动、桌面和 390px 无横向溢出。
- [x] 运行最终 scoped Biome、`pnpm check`、`pnpm type-check`、
  `pnpm build`、`git diff --check` 和任务校验。
- [x] 不提交、不推送、不部署；等待用户单独授权。

### 实施证据（2026-07-31）

- 根因：Swup 外层退场动画和新 DOM 的 `.onload-animation` 是两个独立动画
  所有者；只关闭其中一层会留下可见空白帧。
- 桌面开发预览：书单卡片、书籍目录、顶部导航和浏览器返回均触发
  `animation:skip=1`、`animation:out:start=0`；主容器、内容根、左右侧栏及
  两个横幅容器的最低透明度均为 1，document 标识和 Navigation Timing
  记录保持不变。
- 390px 开发预览：普通卡片 `700→0px`，连续书籍切换均为
  `420→420px`，顶部导航 `400→0px`；所有路径最低透明度为 1、无根节点
  横向溢出或控制台错误。
- 生产预览：等待一次真实首屏动画结束后，普通书单卡片导航的六个采样节点
  最低透明度均为 1，内容根不再携带 `.onload-animation`。
- 静态门禁：scoped Biome、`pnpm check`（185 文件，0
  错误/警告/提示）、`pnpm type-check`、`pnpm build`（31 页面）通过。
  最终 `git diff --check` 和任务校验通过；未提交、未推送、未部署。

## 17. 三段式内容覆盖扩展（用户后续变更）

- [x] 盘点 17 本书当前介绍与摘抄数量，确认多数只有 1 + 1。
- [x] 14 本本地 EPUB/PDF 逐字检索，选择横跨不同章节的短摘抄。
- [x] 《象与骑象人》《小王子》《风沙星辰》改用可公开核验的短原文，并记录
  翻译性质和 URL。
- [x] 17 本书的来源介绍扩展到三个互补角度。
- [x] 17 本书的摘抄扩展到 3–4 条，并保留章节或公开来源定位。
- [x] 为 `BookExcerpt` 增加可选 `url`，贯通类型、Zod schema 与详情页。
- [x] 运行内容数量、长度、重复文本和来源 URL 审计。
- [x] 运行 scoped Biome、`pnpm check`、`pnpm type-check`、`pnpm build`、
  `git diff --check` 与任务校验。
- [x] 审计 17 个生成页面仍只有三个一级区块，且无图谱资源。
- [x] 检查 1440px 与 390px 页面，确认增加内容后无横向溢出或控制台错误。
- [x] 通过 `trellis-update-spec` 固化可复用的内容覆盖合同。
- [x] 不提交、不推送、不部署；等待用户单独授权。

### 实施证据（2026-07-31）

- 内容审计：17 本书均为 3 条来源介绍和 3–4 条摘抄，共 53 条摘抄，
  无跨书重复；文本、来源和 URL 均通过长度与格式检查。
- 来源覆盖：14 本使用本地 EPUB/PDF 核对章节；《象与骑象人》使用作者官网
  公开导言，《小王子》使用作品官网摘录，《风沙星辰》使用《时代》周刊
  公开转引，三者均显示翻译标识和“核对公开原文”链接。
- 数据流：`BookExcerpt.url?` 已贯通 `src/types/book.ts`、
  `src/content.config.ts` 与单书详情页；本地版本摘抄不伪造外链。
- 静态门禁：scoped Biome、`pnpm check`（185 文件，0 错误/警告/提示）、
  `pnpm type-check`、`pnpm build`（31 页面）、`git diff --check` 和
  Trellis task validation 通过。
- 产物审计：17 个生成详情页均恰好包含
  `book-introduction → why-read → classic-excerpts`，每页 3 条介绍、
  至少 3 条摘抄，无图谱标签或 Cytoscape 资源。
- 浏览器门禁：1440px《思考，快与慢》为 3 + 4 条，390px《象与骑象人》
  为 3 + 3 条且三处公开原文链接可见；两者根节点横向溢出为 0、
  图谱资源为 0、控制台错误为 0。
- 视觉证据：`/tmp/firefly-books-expanded-desktop.png` 与
  `/tmp/firefly-books-expanded-mobile.png`。截图用于确认渲染就绪，不代替
  用户的内容和审美验收。
- 生命周期：未提交、未推送、未部署；本地开发服务 PID 746999 继续运行。
