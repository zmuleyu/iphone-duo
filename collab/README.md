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
| V6.2 空间化reveal+真实外壳（v6.2） | 2026-09-19 | done→production（左→右波前reveal/塔辉光关/扫光退出成片） | [goal-t3-capture-2026-09-18](./goal-t3-capture-2026-09-18/GOAL.md) |
