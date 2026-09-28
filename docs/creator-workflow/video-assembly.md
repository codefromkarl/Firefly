# 图片与本人录音的视频合成

`creator_system.video` 将本地 PNG 分镜与一条完整自录音轨合成为视频。它不生成 TTS、不下载录音、不调用外部生成服务，不把测试声音当作本人旁白。没有录音时返回 `status=missing_audio`，不会生成“成功视频”。

## 输入与接口

```python
probe_audio(path)
# 返回真实 ffprobe 时长、起始时间、codec、采样率、声道、文件哈希与字节数。

resolve_timeline(manifest, audio_duration, *, preview=False)
# 返回 timing=explicit/estimated、timing_confirmed、audio_duration、连续 scenes。

assemble_video(frames_manifest_path, output_dir, *, preview=False)
# 返回 build-report；只在全部媒体检查完成后创建最终输出目录。
```

`frames.json`：

```json
{
  "schema": 1,
  "title": "本期标题",
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "timing_confirmed": true,
  "demo_audio": false,
  "audio": {"path": "本人录音.wav"},
  "scenes": [
    {"id": "scene-01", "image": "frames/scene-01.png", "narration": "本段字幕。", "start": 0.0, "end": 3.2, "source_refs": []}
  ]
}
```

录音路径可相对 manifest 或为本地绝对路径；图片路径同理。只接受普通本地文件，拒绝符号链接和网络协议。全部 PNG 尺寸必须与 manifest 一致；宽高必须为偶数。支持 WAV/MP3/M4A/AAC/FLAC/OGG/Opus/AIFF 等本地音频，实际以 ffprobe 成功读取单一音轨为准。音频有多条轨道或无法确定时长时明确拒绝，不猜选某一轨；异常非零起始时间也不自动裁切。

## 时间轴和本人录音

正式合成需要同时满足：

1. 每个场景都有明确 `start/end`。
2. 所有时间为有限数值；从 0 开始，连续，无重叠、空洞或越界。
3. 最后一段覆盖完整录音时长，浮点比较允许 1 毫秒精度误差。
4. `timing_confirmed` 严格为布尔 `true`。
5. 每段至少占用一帧；`demo_audio=true` 只允许预览。

仅设置确认标志、仍缺 start/end 不能正式合成。全部 start/end 缺失时，只有 `preview=True` 才会按 narration 字数估算；部分有时间、部分缺失直接拒绝，避免把人工时间与估算悄悄混合。估算结果标 `timing=estimated`，需要在听本人录音后逐段调整并确认。

默认保留完整音轨的顺序与速度：不使用音轨裁切、变速、`-shortest` 或总输出 `-t`。按输出要求转为 AAC、48 kHz、立体声；只对视频末帧做补齐/收边，使画面覆盖录音。场景边界按输出帧率量化，编码器可能有少量帧或音频 padding 误差，成片会实际检查起止和时长。合成器接收单一完整音轨；分段录音可先用文末的 audio_join 工具拼接。当前没有自动语音识别、逐字对齐或音量美化。

## 输出与检查

输出目录包含：

| 文件 | 用途 |
| --- | --- |
| `video.mp4` | H.264 / yuv420p 画面、AAC 48 kHz 双声道录音 |
| `subtitles.srt` | 场景级字幕或场景内估算细分字幕 |
| `timeline.json` | 本次实际采用的 cue、估算/明确标记及原场景信息 |
| `poster.jpg` | 首帧封面；预览封面保留水印 |
| `build-report.json` | 输入身份、工具版本、产物哈希、音画检查结果和预览状态 |

1920×1080、30 fps 是此工程默认值，不是 B 站官方上限。实际成片通过 ffprobe 校验 codec、pixel format、帧率、尺寸、采样率、声道、音轨/视频起始时间与完整录音覆盖。ffmpeg 线程限制为 2。命令通过 argv 调用，不使用 shell；concat 文本只写入自己生成的固定文件名。临时帧副本、音频副本、concat 文件不进入最终包。

