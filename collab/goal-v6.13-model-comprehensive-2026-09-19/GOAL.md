# GOAL — V6.13 模型全面修复（对照 duowallpaper/onmyduo）

日期：2026-09-19
拍板：对照两参考站全面修复模型，不直接输出视频

## 审计发现 → 修复

1. **close 态 chrome 布局错**（真缺陷）：cover 只显示全景右半并拉宽 → 全宽布局的「9:」被切、home 条偏左。修：cover 区 chrome 以 u0.75 为中心 0.5 压缩（比例正确、9:41 完整）。
2. **右轨按键**：onmyduo（同一 Apple USDZ）= 两颗长键；且 0.12 顶出在 3/4 视角显浮。修：下键簇一并烘焙，凸出量 0.12→0.08。
3. **部署链缺陷**：Vercel buildCommand 只跑 prepare-assets（生产=未烘焙模型）。修：链上 patch-shell-asset.py，生产每次构建=烘焙模型。
4. **审计通过项**：背面白玻璃+双镜头胶囊岛（与 onmyduo 一致）；无 Apple logo（素材如此，不伪造）；铰链齐平；mid-fold 的 blur/darken 为 v4.4 锁定原版效果。

## 验收

- aud2 复核：close cover 9:41 完整、按键两颗无悬浮
- 生产部署后 usdc 哈希=本地烘焙版
- 不出视频（用户明确）
