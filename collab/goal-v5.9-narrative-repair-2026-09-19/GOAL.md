# GOAL — v5.9 叙事修复 + 白底成片（G-G/G-H）

日期：2026-09-19
拍板：用户确认 V5.9 方案（record 路径限定；母图 B 先出模拟 PNG 目检；成片无 chrome；白底仅录制+成片）
分支：work/v5.9-narrative-repair

## 诊断根因（实证）

- v5.8 成片「0.2s 提前变红 + 中段软变形」= 2× 超采样 @60fps 吞吐不足 → 捕获丢帧/冻结帧（v5.4 1× 捕获无此症）
- 真问题：worldMix 映射 ~67° 即饱和（折叠 1/3 世界已变完）；塔随背景同步变橙无第二击
- 黑底根因：renderer alpha=0 清除 → 无 alpha 交付格式落黑

## G-G 范围（record 路径限定，预览/V5.1 冻结契约不动）

1. 捕获 pixelRatio 2×→1.5×；QC 探针（红色时间轴+冻结帧+塔延迟）每片必跑
2. record worldMix：25°→150°（红随展开）
3. 塔延迟激活 110°→165°（towerContentMask，不动母图；预览 uTowerMix=worldMix 恒等零回归）
4. record 折叠段 blur ×0.35（uFoldBlurScale）
5. 16:9 zoom 1.0→1.25（裁切框随 safe-frame 自动重校）
6. cap 模式白底（opaque white clear）

## G-H 范围

7. 三画幅终出：白底、无音乐、无 chrome、轻晕影、白底石墨字片尾板
8. 母图 B 图形化模拟 PNG → 用户目检（不入库，拍板后再说）

## 验收

- [ ] QC 探针 PASS：onset ≥0.30s / 无冻结段 / 1.3s 全红 / 塔列滞后
- [ ] 0 console errors；生产 badge v5.9
- [ ] 终出三画幅 + 抽帧终检
