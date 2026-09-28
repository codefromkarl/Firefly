# 文稿 → B 站专栏与本人录音视频

本工程使用已有 Markdown、书籍封面、明确选定的引文/导图数据和本地本人录音。不会调用 TTS，不新增观点，不上传或发布。设计与本阶段唯一验收清单见 [media-delivery-design.md](media-delivery-design.md)。

文稿录音前的论证分段、分镜规划和反向审稿见 [semantic-review.md](semantic-review.md)。原有 plan/build 是按标题与段落生成的机械初排，不因此具有语义审查能力。

## 一次构建本地交付包

在 Firefly 根目录运行：

```bash
pnpm creator:media build \
  --input '.local/creator-vault/40 内容项目/某项目/主稿.md' \
  --visuals '.local/某项目/visuals.json' \
  --audio '/本机录音路径/旁白.m4a' \
  --output '.local/某项目/交付-v1'
```

`--visuals` 可省略；没有附加图配置时，根据原稿标题生成结构导图。`--audio` 可省略，此时仍生成专栏、分镜、图片和录音清单，明确返回 `recording_required`，不会拿别的声音冒充你的旁白。

输出结构：

```text
交付-v1/
├── storyboard.json          可编辑的分镜计划
├── article-assets.json      专栏所用图片及插入位置
├── frames/
│   ├── frame-001.png ...    1920×1080 标题、正文、引用、导图
│   ├── frames.json          录音和场景输入
│   ├── gallery.html         全部分镜预览
│   ├── recording-script.md  已有文稿对应的录音清单
│   └── layout-report.json   文字框与字号、引用来源类型
├── bilibili/
│   ├── bilibili.html        富文本复制、图片预览
│   ├── title.txt            平台标题
│   ├── bilibili.txt         保留来源 URL 的备用正文
│   ├── images/             要在编辑器上传的配图
│   └── asset-order.json     图片顺序和插入位置
└── video-preview/           有录音时才生成
    ├── video.mp4
    ├── timeline.json
    ├── subtitles.srt
    ├── poster.jpg
    └── build-report.json
```

首次 build 有录音时生成**估时预览**，并保留预览水印；不把按文字长度分配的场景时间称为准确口播对齐。输入或人工产物发生变化时，使用新的版本目录；不覆盖旧稿。详情见各子工具文档。

## 专栏交付

