# REVIEW — 操作区密度与遮挡治理（v5.3）

日期：2026-09-18
分支：work/v5.3-dock-density → 待按默认收尾链合并
验证：CDP 两轮（1440×900 + 900×700）全过 + vision 4 帧 + 0 console error；证据 `evidence/dens_*.png`

## 交付对照（用户要求 → 实现）

| 要求 | 实现 | 证据 |
|---|---|---|
| 避免遮挡主预览区 | 面板互斥（一次一个）+ 展开体改浮层：dock 闭合/开启恒 118px（实测相等），遮挡从常驻变瞬时；外部点击/Esc 关闭 | dens_1/2/3 + 高度探针 |
| 减少信息层级 | 四段阶段卡磁贴轨；说明段落（QA/Capture/Accept 3 处）移除并收进 ⓘ tooltip | dens_3/5 |
| 多使用图标 | 阶段节点序号→SVG 图标（sliders/shield/record/badge-check）；预设卡→图标+单行（副标题转 title）；Reset/Lock/Reset QC→圆形 ↻ 图标钮 | dens_2/5 |
| 减少文字内容 | Pass/Fail 文字钮→✓/✗ 图标钮（QA 5 行 + Accept 5 行，aria-label 全保留） | dens_3、dens_fix_5 |
| 滑轨/扭动按钮 | Guide 分段→iOS 拨动开关（#record-guide-toggle, role=switch, 实测 true→false→true 同步）；时长滑轨保留；Easing 下拉瘦身 | dens_4 |
| 减少空间占位 | dock 闭合高 118px（v5.2 ~132px）；#viewport 保留区 126→112px；行距/内边距全线下调 | dens_1 vs dock_1 |
| 优化交互 | 度数 tick 复用 data-snap 跳转（v5.2 保留）；浮层自动让位；小视口浮层内滚动兜底（900×700 实测 fits） | dens_sv_5 |

## 修复过程记录

- `.stage-panel[open]{grid-column:1/-1}`（v5.2 残留）导致开面板时磁贴轨折成两行（35→76px）——删除后浮层生效（高度探针实证 118=118）。
- Export ✓/✗ 编辑在批量脚本失败轮中丢失，vision 复筛捕获后补刀（dens_fix_5 确认）。

## 验证记录

- 互斥/外点/Esc/开关/浮层适配/0 console errors——两轮视口全过。
- 既有契约不丢：#angle、#play-label、三面板 ID、motionblur381、recordingMode 数据集。

## 收尾

按 9/18 默认链执行：rebrand v5.3 → FF 合并 → 推送 → ~70s → curl build.json → CDP 生产复跑（Page.bringToFront 防 rAF 节流假阳性）。
