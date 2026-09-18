# GOAL — V6.2 空间化 reveal + 真实外壳

日期：2026-09-19
拍板：用户确认 V6.2 方案（reveal 空间波前从左往右 / 塔后高光关闭 / 外壳钛金属原貌）
分支：work/v6.2-spatial-reveal

## 变更（全部 record 路径限定，预览零变化）

1. **空间 reveal**：新增 uniform uRevealFront（preview 恒 -1=关闭）。record 中 uRevealFront = easedFold×1.12；
   屏幕按 panorama uv.x 从左往右依次 Reality→Red/Black（smoothstep 软边 0.12）。
   塔区口袋照旧 hold 到 foldEnd+0.05→+0.35s 激活（在波前之后生效）。
2. **塔后高光关闭**：record 中 uTowerBoost=0（口袋翻转本身=第二击）。
3. **外壳真实**：record 中 uBezel=0（钛银扫光/折缝红光退出成片）；锁定 pop 减半保留。
   铰链真实几何不再弱化（官方卖点=Titanium frame and hinge cover）。

## 验收

- QC 新增空间门禁：t≈0.7s 左屏区红度 > 右屏区 +20；onset/冻结/全红/居中门禁沿用
- vision：中段帧左红右蓝渐变可见；hold 帧塔无辉光
- 三画幅终出（白底无音乐白片尾板）
