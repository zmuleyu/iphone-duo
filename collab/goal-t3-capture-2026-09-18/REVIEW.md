# REVIEW — T3 母带捕获管线（v5.4）

日期：2026-09-18
分支：work/v5.4-capture → 默认链收尾
交付：`C:\Users\Admin\Downloads\duo\交付\`

## 交付物

| 文件 | 规格 | 用途 |
|---|---|---|
| duo_v5.4_16x9_1080p_fastviral_draft.mp4 | 1920×1080 · 60fps · 2.37s | YouTube/X/官网 |
| duo_v5.4_9x16_1080x1920_fastviral_draft.mp4 | 1080×1920 · 60fps · 2.37s | Shorts/Reels/TikTok |
| duo_v5.4_9x16_loop3_draft.mp4 | 1080×1920 · 7.10s | 3 循环短循环版 |
| duo_v5.4_1x1_1080_fastviral_draft.mp4 | 1080×1080 · 60fps · 2.37s | 信息流 |
| duo_v5.4_*_60fps_custom.webm ×3 | 1440×900 原始母带 | 剪辑中间片（文件名 custom 为标签 bug，内容=Fast Viral 1.85s） |

## 新增能力（代码）

1. `?cap=1` 页内捕获器：canvas.captureStream + MediaRecorder VP9 20Mbps，recordDone 自动收尾下载，dataset.captureDone 可轮询；常态零行为变化。
2. **Recording Mode 电影取景**（本次 QC 发现的真实缺口）：9:16/1:1 竖方画幅在 open 态原本装不下横展设备（设备中心偏左且超宽）。新增逐帧取景：record 期间相机随折叠进度 dolly-out（9x16 zoom 1→0.62）+ 平移回中（1x1 panX -132 / 9x16 -103）；16:9 不变；退出录制模式复位。预览路径零影响。
3. 捕获收尾 +0.5s 静态尾帧（剪辑手柄）。

## 验证

- 帧计数：16x9=142 / 9x16=142 / 1x1=130（序列 111 + 尾帧 pad，无丢帧；前台标签页是关键，后台 rAF 节流会掉帧——首跑教训）
- vision 抽帧：闭合 Reality ✓ / 半折立体 ✓ / open RedBlack ✓ / 三画幅构图居中完整 ✓
- 0 console errors；生产无 `?cap=1` 不受影响

## 已知项（不阻塞草稿）

- 预设标签 custom 误显示：进入录制流程后 activeFoldPreset 被置 null（foldMotion 数值不变、badge 总时长正确），根因未定位；文件名与 Setup badge 文案受影响，内容不受影响。
- 音乐/卡点剪辑属 NLE 人工阶段（spec §3）；如需上音乐轨，用 media-studio/opencut。
- 9:16 设备右缘余量 ~19px（已校准），如需更宽余量可调 panX。

## 媒体工具判断

草稿阶段 ffmpeg 足够（裁切/缩放/循环确定性强）；opencut/remotion 留给音乐+精剪正式版。
