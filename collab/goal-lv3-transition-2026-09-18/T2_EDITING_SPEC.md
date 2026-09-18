# T2 — 视频剪辑 Spec（V5.1 Production Fold Baseline）

日期：2026-09-18
状态：spec 交付（按 lv3 GOAL 约定：剪辑只交 spec，不在仓内实施）
适用基线：V5.1（`v5.1-production-fold`，生产 reveal = clean crossfade）

## 1. 捕获（Capture）

| 项 | 设定 |
|---|---|
| 页面 | 生产 `https://iphone-duo-lv3.vercel.app/` 或本地等价 checkout |
| 入口 | Recording Mode（UI 进入，隐藏开发元素）或 `?record=1` 自动起录 |
| 浏览器 | Chrome，窗口 1440×900 |
| 录屏 | OBS Studio，1440×900@60fps，H.264，CRF 18–20 |
| 母图 | master 对（`Downloads\duo\新建文件夹\`），先上传再进 Recording Mode |
| Safe frame | 录制时 guide = On；交付前按目标画幅各录一遍 |

确定性保证：录制时钟按帧量化（`t = frameIndex / recordFps`），同一预设+fps 下每次 run 的逐帧内容一致；`document.documentElement.dataset` 暴露 `recordT / recordFrame / recordDuration / recordDone`，OBS 起停以 `recordDone=1` 为终点。

## 2. 时间轴锚点（60fps 帧号）

序列 = `closedHold → unfold → openHold`，总时长 = 三段之和。关键锚点：**fold start**（运动起点）与 **fold end**（展开锁定点 = 全片唯一重音）。

| 预设 | closedHold | unfold | openHold | fold start | fold end | 总时长 | fold start 帧 | fold end 帧 |
|---|---|---|---|---|---|---|---|---|
| Fast Viral | 0.18 | 1.15 | 0.52 | 0.18s | 1.33s | 1.85s | 11 | 80 |
| Cinematic | 0.40 | 1.85 | 0.85 | 0.40s | 2.25s | 3.10s | 24 | 135 |
| Slow Demo | 0.65 | 2.80 | 1.20 | 0.65s | 3.45s | 4.65s | 39 | 207 |
| Custom | 按 UI 值 | | | = closedHold | = closedHold+unfold | 三段和 | ×fps | ×fps |

30fps 时帧号减半。V5.1 生产时间轴**无**塔/鸟/impact/pulse 事件（仅在 dev staged 线存在，见 §6）。

## 3. 剪辑规则

1. **重音对帧**：音乐唯一的强拍/踩点必须落在 fold end 帧（展开锁定瞬间）；次重音可对 fold start（运动启动）。两锚点间（折叠段）是连续运动，**禁止跨折叠段做速度斜坡**（speed ramp），只允许整段统一 retime。
2. **起止**：片头从 closed hold 中段切进（留 ≥6 帧稳定闭合画面建立构图）；片尾在 openHold 内收，Fast Viral 可硬切循环回开头（closed≈open 构图差即循环张力）。
3. **预设选型**：Shorts/TikTok/Reels 用 Fast Viral（1.85s 可直发或 2–3 循环拼接）；品牌/官网 hero 用 Cinematic；演示讲解用 Slow Demo。
4. **Motion blur**：Fast Viral/Cinematic 录 Natural；Slow Demo 录 Off（预设已绑定，不要手改）。
5. **音乐**：仅后期叠加，不进录制环境；避免在 fold end 前后 ±3 帧内安排歌词咬字，保留机械锁定感的音效空间（可叠轻微 click/snap 拟音，-18dB 以下）。

## 4. 画幅与导出

| 画幅 | 平台 | 录制设定 | 导出 |
|---|---|---|---|
| 16:9 | YouTube / X / 官网 | format=16x9, 60fps | 1920×1080 H.264 高码率（≥12Mbps） |
| 9:16 | Shorts / Reels / TikTok | format=9x16, 60fps | 1080×1920，主体居中裁切，塔心保持画面中轴偏上 1/3 |
| 1:1 | 信息流 | format=1x1, 60fps | 1080×1080 |

- 每个画幅单独用对应 safe frame 重录，**禁止**用 16:9 素材后期裁 9:16（safe frame 的意义就是构图前置）。
- 平台二压核验：上传后回看折叠段是否有色带/涂抹（红天空是二压重灾区）；若出现，上传码率提档或改 ProRes 中间片交平台转码。

## 5. QC 门禁（剪辑前置）

素材进剪辑前必须过 Export Acceptance：
- 自动项全绿：capture metadata、deterministic clock pass、endpoint angle、master pair pass
- 人工 5 项全 PASS：Motion Blur / Hinge / Open Endpoint / Crop Safety / Compression
任一不过 → 重录，不剪带病素材。

## 6. 附录：dev staged 线（非生产）

三阶段 reveal（红泄露→黑吞噬→黄锁塔）在 V5.1 中仅 `?dev=1&reveal=staged` 可达，锚点按 unfold 段归一化：leak 55%–72%、collapse 72%–90%、lock 90%–100%。该线历史锚点（2.15s impact / 3.18s pulse，基于 unfold=1.80s 时代）已作废，如需 staged 变体视频按归一化锚点重算帧号。**staged 素材不得标注为生产效果。**
