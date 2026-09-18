# GOAL — v5.7 屏幕 chrome 状态栏（G-C）

日期：2026-09-18
拍板：按建议依次 goal 执行（G-A ✅ → G-B ✅ → G-C → G-D）
分支：work/v5.7-screen-chrome

## 范围

1. ?ui=1 / __duo.setScreenChrome 开关的 iOS 状态栏 + home 指示条
2. Canvas2D 绘入 world canvas（随折叠/捕获自然成立）
3. 基线默认关、可运行时切换

## 验收

- [x] ?ui=1 open/closed 状态栏可见
- [x] 无参基线零变化
- [x] 运行时 toggle 一致
- [x] 0 console errors
