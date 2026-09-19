# GOAL — V6.11 官方渲染对齐（铰链/侧键 + R→L reveal + 锁屏 chrome 默认开）

日期：2026-09-19
拍板：用户给官方渲染参考，三点要求

## P1 外壳：上边框铰链凸出 + 右边框侧键收回

- 顶/底边铰链节微凸出框线（官方渲染锚点；当前 flush）
- 右下长键（USDZ y≈−2.62）收回贴框（撤 v6.4 +0.12 顶出）；上键（y≈+1.6）保留

## P2 Reveal 方向 R→L（record 路径）

- `seqR` 先行、`seqL` 延后；面板内前沿 lu 1→0（红世界从右缘进入向左推进，随展开）
- 预览均匀 crossfade 不动；staged（dev）不动

## P3 锁屏 chrome 默认开

- `screenChrome` 默认 true（`?ui=0` 关）；drawLockChrome 现有版式（日期+9:41+右上Wi-Fi+右下手电/相机+home条）
- 只画 RedBlack 世界；Reality 保持纯壁纸

## 验收

- cap 16:9：铰链节可见微凸、右下无凸键、上键可读；reveal 红从右向左；展开态时钟/Wi-Fi/手电/相机/ home 条清晰
- 预览 `?nofx=1` 同验；母版/几何/曝光（v6.10 锁定）不动
