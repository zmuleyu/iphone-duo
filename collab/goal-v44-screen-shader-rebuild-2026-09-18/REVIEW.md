# REVIEW — v4.4 Original Screen Shader Rebuild

日期：2026-09-18 · 执行：Hermes session（本机）

## 结果

v4.4 已上线（https://iphone-duo-lv3.vercel.app，badge v4.4）。
wrapper 架构（`main_v41d4.js` + `physicaldisplay431.js` 等 13 个模块）已停止加载并从
工作区删除（git 历史保留）。新主链：`bootstrap.js → motionblur381.js → main_v44.js`。

## 问题清单（第三方评审 + 代码实证）

| # | 问题 | 实证 |
|---|---|---|
| P0-1 | 统一 panorama 未成立 | `drawArtwork()` 把 outer canvas 画成 inner 右半裁切——两屏从源头是两张图；wrapper 事后共享 texture 会被 `setScreenMaps()` 回写 |
| P0-2 | 左屏 blur 不对 | blur 基于 `worldUv.x`，而 worldUv 来源不可靠（见 P0-3），blur 梯度没有物理意义 |
| P0-3 | shader authority 碎片化 | geometry UV 双公式烘焙（÷15.7987 / ÷7.73936）；431 对 `'vec2 worldUv = vMapUv;'` 的 replace 无失败检查；`frame431` 硬编码 inner frame 给两屏用（原版 outer 有独立深度补偿 frame）；main 与 431 双写同一批 uniforms |

第三方补充确认：P0-1/2 比文档描述更严重；支持 v4.4 重建；建议包内补录
`unifiedpanorama43.js` / `geometrytiming42.js`（已纳入本仓历史，本 goal 中已删除死代码）。
第三方一处误差已更正：`anchorX431` / `physical431Shader` / `physical431Wrapped` 在
完整版 `physicaldisplay431.js` 中有赋值（116/155/160 行）——是 excerpt 评审的假象，
不影响结论成立。

## v4.4 结构（对应 Review 输出格式）

1. **Root Cause**：见上表 P0-1/2/3。
2. **Architecture Verdict**：停止 wrapper，重建单一 screen shader authority。
3. **停止加载/删除模块**：`main.js`、`main_v41d4.js`、`physicaldisplay431.js`、
   `unifiedpanorama43.js`、`geometrytiming42.js`、`physicalcross41c.js`、
   `worldtransition41d(_v2).js`、`cinematicdof41b(_v2).js`、`defocus41.js`、
   `motionblur38.js`、`framing373.js`（commit 1e75ec8）。
4. **单一实现**：`main_v44.js`——原版投影 + 每世界单 canvas + shared worldMix。
5. **关键 shader**：原版 screenShader verbatim + `transitionTarget`/`worldMix`，
   顺序：fold → `vUIPosition` → 投影 `sourceUV` → 双世界同 UV 采样 → mix → blur/darken。
6. **35/50/70%**：见 evidence/testB_*（实图）与 testA_*（校准图）。

## 验收结果（CDP 实驾 chrome-debug:9222 + localhost:8766）

| Test | 内容 | 结果 |
|---|---|---|
| A | 校准图（网格/数字/穿铰链红线/单圆）35/50/70% | ✅ 红线连续、单圆不重复、数字不重复；50%（90°）左屏物理侧棱为正常现象 |
| B | 东京塔单锚点（实图 Reality/RedBlack） | ✅ 35/50/70% 均只出现一次，跨铰链连续 |
| C | Blur：铰链弱→左外缘强、右屏清晰 | ✅ 70% 明确成立（对照 Spline 127° 参考一致） |
| D | worldMix 0/0.5/1 同步 | ✅ 全局一致混合，无空间分裂 |

对照组：原版 chuspeeism build 在相同校准图、相同角度的截图（evidence/orig_*）
与 v4.4 逐点一致——包括 35% 时左侧可见面为 outer cover 及其透视拖影，属原版固有行为。

## 已知边界

- **35%（63°）左侧可见面 = outer cover**（原版物理模型决定：该角度 inner 左半背向被
  剔除）。cover 显示 hinge 锚定的同一世界右段，校准图上看似"圆在左侧再现"——
  与原版逐点一致，非回归。若要在 35% 隐藏 cover 需另立设计决策（doc 08 明确反对
  未经验证的人为规则），不在本 goal 范围。
- worldMix 沿用 geometry signal 简化 timing（g 0.10–0.92 窗口）；精调待 Freeze 后另议。
- shader 有一条 ANGLE 双精度 warning（X4122，原版即存在的常量表达式，无实际影响）。

## 生产资产名

`bootstrap.js`（v4.4 加载链）、`main_v44.js`、`motionblur381.js`；`build.json` build=4.4。
