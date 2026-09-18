# REVIEW — v5.7 屏幕 chrome 状态栏（G-C）

日期：2026-09-18
分支：work/v5.7-screen-chrome → 默认链收尾

## 交付

iOS 风格状态栏 chrome（可选层，默认关）：
- `?ui=1` 或 `__duo.setScreenChrome(true)` 开启；基线（无参）零变化（验证帧确认）
- 内容：左侧 9:41 时间；右侧 信号格/Wi-Fi/电池（75%）图标组；底部 home 指示条；白色 + 柔阴影，双世界皆可读
- 实现：Canvas2D 绘制进 world canvas（drawWorld 末端）——随屏幕几何折叠、透视、被 ?cap=1 捕获全部自然成立，零投影代码；上传时缓存 worldImages 供切换重绘
- 默认 UI 自带锁屏 chrome，不受影响；仅作用于自定义母图世界

## 验证

- ?ui=1 open：状态栏+home 条可见 ✓（9:41 左、图标组右）
- 无参 open：纯壁纸基线无变化 ✓
- 运行时 toggle：一致 ✓；两趟 0 console errors

## 设计说明

状态栏按「整屏内容」处理（横贯展开全景顶部）——等于横屏 iPad 式布局；折叠时随屏幕弯曲（物理正确的"屏幕内容"行为）。二期可加 dock 图标条（拍板再做）。
