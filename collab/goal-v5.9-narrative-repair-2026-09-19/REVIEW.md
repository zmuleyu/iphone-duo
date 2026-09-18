# REVIEW — v5.9 叙事修复 + 白底成片（G-G）

日期：2026-09-19
分支：work/v5.9-narrative-repair → 默认链收尾

## 根因记录（第三方报告的实证校正）

- 「0.2s 提前变红 + 中段涂抹」真相：**2× 超采样 @60fps 捕获吞吐不足 → 丢帧/冻结帧**（v5.8 成片 0.2-0.6s 网格逐位相同）；v5.4 1× 捕获时序本就正确。几何一直是 rigid panel——报告猜错归因。
- 真问题①：worldMix 几何映射 ~67° 即饱和（折叠 1/3 世界变完）→ record 路径改 25°→150°。
- 真问题②：塔随背景同步变 → uTowerMix 时间基延迟（foldEnd−0.05→+0.35s）+ uTowerBoost 暖光增益 ×0.55（塔格核亮度实测 **+39.9%**，与 bezel pop 同拍叠加成「第二击」）。
- 黑底根因：renderer alpha=0 清除 → 无 alpha 交付落黑。cap 模式改不透明白（预览不变）。

## 变更（record/cap 路径限定；预览与 V5.1 冻结契约零回归：uTowerMix 预览恒等 worldMix，uTowerBoost 预览恒 0）

- 捕获 pixelRatio 2×→1.5×（吞吐修复：247-257 帧、无冻结段）
- 16:9 zoom 1.0→1.25（设备占比提升）
- record 折叠段 blur ×0.35（uFoldBlurScale）
- QC 探针 qc_capture.py：红色时间轴 / 冻结帧 / 塔滞后 / 塔核亮度第二击（top-5 cell 指标——均值型指标被天空稀释，教训记录）

## 验证

- QC PASS（onset 0.7s / 无冻结 / 1.3s 全红 / 塔滞后 48vs78 / 激活 +39.9%）
- 白底四角亮度 ~253 ✓；vision 复核 hold 帧：白底/放大/琥珀塔/无 chrome ✓
- 0 console errors

## 遗留

- 母图 B 图形化减法模拟图 → 用户目检中（mock 入库与否待拍板）
- 塔激活增益观感（0.55）待用户目检，调旋钮 = shader 单常数
