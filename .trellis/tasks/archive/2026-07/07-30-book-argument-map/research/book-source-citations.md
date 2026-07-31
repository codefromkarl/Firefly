# 书籍来源介绍与经典评论调研

调研日期：2026-07-31

## 采用规则

- “整本书介绍”优先引用出版社、作者官网、官方书站或可追溯的书目介绍。
- 详情页把三条介绍组合成一篇“书籍简介”，来源在正文下方按 URL 去重。
  优先使用 Macmillan、Penguin Random House、Simon & Schuster、
  Bloomsbury 等出版社官网、作者或作品官网，以及豆瓣等知名书目页；不采用
  无署名搜索摘要。
- “这本书值得看的地方”使用出版社、作者或作品官网、媒体、专业书评或具名
  评论中的具体内容，回答读者能理解什么、全书覆盖什么、如何写、如何用或
  有什么边界。
- “作者很伟大”“一部必读经典”等泛赞誉不再作为阅读理由，只能放在可选
  `endorsements` 中做次要背书。
- 外文材料只保留短译文，并在来源名中明确标注“据英文原文译”或“据意译”；
  页面提供原始 URL，读者可以回到来源核对。
- 原书句子仍只放在“经典摘抄”，评论不得冒充作者原话。
- 单条译文限制在 240 字内，不复制长篇出版社文案或书评正文。

## 已采用来源

