# 语义分段与分镜反向审稿

状态：已实现并用已有稿件验证。用户授权在文稿到图片渲染之间加入论证分段与反向审稿。本文是本扩展唯一验收清单；数据字段与函数说明见 [semantic-contract.md](semantic-contract.md)。

## 流程与职责

1. prepare 固定原稿和提供的来源笔记版本，产生带实际行号、原文、指纹的段落包。机器分块只是定位，不是语义分段。
2. 当前助手依据原稿和材料填写语义分段候选：每段的问题、命题、观众理解变化、推理路径、边界、转场及画面计划。不会偷偷调用收费模型或把空模板称为已分析。
3. 独立审稿重新读原稿与来源，不能只读第一轮摘要。发现必须指向真实原句，区分内容与画面问题；没有原文核查材料时保留范围限制。
4. 校验原稿版本、锚点、引用、正文覆盖、段落/画面身份和报告版本。程序结构信号单独显示，不冒充语义结论。
5. 导出论证分段稿、视频分镜表和反向审稿报告。允许将候选分镜编译成现有图片renderer接受的storyboard；不会修改原稿或自动记录作者认可。
6. 原稿修改后compare列出改变、移动、语境变化、重复歧义和未归属的新段，关联需要检查的分镜及可能需重录的段落。

## 核心规则

- 视频段落、原文段落与画面不是一一对应；一个语义段可以有多张画面。
- hook/transition不机械要求证据；因果解释、事实、比较、建议、工作定义和个人判断使用不同检查角度。
- 没有配图只能作为表达问题的线索，不能推出命题薄弱；书封面或引文不是该命题成立的自动证明。
- source笔记被读取不代表原书/论文全文已经核查，报告要保存读取范围和原始材料缺口。
- 发现要有位置、观察、理由、影响、修订选项和不确定性。缺少依据可以建议补查或收窄，不能自动生成研究或替作者重写结论。
- resolved/dismissed是带理由和处理者的记录，不构成强身份认证，也不能凭自动字段创建发布批准。
- 原稿和分析版本变化后，旧审稿不能静默用于新稿；相同文本重复出现必须报告定位歧义。
- 修改影响提示不是语音识别；最终录音是否需要重录仍需结合实际旁白检查。

## 固定产物

- 原稿定位包与来源版本清单。
- 论证分段稿：单元承诺、命题类型、原稿锚点、依据、推理、边界、转场。
- 视频分镜表：语义段ID、画面ID、画面目的、显示内容、旁白来源与素材。
- 反向审稿报告：独立AI审阅意见与程序结构信号分开列出。
- 可供现有frames/video工具读取的storyboard；保留语义段及审查候选状态。
- 原稿变更影响报告：受影响的语义段、画面和需要复查的旁白。

## 验收

- [x] 原稿分块有准确行号与稳定内容锚点；不修改原稿、不伪造semantic结论。
- [x] 分段与审查绑定文稿版本、来源版本及分析版本；伪引用、未知ID、漏段和错转场被指出。
- [x] 实际完成一次基于已有稿件的语义分段，以及独立重读原稿/来源的反向审稿；意见全部保留candidate。
- [x] 三份可读产物和兼容旧renderer的分镜实际生成，旁白不重复/丢失，画面可回到原稿。
- [x] 插入、修改、移动和重复段落的影响测试通过；纯段落序号变化不迫使全文重录。
- [x] 原有媒体/系统测试保持通过，未改用户文章、调用付费模型或发布。


## 操作入口

```bash
pnpm creator:media semantic-prepare   --input '.local/creator-vault/40 内容项目/某项目/主稿.md'   --sources-dir '.local/creator-vault/50 来源'   --output '.local/某项目/semantic-input-v1'
```

输出 packet.json、analysis-template.json、“分段分析任务.md”和“独立审稿任务.md”。`--sources-dir` 选取该目录下 SRC-*.md 来源卡；不填写时没有来源输入，不会自动宣称找到证据。prepare 只准备材料，明确 semantic_analysis_executed=false。

把这份材料交给当前助手：先根据原稿产生 analysis.json；独立审稿先重新读原稿与提供材料，再绑定分段ID，形成 review.json。模型调用不嵌入脚本，没有后台或付费服务。本轮已由当前助手与独立子代理实际完成一次，不只是留空模板。

```bash
pnpm creator:media semantic-check   --packet '.local/某项目/semantic-input-v1/packet.json'   --analysis '.local/某项目/analysis.json' --review '.local/某项目/review.json'
pnpm creator:media semantic-export   --packet '.local/某项目/semantic-input-v1/packet.json'   --analysis '.local/某项目/analysis.json' --review '.local/某项目/review.json'   --output '.local/某项目/semantic-output-v1'
pnpm creator:media frames   --plan '.local/某项目/semantic-output-v1/storyboard.json'   --output '.local/某项目/semantic-frames-v1'
```

check/export会重新读取当前原稿与来源卡并比较完整pack，不能改pack原句后仍借旧SHA假装原文定位正确。输出目录按版本保留；生成内容或规则结果改变时不能复用旧报告，人工修改的文件不会覆盖。

正文只需在 Obsidian 原稿中修改。随后比较：

```bash
pnpm creator:media semantic-compare   --before '.local/某项目/semantic-input-v1/packet.json'   --input '.local/creator-vault/40 内容项目/某项目/主稿.md'   --analysis '.local/某项目/analysis.json'   --output '.local/某项目/change-impact-v2.json'
```

比较允许历史packet，但不把旧分析重新批准给新稿。返回受影响段落、画面、未分配的新正文和旁白复查范围；画面受语境影响不表示一定需要重画，旁白提示也不是语音识别对齐。只比较原稿/来源，独立更改的旁白配置还需依据工程文件版本核对。

## 实际演练结果

本轮使用既有稿件，输出在 `.local/semantic-review/wealth-results-ready`，画面在 `.local/semantic-review/wealth-frames-ready`。实际生成9个语义单元、18张候选画面；34个正文块各进入旁白一次，2个非口播块（分隔线、参考资料附注）有明确排除理由。原稿没有被改写。

独立审稿实际先读原稿、研究账本和6份来源卡，未先看新分镜候选；保留4项候选意见、6项已有优点。所有意见含逐字原句、实际行号、影响、两个修订选项和不确定性。没有据来源笔记冒称重新核验原书或论文全文，也没有把尚未查看的画面说成存在视觉缺陷。

在专用副本中修改定义表述：S03/S04/S08/S09及相应画面进入语境复查，核心旁白提示仅S03；原稿未变。输出 `definition-change-impact.json` 不代表作者已经接受该修改。

程序标记valid只证明绑定和结构检查通过；全部结果保持candidate/pending_review，未生成作者批准、未录音、未发布。
