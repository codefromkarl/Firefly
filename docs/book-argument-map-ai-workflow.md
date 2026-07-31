# 书籍论证地图 AI 候选生成工作流

这套流程用于把合法持有的目录、电子书内容或个人笔记整理为
`src/content/books/<slug>/graph.json` 的候选数据。它不绑定模型供应商，
不接入网站运行时，也不会自动覆盖或发布现有内容。

## 原则

- 先识别书型和整书主线，再展开部分论证，最后抽取概念关系。
- “问 / 答 / 接”分别由 `part.question`、`part.thesis` 和
  `transitions` 持有；论证卡只保存“机 / 证 / 症 / 法 / 界”。
- 每条公开内容都要回指真实来源单元。目录推断使用
  `editorial_inference`，不能冒充 `source_summary`。
- AI 输出永远是候选数据。只有人工核对后才能进入已发布
  `graph.json`。
- 原始 EPUB/PDF 和连续正文留在本地，不进入仓库或公开构建产物。

## 阶段 1：来源清单

把可用材料切成可定位单元，例如：

```text
metadata:title
toc:part-1/chapter-2
epub:chapter-3/section-1
notes:internal-coordination/negative-bias
```

记录每个单元的来源类型、定位、是否允许短摘录，以及哪些全书部分没有材料。
不要在这一阶段总结或补写。

提示词：

```text
你是来源整理员。只根据提供的材料列出可独立定位的来源单元。
输出 JSON 数组，每项包含 basis、locator、scope、availableForQuote。
不要总结作者观点，不推断缺失章节，不输出原文长段落。
```

## 阶段 2：整书骨架

先判断书型：

- `argumentative_monograph`：因果或观点递进；
- `progressive_dialogue`：通过对话发生立场转折；
- `essay_collection`：主题短论并列；
- `curated_anthology`：编者组织多位作者材料；
- `narrative`：人物、事件和意义随叙事推进。

然后生成核心问题、全书回答、阶段性结论、有序部分及部分间交接。概念相似度
或关系图位置不能代替作者顺序。

提示词：

```text
你是整书结构分析员。输入只有来源清单和对应短摘要。
先选择一种 archetype，再输出 coreQuestion、thesis、conclusion、
ordered parts 和 transitions。
每个字段必须包含 provenance 与 sourceRefs。
材料不足的部分保留 outline，不得生成看似完整的答案。
只输出符合候选模板的 JSON。
```

## 阶段 3：部分论证

只展开依据充分的部分。对每部分按需选择：

- `mechanism`：解释为什么成立；
- `evidence`：实验、案例或材料线索；
- `manifestation`：现实表现、偏差或问题；
- `practice`：训练、干预或解决路径；
- `boundary`：适用限制、争议或风险。

`context` 与 `provenance` 是两条不同维度：

| context | 含义 |
| --- | --- |
| `book_argument` | 当前书中的论述 |
| `external_research` | 书或笔记提到的外部研究线索 |
| `cross_book` | 与其他书的关联 |
| `personal_reflection` | 读者个人观察或实践 |

外部研究若没有核验原始论文，只能标为“研究线索”。医疗、法律、金融等高风险
内容必须增加边界卡。

提示词：

```text
你是部分论证编辑。只处理 maturity 不为 outline 且来源充分的部分。
生成最少但足够形成闭环的 argumentCards；不要机械凑齐五种类型。
每张卡必须关联已有概念节点 ID，并回指一个或多个真实来源。
区分本书论证、外部研究、跨书关联和个人反思。
不要把个人笔记改写成作者原话。
```

## 阶段 4：概念规范化

合并同义概念，为节点分配稳定 kebab-case ID，再生成有方向的关系。节点与关系
服务于跨部分探索，不能复制整书主线的作者顺序。

提示词：

```text
你是概念规范化编辑。合并同义词，保留概念边界，输出 nodes 和 edges。
每个 argumentCard.conceptNodeIds 必须指向已存在节点。
每条关系说明其方向和依据；不确定关系使用 editorial_inference。
禁止自环、重复 ID、悬空端点和只有画布才能理解的内容。
```

## 阶段 5：反向证据审计

逐项从公开结论返回来源：

- 是否存在无来源结论或伪造定位；
- `source_summary` 是否真的有 EPUB/notes 依据；
- `personal_note` 是否真的指向 notes；
- 外部研究是否被误写成已核验事实；
- `outline` 是否被虚假内容填满；
- 卡片和部分引用的概念节点是否存在；
- 交接是否向后或让某部分不可达；
- 短摘录是否不超过 240 字且不会替代原书。

提示词：

```text
你是反向证据审计员。不要改写候选 JSON。
按 JSON Pointer 列出 error、warning 和 verified 三类发现。
任何无法返回真实来源的内容都列为 error；材料不足但已标 outline 的部分
列为 verified，不建议自动补写。
```

## 人工审核与发布

1. 复制 [候选 JSON 模板](./templates/book-argument-map.candidate.json)，在仓库
   外生成和修订候选结果。
2. 人工核对标题、书型、部分顺序、来源定位、内容范围与医疗等风险边界。
3. 将确认后的紧凑数据写入目标书目的 `graph.json`。
4. 保持 `index.md.graphStage` 与 `graph.json.stage` 一致。
5. 运行：

   ```bash
   pnpm validate:book-map -- <slug>
   pnpm check
   pnpm type-check
   pnpm build
   ```

6. 在桌面与 390px 视口检查主线、来源折叠、关系探索、结构列表和横向溢出。

通过自动校验只代表数据和构建就绪，不代表内容已经获得人的阅读体验验收。
