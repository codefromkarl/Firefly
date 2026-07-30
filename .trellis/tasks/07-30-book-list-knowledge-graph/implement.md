# 书单与书籍知识图谱实施计划

## 0. 启动前门禁

- [x] 用户审阅并批准 `prd.md`、`design.md` 和本计划。
- [x] 运行 `task.py start` 进入 `in_progress`，不得在 planning 状态改功能代码。
- [x] 加载 `trellis-before-dev`，重新读取 frontend spec 的适用章节。
- [x] 确认工作树只包含本任务规划文件，不覆盖无关修改。

## 1. 建立依赖与领域合同

- [x] 使用 pnpm 添加 `cytoscape` 3.x，并审查 lockfile 只包含预期依赖。
- [x] 在 `src/types/book.ts` 定义共享展示类型、状态、节点种类和关系种类。
- [x] 扩展 `src/content.config.ts`：
  - `books` Markdown/MDX collection；
  - `bookGraphs` JSON collection；
  - 本地图片 schema；
  - collection reference；
  - 节点/边唯一性与端点引用 `superRefine`。
- [x] 在 `src/utils/book-utils.ts` 集中实现：
  - 非草稿书籍排序；
  - 书籍与图谱关联；
  - 状态、节点类型、关系类型的中文展示投影；
  - 传给 Svelte 的可序列化卡片数据。
- [x] 不复用或扩展 Bangumi 的外部 API 类型作为书籍领域模型。

回滚点：此阶段只增加依赖和数据合同；若 Cytoscape 不适用，可以移除依赖而不
影响现有页面。

## 2. 整理首版 EPUB 内容

- [x] 为 5 本书创建稳定英文 slug 目录：
  - `thinking-fast-and-slow`
  - `the-psychology-of-money`
  - `the-courage-to-be-disliked`
  - `the-almanack-of-naval-ravikant`
  - `the-art-of-loving`
- [x] 从 EPUB OPF/目录核对书名、作者、语言和可靠 ISBN。
- [x] 只提取 EPUB 内置封面，使用 Sharp/现有资源管线生成低分辨率 WebP。
- [x] 删除临时解包文件，确认仓库中不存在 `.epub`、完整章节或原始封面副本。
- [x] 为每本书编写 `index.md`：
  - `status: wishlist`；
  - `graphStage: preview`；
  - 中性简介；
  - 预读关注点与问题；
  - 明确尚未阅读。
- [x] 为《思考，快与慢》整理 25–40 个候选节点与关系，依据为
  `metadata + toc + epub`。
- [x] 为其他 4 本整理 6–15 个节点，依据只为 `metadata + toc`。
- [x] 所有图谱写明 `aiAssisted: true` 和预读阶段，不写个人评分。
- [x] 对图谱内容做逐项来源核对，避免长篇原文和无法由输入支持的关系。

回滚点：每本书是独立目录，可单独移除有问题的条目而不影响页面框架。

## 3. 实现书单页

- [x] 新建 `src/pages/books/index.astro`，加载非草稿书籍并构建卡片投影。
- [x] 新建 `BookLibrary.svelte`：
  - 关键词搜索；
  - 状态和主题筛选；
  - 清除筛选；
  - 结果数量与无结果状态。
- [x] 新建或组合 `BookCard.svelte`，显示封面、作者、想读状态、主题和预读关注点。
- [x] 所有详情链接经过 `url()`/base-aware 处理。
- [x] 在 `navBarConfig.ts` 增加“书单”入口，不恢复 Bangumi 路由。
- [x] 如新增 i18n key，按仓库现有语言映射保持所有语言文件类型完整。

## 4. 实现详情页与 SEO

- [x] 新建 `src/pages/books/[...slug].astro` 与 `getStaticPaths()`。
- [x] 获取并验证每本书的唯一图谱条目。
- [x] 使用 MainGridLayout、Astro Image 和 Markdown 组合详情页面。
- [x] 展示：
  - 书籍元数据；
  - 想读状态；
  - 预读关注点；
  - “预读知识地图”及 AI 辅助/依据说明；
  - Markdown 正文。
- [x] 输出 Schema.org `Book` JSON-LD，仅包含可靠字段。
- [x] 添加 Pagefind 元数据与可索引静态文本。

## 5. 实现可探索图谱

