# GOAL — lv3-transition 三阶段空间转场

日期：2026-09-18
前置：v4.4 panorama 架构已冻结（goal-v44-screen-shader-rebuild 全验收通过）
依据：Lv3 Clean Handoff + 案例研究 §5/§6 + 第三方遮罩方案（经修正）

## 目标

在 v4.4 冻结架构之上实现「红先泄露 → 黑吞噬 → 黄锁塔」三阶段空间转场，
并提供 `?record=1` 录制时间轴，供 0–5.5s 视频录制。

## 范围

1. **三阶段 reveal shader**：main_v44.js 的 screenColor() 中，
   `mix(reality, redblack, worldMix)` 升级为区域排序揭示：
   - 采样空间 = sourceUV（panorama 空间），不用 mesh vUv
   - 遮罩：leak（程序化垂直亮带+噪声，铰链 u=0.5 中心）、city silhouette、
     tower 程序化椭圆（中心与半径以最终 B 图重测为准）
   - uniforms：uLeak / uCollapse / uLock（替代单一 worldMix；worldMix 保留作 debug 后门）
   - 转场窗口（约 1.65–2.35s）内压制左屏 blur radius，防止 5×5 tap 拖糊红缝边界
2. **录制时间轴** `?record=1`（案例研究 §6）：
   0.00–1.20 Closed 稳定 → 1.20–1.65 展开 → 1.65–1.90 Red Leak →
   1.90–2.10 Black Collapse → 2.10–2.15 Yellow Lock + impact → 2.15–2.35 Open 稳定 →
   2.35–3.00 hero hold → 3.18 Lv1 塔脉冲 → 3.50–5.50 final hold
3. **impact @2.15s**：1 帧红/白闪 + 极短 RGB split（shader 层，不动几何）
4. **Lv1 脉冲 @3.18s**：塔锚点暖光晕脉冲 + 窗灯 ~25% 响应
5. **瞬态红 rim light**：Red Leak 窗口机身反光推红，过后恢复（无常驻灯光改动）

## 验收

- Tower Anchor Lock：全时间轴塔心 X 漂移 ≤8px（源图对齐后 3D 投影天然成立，截图抽帧验证）
- No-FX Test：关 pulse/impact 后 Closed→Open 仍一眼成立
- 三阶段因果顺序肉眼可辨（红→黑→黄不糊成一团）
- v4.4 既有 Test A–D 不回归

## 冻结/范围外

- v4.4 panorama 坐标/blur 架构不动
- 视频剪辑（音乐/节奏）只交付 spec 文档，不在本 goal 实施
- UI 拟真（状态栏/时钟/外壳材质）不在本 goal
