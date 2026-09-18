# GOAL — V6.1 Clean Hero + Export Cleanup

日期：2026-09-19
拍板：用户转第三方 V6.0 减法分析（烟雾/光柱/点阵删、塔 glow 收敛、窗灯减 50-70%、结尾边框检查、四层极简）
分支：work/v6.1-clean-hero

## 落地

- 母图 B v2：塔区只保护 warm lattice 像素（lum>0.30，实测 halo≤0.23 / lattice p50=0.45）→ 穹顶 halo/烟雾压除；天空全区平涂渐变（移除暖点豁免=塔吊光柱消失）；城市 lum<0.35 纯黑、窗灯 lum>0.70（再减半）
- uTowerBoost 0.55→0.35（单一稳定橙黄发光，不过曝）
- 成片 vignette PI/6→PI/10（消除「边框感」）
- 结尾边框问题：抽帧实证 v6.0 末段干净无 UI 边框（圆角裁切正常、无露缝）→ 无需 overscan，仅记档
- 展开真实感：核对 Apple 官网 iPhone Duo 页（book 式开合/闭合竖屏外屏/展开横屏/under-display camera 无开孔）——当前实现一致；record 缓动维持 ease-in-out（v6.0 已验证时序，勿改）

## 验证

三画幅 QC PASS + vision 口袋帧/hold 帧双过（四层干净、口袋保持、塔发光收敛、居中 +0.00%）