- [x] 新建 `BookKnowledgeGraph.svelte`，使用 `client:visible`。
- [x] 在 `onMount` 内动态导入并初始化 Cytoscape。
- [x] 实现节点选择、一阶邻居高亮、清除选择。
- [x] 实现节点种类和关系种类筛选。
- [x] 实现放大、缩小、适配视图与重置。
- [x] 实现详情面板和章节锚点链接。
- [x] 实现 SSR 节点/关系列表与移动端结构视图。
- [x] 实现键盘按钮、可访问名称、焦点样式和 `aria-live`。
- [x] 实现主题变化与 ResizeObserver。
- [x] `onDestroy` 清理 Cytoscape、observer、监听器和异步布局。
- [x] 验证 Swup 首次进入、离开、返回、再次进入不会重复挂载。

## 6. 样式与响应式检查

- [x] 复用 card-base、主题变量、圆角和间距，不复制文章卡片大段实现。
- [x] 检查亮色/暗色主题的节点、边、标签和焦点对比度。
- [x] 检查约 360px、768px、1280px 宽度：
  - 无页面横向溢出；
  - 触控按钮尺寸合理；
  - 图谱与详情面板排序清晰；
  - 长书名、作者和关系标签不破坏布局。
- [x] 检查 `prefers-reduced-motion`。
- [x] 记录自动化截图只能证明渲染就绪，最终视觉感受仍需人工验收。

## 7. 质量门禁

- [x] 对变更源文件运行有范围的 Biome check/format，避免全仓格式化。
- [x] `pnpm check`
- [x] `pnpm type-check`
- [x] `pnpm build`
- [x] 根域 preview HTTP 检查：
  - `/books/`
  - 五个详情 URL；
  - 至少一个封面和 Cytoscape chunk；
  - sitemap 与 Pagefind 输出。
- [x] 子路径构建：

```bash
ASTRO_SITE_URL=https://codefromkarl.github.io \
ASTRO_BASE_PATH=/Firefly \
pnpm build
```

- [x] 检查子路径构建中的导航、封面、详情链接和章节锚点。
- [x] 使用 dev/preview 做两轮 Swup 导航和桌面/移动视觉检查。
- [x] 审查 `src/constants/lqips.json` 等生成文件，只保留由新增封面引起的预期变化。
- [x] `git diff --check` 与最终 `git status --short`。

## 8. 完成与交付

- [x] 运行 `trellis-check` 做 spec、类型、数据流、复用和验证复核。
- [x] 根据实施中发现的持久合同判断是否更新 frontend spec。
- [x] 向用户报告：
  - 实际实现范围；
  - 图谱的预读/AI 辅助边界；
  - 验证命令和结果；
  - 尚未完成的人工视觉/内容验收。
- [x] 只有用户明确授权时才提交、推送或部署。

## 9. 本地检查反馈

- [x] 在 `MainGridLayout` 增加 Swup 安全的自定义左侧栏插槽。
- [x] 新增书籍目录组件，书单页显示全部书籍。
- [x] 单书详情目录增加概览、知识图谱、阅读笔记和 Markdown 章节。
- [x] 普通页面继续显示 Profile/Categories/Tags，不改变全站默认侧栏。
- [x] 验证直接访问、普通页进入书单、书单进入详情和历史返回。
- [x] 重新运行定向 Biome、Astro check、type-check 和生产构建。

## 10. 图谱阅读层与来源透明度

- [x] 扩展共享类型和 Content Collection schema：
  - 节点/关系 `provenance`；
  - 节点必填、关系可选的 `sourceRefs`；
  - 来源必须属于图谱顶层 `basis`；
  - 来源总结和个人笔记必须引用匹配的正文/笔记依据；
  - 可选短摘录长度受限。
- [x] 迁移五本书图谱：
  - 《思考，快与慢》的正文概念标记为来源总结；
  - 其他四本的目录候选概念标记为整理推断；
  - 未逐项建立正文证据的关系统一标记为整理推断；
  - 不增加未经核对的原文摘录。
- [x] 图谱组件增加“结构概览 / 关系探索 / 结构列表”视图。
- [x] 结构概览默认只显示核心和高重要度节点，并按章节/主题分组渐进展开。
- [x] 节点与关系详情展示内容性质、来源位置和可选折叠短摘录。
- [x] 重新运行定向 Biome、`pnpm check`、`pnpm type-check`、`pnpm build`
  和 `git diff --check`。

