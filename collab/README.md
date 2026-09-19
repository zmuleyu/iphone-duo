# collab — Goal 登记表

| Goal | 日期 | 状态 | 目录 |
|---|---|---|---|
| v4.4 Original Screen Shader Rebuild | 2026-09-18 | done（用户目检通过，架构冻结） | [goal-v44-screen-shader-rebuild-2026-09-18](./goal-v44-screen-shader-rebuild-2026-09-18/GOAL.md) |
| lv3-transition 三阶段空间转场 | 2026-09-18 | superseded by V5.1（staged 转入 dev-only；T2 剪辑 spec 已交付） | [goal-lv3-transition-2026-09-18](./goal-lv3-transition-2026-09-18/GOAL.md) |
| R&D 评审 v5.0.7.3 Hero Tower + Spire Birds | 2026-09-18 | dropped（用户拍板 2026-09-18：飞鸟效果过于机械化，整线弃用；塔/鸟 FX 不晋升） | [goal-rd-hero-tower-birds-2026-09-18](./goal-rd-hero-tower-birds-2026-09-18/REVIEW.md) |
| 操作区信息架构重组（v5.2） | 2026-09-18 | merged→production（用户拍板合并 2026-09-18） |
| 操作区密度与遮挡治理（v5.3） | 2026-09-18 | merged→production（v5.3 已上线核验） | [goal-dock-density-2026-09-18](./goal-dock-density-2026-09-18/REVIEW.md) | [goal-control-dock-ia-2026-09-18](./goal-control-dock-ia-2026-09-18/REVIEW.md) |

## 生产基线

- **V5.1 — Production Fold Baseline**（2026-09-18 冻结）：`v5.1-production-fold`，交接边界见根目录 `PRODUCTION_BASELINE_V5.1.md`。
- Tower / Bird / displacement / 新转场一律独立 R&D 分支起步，晋升须独立视觉验证 + 用户拍板。
| T3 母带捕获管线（v5.4） | 2026-09-18 | done→production（三画幅草稿已交付） |
| G-A 采集质量（v5.5） | 2026-09-18 | done→production（2x 超采样+颗粒+CRF16 重出草稿） |
| G-B 边框光亮过渡（v5.6） | 2026-09-18 | done→production（钛银扫光+open pop，待用户目检） |
| G-C 屏幕 chrome 状态栏（v5.7） | 2026-09-18 | done→production（?ui=1 状态栏层） |
| G-D AI 飞鸟底板 | 2026-09-18 | done（双画幅底板+prompt 文档已交付；AI 工具运行=外部卡点） |
| G-E/F 锁屏 chrome + 音效成片（v5.8） | 2026-09-19 | done→production（三画幅有声成片已交付；音乐后撤） |
| G-G/H 叙事修复+白底成片（v5.9） | 2026-09-19 | done→production（红随展开25-150°+塔第二击+白底无音乐终出；母图mock目检中） |
| V6.0 塔激活性叙事（v6.0） | 2026-09-19 | done→production（Reality口袋+0.3s激活+图形化母图+16:9居中） |
| V6.1 Clean Hero（v6.1） | 2026-09-19 | done→production（母图v2压halo/纯天/灯减半+塔光收敛+轻晕影；含6.0.1 9:16居中） |
| V6.2 空间化reveal+真实外壳（v6.2） | 2026-09-19 | done→production（左→右波前reveal/塔辉光关/扫光退出成片） |
| V6.3 回归原始母版+逐面板reveal（v6.3） | 2026-09-19 | done→production（图形化过滤否决,回退原母版;接续reveal;1.25x捕获） |
| V6.4 外壳保真（v6.4） | 2026-09-19 | done→production（侧键显现+暖钛框+去爆白） |
| V6.5 冷晕/白缝/节奏（v6.5） | 2026-09-19 | done→production（内容遮罩回退+overscan+3.73s剪辑） |
| V6.6 左缘亮带（v6.6） | 2026-09-19 | done→production（cap key 1.7） |
| V6.8 外壳颜色锁定（v6.8） | 2026-09-19 | done→production（暖rim+缎面钛+中灰族tint；定格剪辑v6.7配方） |
| V6.9 外壳 stock 回归（v6.9） | 2026-09-19 | done→production（v6.4-6.9 色彩 tweak 全删;并行WIP已stash） | [goal-v6.9-cap-rim-hold-2026-09-19](./goal-v6.9-cap-rim-hold-2026-09-19/GOAL.md) |
| V6.10 Star White 可读性（v6.10） | 2026-09-19 | done→production（曝光锁定 env0.92/hemi1.15/key1.7/rim1.4；预览不透明白+关假扫光；色号不动） | [goal-v6.10-shell-exposure-2026-09-19](./goal-v6.10-shell-exposure-2026-09-19/GOAL.md) |
| V6.11 官方渲染对齐（v6.11） | 2026-09-19 | done→production（铰链凸出+下键收回；reveal R→L；锁屏 chrome 默认开） | [goal-v6.11-official-align-2026-09-19](./goal-v6.11-official-align-2026-09-19/GOAL.md) |
| V6.12 外壳烘焙+Night Sky+close 对齐（v6.12） | 2026-09-19 | done→production（键/铰链入资产；rim 0.85 去右缘亮带；chrome 双世界+放大修正；?shell=nightsky） | [goal-v6.12-shell-bake-nightsky-2026-09-19](./goal-v6.12-shell-bake-nightsky-2026-09-19/GOAL.md) |
