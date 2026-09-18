# GOAL — 操作区密度与遮挡治理（Dock Density & Occlusion）

日期：2026-09-18
前置：v5.2 操作区 IA 已上生产；用户 4 张截图实证多面板同开挤爆预览区（100% 遮挡）
分支：work/v5.3-dock-density（基 main b63f513+）

## 范围

1. **互斥浮层**：阶段卡面板一次只开一个；展开体脱离文档流为向上浮层（dock 高度恒定）；外部点击 / Esc 关闭。遮挡从常驻变瞬时。
2. **减层级减文字**：预设卡去副标题（转 title）；QA/Capture/Accept 说明段落移除（转 ⓘ tooltip）；Pass/Fail → ✓/✗ 图标钮（aria-label 保留）；Reset/Lock 图标化。
3. **滑轨与扭动钮**：Guide 分段 → iOS 拨动开关（#record-guide-toggle, role=switch）；Easing 下拉瘦身；时长滑轨保留。
4. **常驻条变薄**：dock 闭合高压缩；`#viewport` 保留区 126→112px；阶段节点序号改图标。

## 验收

- 互斥：开 Quality 再开 Capture → Quality 自动关；外部点击/Esc 关闭当前面板。
- dock 闭合高 ≤ 上一版；展开任意面板 dock 总高不变（浮层）。
- 小视口（900×700）面板浮层不超出视口。
- Guide 开关拨动同步 data-record-guide 语义与 safe frame 显隐。
- CDP 截图 + vision 自检 + 0 console error；既有 ID/契约不丢。
- 收尾按默认链：rebrand v5.3 → 合并 → 推送 → 部署 → 生产 CDP 核验。

## 范围外

- 渲染/几何/motionblur 契约；R&D Tower/Bird 线。