日常专栏以 [统一入口](README.md#统一专栏入口) 为准。媒体 build 产物仍可预览；需要受控交付时，将选定图片及 manifest 放入 vault 的项目可读范围，使用 creator:system preview --draft ... --assets ... 重新生成绑定登记稿件的 B 站包，再 release-prepare。系统首页维护受控预览指向，视频分支独立进行。

打开 `bilibili/bilibili.html`，分别复制标题和正文富文本；在 B 站当前编辑器粘贴后，按图片占位和 asset-order 上传图片。当地图片不会随着剪贴板自动上传。纯文本备用稿保留完整来源 URL。

适配器支持段落、二三级标题、加粗、引用、列表、公开链接，表格降级为可读的带列名段落。没有假定 B 站原生接收 Markdown 或能够保留全部 CSS。详见 [bilibili-export.md](bilibili-export.md)。

本轮 Browser 运行时没有可用会话，无法在真实登录编辑器做粘贴试验；已用本地 Chromium 验证复制数据与 contenteditable DOM，并检查桌面/手机排版。正式平台预览、图片上传、发布仍未执行。

## 书籍封面与引用卡

`visuals.json` 示例：

```json
{
  "schema": 1,
  "scenes": [
    {
      "id": "quote-one", "type": "quote",
      "book_id": "the-psychology-of-money", "excerpt_index": 1,
      "heading": "书籍中的原文", "after_heading": "正文中准确的标题"
    }
  ]
}
```

- `book_id` 对应现有书单目录，封面保持比例。`excerpt_index` 是该书 `excerpts` 的零起始索引，文字和出处由原记录读取，不能随便填一句话再加书封面。
- 引文沿用书单记录，不自动宣称本轮重新核查了原书。若需引用受控证据，使用 `evidence_id` 替代 excerpt_index，并给 CLI 提供 `--vault`；证据来源的 work_id 必须与展示的 book_id 一致，且不能已撤回或失效。
- `after_heading` 指定正文对应章节，专栏图片也放在该标题后。没有该字段时，补充视觉放在分镜/专栏末尾。
- 单纯展示参考书可用 `type: book` 与明确的 `text`；它不会把转述排成书中原话。
- 本地封面及引用材料仍需作者在交付前检查使用依据，工具只保留出处，不作许可认定。

## 一系列知识导图

自动生成的图只表示原稿标题结构，图上写“文稿结构导图”；按每张最多四个分支拆成一系列图片。它不会从标题自动推导因果关系。

需要展示已经整理好的知识关系时，提供明确节点和边：

```json
{
  "id": "map-one", "type": "map", "heading": "本期知识关系",
  "diagram_basis": "provided_structure",
  "nodes": [{"id":"q","label":"中心问题"},{"id":"a","label":"已确认的分论点"}],
  "edges": [{"from":"q","to":"a","label":"包含"}],
  "narration": "已有口播文字"
}
```

每张图 2–5 个节点，复杂关系拆成多张。节点与关系原样保留；未知端点、重复节点、过长文字停止并提示调整。正文卡按已有段落拆页；引文卡保留出处。中文断行处理标点，过小字号或溢出会报错，不静默截断。

## 本人录音与时间轴

建议先查看 `frames/recording-script.md`。它是已有文稿的分镜录音清单，不是语音识别结果。整段录音可直接给 build；已有分镜时也可单独接入：

```bash
pnpm creator:media frames --plan .local/某项目/storyboard.json \
  --audio /本机路径/录音.wav --output .local/某项目/frames-v2
pnpm creator:media timeline --frames .local/某项目/frames-v2/frames.json \
  --output .local/某项目/timing-review.json
```

听录音，修改 timing-review.json 中各场景 start/end，使其连续覆盖整段录音；确认无误后设置 `timing_confirmed: true`。该动作是本地作者确认，不是算法已识别出准确字幕。

```bash
pnpm creator:media video --frames .local/某项目/timing-review.json \
  --output .local/某项目/video-v1
```

加 `--preview` 可先看带水印的版本。正式合成要求完整显式 cue 与确认标记；只改布尔值、时间仍缺失不能通过。字幕是场景级或场景内估算细分的 SRT，目前不自动识别语音、不提供逐字对齐，也不默认烧进画面。

音轨保持原顺序和速度，转换为 AAC 48kHz 双声道；输入全局/音轨元数据和章节信息不会复制到成片。输出采用本工程默认 1080p30、H.264/yuv420p/MP4，不把该默认说成平台官方上限。详见 [video-assembly.md](video-assembly.md)。

### 分段录音

```json
{"schema":1,"clips":[{"id":"scene-001","path":"recordings/01.wav"},{"id":"scene-002","path":"recordings/02.m4a"}]}
```

```bash
pnpm creator:media audio-join --clips .local/某项目/clips-input.json \
  --output .local/某项目/joined-audio
```

按给定顺序完整解码并拼接，不自动去停顿、变速或交叉淡化。使用 joined.wav 作为后续录音；clips.json 保留按解码采样数计算的真实分段边界。如果录音段 ID/顺序与所有分镜完全对应，可由 `timeline --clip-cues .local/某项目/joined-audio/clips.json` 自动填入边界，工具会核对音频版本；否则仍用整轨时间轴人工调整。填入边界后保留 timing_confirmed=false，听看确认后再正式合成。

## 当前交付状态

- 工具与技术预览已实现，测试录音只用于验证合成过程；未生成 TTS、未收到或冒用用户旁白。
- 演示使用已有文稿，额外选择现有书单中的一条摘录作引用卡；没有改写原稿。
- 完整本人录音成片需要实际文件路径和时间轴确认。
- 专栏素材包和视频产物均只在本地，未上传、保存平台草稿或发布。