## 11. 分类目录与统一筛选

- [x] 为书籍内容 schema 增加单一主分类 `shelf` 枚举。
- [x] 为首批 5 本书分配“认知与决策”“财富与成长”“心理与关系”。
- [x] 左侧目录按主分类分组并显示书籍数量。
- [x] 左侧栏提供阅读状态、主题和清除筛选入口。
- [x] 主区域增加主分类筛选及当前筛选条件展示。
- [x] 分类、状态、主题和关键词统一读写 URL 查询参数。
- [x] 验证刷新、Swup 导航、前进/后退和移动端交互。
- [x] 重新运行定向 Biome、Astro check、type-check 和生产构建。

## 12. 左栏目录 UI/UX 优化

- [x] 移除左栏重复的阅读状态、主题和清除筛选卡片。
- [x] 使用原生可折叠分组呈现主分类，并保留全部书籍导航。
- [x] 区分未筛选书单、当前筛选分类和当前详情书籍三种视觉状态。
- [x] 筛选不再隐藏左栏书目，筛选交互统一由主区域承担。
- [x] 单书详情自动展开当前书籍所在分类，并保留本页目录。
- [x] 验证过滤 URL、详情返回、桌面视觉和 390px 窄屏。
- [x] 重新运行定向 Biome、Astro check、type-check、生产构建和
  `git diff --check`。

## 13. 整书主线样板

- [x] 增加可选 `bookMap` 共享类型和 Content Collection schema。
- [x] 构建期校验主线部分/交接 ID、关联概念引用、交接端点和整体可达性。
- [x] 新增全书主线组件，显示核心问题、全书主张、各部分角色、认知推进、
  部分间交接、关联概念和全书落点。
- [x] 有 `bookMap` 时默认页签显示“全书主线”；旧图谱继续使用结构概览。
- [x] 为《爱的艺术》补齐四章主线及第三章社会诊断概念，不扩大正文引用范围。
- [x] 运行 `trellis-check`、定向 Biome、`pnpm check`、`pnpm type-check`、
  `pnpm build` 和视觉检查：
  - Astro diagnostics：185 个文件，0 error / 0 warning / 0 hint；
  - 生产构建：19 个静态页面、Pagefind 索引成功；
  - 浏览器：默认“全书主线”，桌面和 390px 无横向溢出，封面加载成功；
  - 切换“关系探索”后 Cytoscape chunk 才加载，画布约 623 × 704，无页面错误。

## 14. 首屏与按需加载优化

- [x] 禁用 Swup 全局预加载，避免首页重复预取当前文档。
- [x] Pagefind 统一通过共享 loader 在搜索意图或搜索页挂载时加载。
- [x] Cytoscape 保持在用户打开“关系探索”后才动态加载。
- [x] 非首页背景和被上下文目录替代的 Profile 图片使用懒加载。
- [x] 将首页壁纸移入 `src/assets`，同源移动/桌面背景合并为一个响应式图片节点。
- [x] 详情页主封面和书单首张可见封面使用首屏加载优先级，其余封面懒加载。
- [x] 将六种语言的静态全集导入改为当前语言与回退语言的动态分块加载。
- [x] 为内容哈希的 `/_astro/*` 增加一年 immutable 浏览器缓存策略。
- [x] 在 390 × 844、DPR 3、4× CPU、约 1.6 Mbps / 150 ms 延迟下复测：
  - 首页约 318 KB / 40 requests，FCP 1.04 s，LCP 2.44 s，CLS 0；
  - 《爱的艺术》详情约 215 KB / 36 requests，FCP/LCP 约 0.80 s；
  - 普通首屏不请求 Pagefind 或 Cytoscape，只请求 `zh_CN` 与 `en` 语言块。
- [x] 验证搜索、图谱、Swup 往返和上下文侧栏无回归，浏览器控制台无错误。
- [x] 根路径与 `/Firefly` 子路径均完成生产构建；抽样 37 个子路径资源引用均映射到真实产物。
- [x] 运行全 `src` Biome check、`pnpm type-check`、`pnpm check`、
  `pnpm build` 和 `git diff --check`。