字幕默认作为旁挂 SRT，不烧进画面。场景 narration 超过两行时，每行最多 36 字符，切分为多个两行块；没有语句级时标，因此切分后的时长只能按场景均分估算，报告明确 `estimated_segments_within_scenes`，不能称为逐字识别。过密到无法形成有效 cue 的文字会拒绝，需要先拆镜/重配时间。发布前仍需听看：程序的时长检查不代表口播与画面语义同步。

所有预览都会把水印画到临时帧副本，绝不改用户原图。普通预览显示“预览 · 时间轴待确认”；`demo_audio=true` 显示“预览 · 测试音频”。技术测试音轨只是合成可用性测试，不代表已经收到本人旁白。

## 重跑、修改和交付边界

最终目录按版本保留。同一输入内容、manifest、预览模式、工具版本再次运行时，核对所有产物哈希后才复用；录音或图片变更、manifest 改动、产物被手工修改，都拒绝覆盖该目录，需要选择新的版本目录。未知目录中的文件不会被覆盖。渲染中发现输入变化，停止，不发布本地成功包。项目内部输出必须放在 `.local/`，不能写入 `src/public/docs`。

全部输出先在私有临时目录完成验证，再一次性改名为最终目录；工具失败和半成品不能返回 assembled。整个操作没有平台上传或发布动作。时间轴/报告属于私有工程材料，公开交付通常选用 MP4、封面和经过检查的字幕。

## 实际验证

本机 ffmpeg/ffprobe 已存在，没有安装依赖。测试自动生成 320×180 彩色 PNG 和 1 秒合成测试音，真实执行四次媒体合成：WAV 估时预览、WAV 明确时间轴、MP3、M4A；分别验证完整录音与码流。另测缺音频、损坏音频、尺寸不符、NaN/空洞/重叠/截尾、确认标志不足、demo 正式合成拒绝、缓存输入变化、手改产物、未知目录保护和长字幕行数。

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s scripts/creator_system -t scripts -p 'test_video.py'
```

这些合成测试不使用用户录音；用户尚未提供的录音路径不能填造，正式本人旁白成片仍以实际音频接入和听看确认作为完成条件。

## 本人分段录音

分段录音先用 `creator_system.audio_join.join_recordings(clips_manifest_path, output_dir)` 合并，再把生成的 `joined.wav` 作为视频 manifest 的 `audio.path`。CLI 提供 `audio-join --clips <录音清单.json> --output <新版本目录>`；准确的全局参数顺序以主 CLI 的 `--help` 为准。

```json
{"schema":1,"clips":[{"id":"opening","path":"录音/开场.wav"},{"id":"argument","path":"录音/论证.m4a"}]}
```

模块严格按数组顺序完整解码每段至 48 kHz、双声道、16 位 PCM WAV，再按采样帧顺序拼接。不剪停顿、不变速、不做交叉淡化，不修改原录音，也不代替用户补录。每段规范化后的实际采样帧数决定 `clips.json` 的 start/end，因此 MP3/AAC 解码 padding 不会被伪装为精确的原容器时长。最多 100 段、总计 4 小时，避免 PCM WAV 的 RIFF 大小限制。

输出 `joined.wav`、私有段落映射 `clips.json` 和 `join-report.json`。映射包含段落 ID、原文件哈希、实际解码时长和累计起止；它是录音工程资料，不是公开字幕。输入元数据不写入最终 WAV。重复运行仅在输入及所有产物哈希一致时复用；顺序改变、文件改变、已有未知目录或手改产物均拒绝覆盖，需新版本目录。

验证使用两个不同频率的合成短音：实际 FFmpeg 解码与拼接后检查 WAV 采样帧数、总时长、段落顺序和零交叉频率，并检验坏录音、多音轨拒绝及私密音频标签不会进入 WAV。没有访问任何用户录音。
