# REVIEW — 操作区信息架构重组（v5.2-rc1 CANDIDATE）

日期：2026-09-18
分支：work/v5.2-control-dock-ia（基于 V5.1 冻结基线，未触 main）
验证：CDP 实驾 8 步全过 + vision 自检 5 帧 + 0 console error；证据 `evidence/dock_*.png`

## 交付对照（指引 → 实现）

| 指引项 | 实现 | 证据 |
|---|---|---|
| G1 topline 重排 | [▶Unfold] [Closed chip] [时间轴] [Open chip] [0%/0°] 单行 | dock_1 |
| G1 常量标题删除 | `.timeline-title-block` 移除（JS 引用均有 null 守卫） | dock_1 |
| G1 锚点刻度 | 0/45/90/135/180° tick，复用既有 `data-snap` 死基建（点击跳转+is-current 高亮即刻生效） | dock_3（点击 90°→angle 90） |
| G1 角度气泡 | 拇指跟随气泡，随 scrub/play 实时更新 | dock_4（166° 跟随） |
| G1 相位条 | sequence strip：closedHold/unfold/openHold 三段区带 + foldStart/foldEnd 锚点 tick + 播放头（play 跟 playbackTime、record 跟 recordT、scrub 经 foldEase 64 点反解停泊；motion 参数改动实时重算比例） | dock_1/4 |
| G2 dock 单栏化 | 两栏 → 单列 flex；Assets 并入 ① Setup | dock_1/6 |
| G2 四段阶段卡 | ① Setup ② Quality ③ Capture ④ Accept，序号节点图形化（active=环、done=绿底✓）；展开卡自动横跨整行，其余卡自然让位 | dock_2（✓）、dock_6 |
| G2 badge 规范 | 沿用既有 ID 文案管线（qa-summary 等零 JS 文案改动） | dock_2 |
| G3 互斥修复 | `[hidden]{display:none!important}` 全局守卫：record-hud 不再常驻（此前 author display:flex 压 UA [hidden]，生产上 HUD 全程可见）；export-review-wrap 同类潜在 bug 一并修复 | dock_1（hudHidden=true）、dock_7/8 |
| 互斥行为 | Recording Mode：dock/徽章 opacity 0、仅 HUD+safe frame；Exit 复原 | dock_7/8 |

## 偏差说明（相对指引）

1. **四卡默认全闭合**（指引写「① Setup 默认展开」）：viewport inset 固定 126px，展开态会压迫 3D 预览区——保持生产的紧凑默认，Setup 以 active 环提示为当前任务。
2. 度数 tick 置于滑块正下方独立行（不与轨道重叠），热区 18×9px。

## 观察（既有行为，非本次回归）

- Fold Motion badge 在交互后由「Fast Viral · 1.85s」翻转为「Custom · 1.85s」——用户提供的生产截图即为 Custom，本次 diff 未触 preset 逻辑（activeFoldPreset 代码路径零改动），判定为既有行为，不在本 goal 修。

## 验证记录

- ready、badge `v5.2-rc1 · CANDIDATE`、Setup is-active→is-done、tick90 跳转、bubble/playhead 同步、Recording Mode 进出互斥、0 console error。
- 既有契约未动：#angle slider、#play-label、面板 ID（master-pair-qa-panel / recording-editing-panel / export-acceptance-panel）、motionblur381 契约。

## 剩余 gate

- **视觉终验归用户**：本地 `http://127.0.0.1:8766/`（当前 checkout = 本分支）。
- 合并 main 须用户拍板（V5.1 baseline change policy）；合并后按标准流程生产 curl + CDP 复验。
