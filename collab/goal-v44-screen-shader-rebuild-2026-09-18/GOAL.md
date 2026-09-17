# GOAL — v4.4 Original Screen Shader Rebuild

日期：2026-09-18
来源：iPhone_Duo_ThirdParty_Review_v4.3.1（Review Pack）+ 第三方评审结论（Claude，2026-09-17/18）

## 目标

停止 v4.3.1 wrapper 架构，以原始 `chuspeeism/iphone-duo/main.js` 的 screenShader 为唯一
坐标/blur authority，重建单文件主实现 `main_v44.js`，使：

1. 左右两屏成为 **同一张 panorama 的两个连续视口**（P0-1）
2. 左侧 moving inner panel 的 blur/darken 复现参考行为：hinge 弱 → 左外缘强，右屏清晰（P0-2）

## 已确认根因（代码实证）

- **数据层**：`main_v41d4.js drawArtwork()` 把 outer canvas 绘制成 inner 图的右半裁切
  （`outer.drawImage(inner, inner.width/2, 0, ...)`）——两屏从源头就是两张不同裁切；
  wrapper 事后强制 `outer.map = inner.map` 会被 `setScreenMaps()` 在上传/换主题时回写。
- **坐标层**：geometry UV 烘焙用两套硬编码公式（inner ÷15.7987 / outer ÷7.73936，Y 亦不同），
  `vMapUv` 永远不是统一 panorama 坐标；`physicaldisplay431.js` 对
  `'vec2 worldUv = vMapUv;'` 的 string replace **无失败检查**，静默失败即回退到双局部 UV。
- **Frame 层**：431 把 `frame431` 硬编码为 inner frame 同时用于两屏；原版使用 per-kind
  `uiFrame`（outer frame 有深度补偿 ×1.0147 与独立 Y offset/height）。outer Y 从未重锚定。
- **Authority 碎片化**：main 的 `setAngle` timing 与 431 的 geometry timing 双写同一批
  shared uniforms；compile-hook 套 compile-hook；`isCustomReady()` 门控 uniform 更新。

## 方案（第三方唯一推荐）

v4.4 = Original Screen Shader Rebuild：

- 每世界单 canvas：`RealityCanvas 1600×1125` / `RedBlackCanvas 1600×1125`，无 inner/outer 对
- 两屏 material 共享 uniform holders：`realityMap`（=map）、`transitionTarget`、`worldMix`、
  `uiFrame`、`uiGradient`、`uiPixel`、`uiReferenceEye`、`foldAngle`
- shader 顺序：fold 后 `vUIPosition` → 原版 fixed-front 投影 `sourceUV` → 同 UV 采样
  Reality/RedBlack → `worldMix` → 原版 blur/darken（5×5 加权 + LOD + coverage）
- outer cover 显示/隐藏完全回到原版：`color.setScalar(angle >= 180 ? 0 : 1)`，无人工 fade 曲线
- worldMix：geometry signal 简化 timing + `window.__duo.setWorldMix()` debug override

## 验收标准（全过才 Freeze）

- **Test A — Same-image continuity**：Reality/RedBlack 传同一校准图（网格+数字+穿 hinge
  直线+单一大圆）。35%/50%/70%：grid 连续、直线跨屏可解释、大圆不重复。
- **Test B — Tokyo Tower one-anchor**：同一张 Reality。35/50/70% 东京塔只存在一个空间位置；
  moving left panel 只显示 panorama 中被它物理覆盖的部分。
- **Test C — Blur**：50–70%：fixed right inner sharp；moving left inner blur；hinge 弱、
  左外缘强；blur 不改变 panorama 内容 identity。
- **Test D — World mix**：A/B/C 过后，Reality→RedBlack 在两屏同一 `worldMix` 下同步切换，
  且不破坏 1–3。

## Stop Conditions（全部通过即 Freeze，不再改 panorama 架构）

1. Same-image calibration 不重复
2. 东京塔只出现一个视觉锚点
3. 左 inner blur / 右 inner sharp 明确成立
4. Reality → RedBlack 不破坏 1–3

## Freeze / 范围外

- Step 3.7.2 framing：冻结（原样移植，不调）
- fold geometry：不改
- motionblur381.js：保留（shell 拖影，非 P0）
- worldMix 精调 timing：panorama+blur 验收后再议
- 「杀死比尔式空间转场」氛围：P0 之后另开 goal，届时在 Review Pack 写具体参考镜头