| 书籍 | 介绍来源 | 评论来源 |
| --- | --- | --- |
| 《经济学的思维方式》 | [Basic Books / Hachette](https://www.hachettebookgroup.com/titles/thomas-sowell/basic-economics/9780465056842/) | 《华尔街日报》，转引自同一出版社书页 |
| 《褚时健传》 | [中信出版社内容简介，豆瓣书目页](https://book.douban.com/subject/26664352/) | [王石评价，转引自豆瓣书评页](https://book.douban.com/subject/35799005/reviews) |
| 《情绪》 | [Publishers Weekly](https://www.publishersweekly.com/9781524747596) | [Kirkus Reviews](https://www.kirkusreviews.com/book-reviews/leonard-mlodinow/emotional/) |
| 《富甲美国》 | [Penguin Random House](https://www.penguinrandomhouse.com/books/599233/made-in-america-mi-historia--made-in-america-my-history-by-sam-walton/9780525564898/) | 《纽约时报书评》，转引自同一出版社书页 |
| 《人类与象征》 | [Penguin Random House](https://www.penguinrandomhouse.com/books/89056/man-and-his-symbols-by-carl-g-jung/9780593499993/) | 《卫报》，转引自同一出版社书页 |
| 《穷查理宝典》 | [Stripe Press 新版介绍](https://stripepress.substack.com/p/poor-charlies-almanack-is-out-now) | [CFA Institute 书评](https://rpc.cfainstitute.org/blogs/enterprising-investor/2023/book-review-poor-charlies-almanack) |
| 《纳瓦尔宝典》 | [The Navalmanack 官方网站](https://www.navalmanack.com/home) | 蒂姆·费里斯推荐语，转引自同一官网 |
| 《爱的艺术》 | [Bloomsbury](https://www.bloomsbury.com/us/art-of-loving-9780826412607/) | [Kirkus Reviews 1956 年书评](https://www.kirkusreviews.com/book-reviews/a/erich-fromm-4/the-art-of-loving/) |
| 《被讨厌的勇气》 | [Simon & Schuster](https://www.simonandschuster.com/books/The-Courage-to-Be-Disliked/Ichiro-Kishimi/9781501197277) | 马克·安德里森推荐语，转引自同一出版社书页 |
| 《象与骑象人》 | [乔纳森·海特作者官网](https://www.happinesshypothesis.com/) | 《自然》书评，转引自作者官网 |
| 《小王子》 | [作品官方网站](https://www.lepetitprince.com/en/) | [P. L. 特拉弗斯首版书评，转引自 Literary Hub](https://lithub.com/how-a-beloved-childrens-book-was-born-of-despair/) |
| 《金钱心理学》 | [Harriman House](https://harriman-house.com/authors/morgan-housel/the-psychology-of-money/9780857197689) | 杰森·茨威格《华尔街日报》评论，转引自同一出版社书页 |
| 《思考，快与慢》 | [Macmillan / FSG](https://us.macmillan.com/books/9781429969352/thinkingfastandslow/) | 吉姆·霍尔特《纽约时报书评》，转引自同一出版社书页 |
| 《蛤蟆的油》 | [岩波书店介绍，转引自纪伊国屋](https://www.kinokuniya.co.jp/f/dsg-01-9784006020378) | [四方田犬彦，ALL REVIEWS](https://allreviews.jp/review/319) |
| 《自卑与超越》 | [Oneworld 版本介绍，转引自 Goodreads](https://www.goodreads.com/book/show/1940020.What_Life_Should_Mean_to_You) | [Isobel Collins，Behavior Online 历史书评](https://www.behavioronline.net/classical-adlerian-psychotherapy/329-life-mean-review/) |
| 《解压手册》 | [Macmillan Academic](https://academic.macmillan.com/academictrade/9780805073690/whyzebrasdontgetulcers/) | 奥利弗·萨克斯推荐语，转引自同一出版社书页 |
| 《风沙星辰》 | [Harcourt 出版社介绍，转引自 Google Books](https://books.google.com/books/about/Wind_Sand_and_Stars.html?id=5NtXAAAAYAAJ) | [《时代》周刊 1939 年书评](https://time.com/4255854/little-prince-1943-history-2/) |

## 页面数据流

```text
来源网页
  → 人工选择短段并翻译、记录署名和 URL
  → books frontmatter introductions / readingReasons / endorsements
  → Zod 校验文本、署名和 URL
  → 书单使用首条来源介绍作预览
  → 详情第一节显示来源介绍，第二节显示阅读价值与次要背书，第三节显示原书摘抄
```

## 2026-07-31 阅读理由复核

17 本书的原有经典评论逐一按信息量复核。能够说明具体视角、结构、方法或
边界的评论进入 `readingReasons`；只称赞作者地位、作品重要性或总体质量的
评论进入 `endorsements`。每本书再从已经核对的官方介绍或专业书评中选择
互补材料，最终形成 2–3 条、且 `kind` 不重复的阅读理由。

《解压手册》直接采用 Macmillan Academic 同一官方书页收录的三类依据：

- 《华盛顿邮报》说明本书怎样把短期适应性压力反应与长期心理刺激造成的
  健康风险连接起来；
- 出版社第三版介绍列出睡眠、成瘾、焦虑、体重、创伤后应激和压力管理等
  覆盖范围；
- Kirkus Reviews 强调个人轶事、奇异知识和面向非科学读者的一流科学写作。

奥利弗·萨克斯关于作者地位的评价保留在 `endorsements`，不再独占第二节。

## 2026-07-31 内容覆盖扩展

用户复核后认为每本书只有一条介绍和一处摘抄，不足以呈现全书范围。本轮在
不增加公开一级区块的前提下，将内容密度调整为：

- 每本书至少三条来源介绍，分别覆盖核心问题或起点、主要内容与结构、结尾
  落点或实际用途；三条不得只是同一句话的同义改写。
- 每本书至少三处短摘抄，尽量分别来自开篇、核心机制和后半部/结论，避免只
  取同一章节的相邻段落。
- 14 本有本地 EPUB/PDF 的书使用本地版本逐字核对并记录章节；不把完整原书、
  连续长段或原始电子书放进仓库。
- 《象与骑象人》使用作者官网公开导言，《小王子》使用作品官网公开英文摘录，
  《风沙星辰》使用《时代》周刊转引的英文版短句。三者均在来源中标明翻译
  性质，并提供公开核对 URL。
- 单条仍限制在 240 字以内。增加数量是为了覆盖不同主线，不是复制更多连续
  原文；所有公开摘抄合在一起也不得替代阅读原书。

### 覆盖结果

| 书籍数 | 每本来源介绍 | 每本短摘抄 | 公开摘抄核对链接 |
| --- | --- | --- | --- |
| 17 | 3 | 3–4 | 无本地版本的 3 本提供 |

页面数据流相应补充为：

```text
本地原书 / 作者或作品官网公开文本
  → 选择分属不同章节或论述阶段的短句
  → books frontmatter excerpts（文本、版本定位、可选公开 URL）
  → Zod 校验文本、来源与 URL
  → 详情第三节按原书顺序展示并允许核对公开原文
```
