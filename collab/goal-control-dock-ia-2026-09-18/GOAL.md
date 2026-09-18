# GOAL — 操作区信息架构重组（Control Dock IA Rework）

日期：2026-09-18
前置：V5.1 Production Fold Baseline 已冻结；本 goal 在 work/v5.2-control-dock-ia 分支，不碰 main
依据：用户拍板的《操作区优化指引》（诊断 D1–D6 + 三层信息架构）

## 范围

1. **G1 操作条+时间轴**：transport 单行重排（主按钮 / 端点 chip / 时间轴 / 读数）；
   角度滑块加度数刻度（data-snap 复用既有跳转基建）；滑头角度读数气泡；
   新增 sequence strip：三段相位区带（closedHold/unfold/openHold）+ foldStart/foldEnd 锚点 + 播放头（play 跟 playbackTime、record 跟 recordT、scrub 经 ease 反解停泊）。
2. **G2 工作流面板分组**：dock 单栏化；Assets 并入 ① Setup（默认展开）；
   四段阶段卡 ① Setup → ② Quality → ③ Capture → ④ Accept；
   节点状态徽章图形化（todo/active/done→✓）；badge 摘要沿用既有 ID（fold-total-readout / qa-summary / recording-summary / export-acceptance-summary）。
3. **G3 模式互斥修复**：`[hidden]{display:none!important}` 全局守卫——修 record-hud 常驻可见（author display:flex 压 UA [hidden]）、export-review-wrap 同类潜在 bug。

## 验收

- 全部既有元素 ID/JS 契约不丢（master-pair-qa-panel / recording-editing-panel / export-acceptance-panel / #angle / #play-label 等）。
- CDP 截图：初始（Setup 展开）、母图上传后（节点 ✓）、播放中（气泡+播放头）、180°、Recording Mode（dock 隐藏仅 HUD）、Export 面板展开。
- 控制台 0 error；折叠/上传/QA/录制流程功能不回归。
- 视觉终验归用户；不合并 main，合并须用户拍板。

## 范围外

- 渲染/shader/几何/motionblur 契约不动；R&D Tower/Bird（G4）不在本 goal。
