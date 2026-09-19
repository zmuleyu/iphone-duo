# GOAL — V6.10 Star White 可读性（白底金属分离）

日期：2026-09-19
拍板：用户确认按建议彻底解决（不是暖钛 vs Star White）

## 问题

官方 iPhone Duo = Star White / Night Sky、抛光 5 级钛。红框「错误外壳」= 白底上框被打爆成纸白，不像金属。网页 `?nofx=1` 透明 canvas 贴 `#f6f6f3`，展开后右缘消失。

## 非目标

- 不改 albedo / 不做暖钛 tint / 不恢复 v6.4–6.8 色锁
- 不把假 bezel sweep 当生产色

## 修复

- 预览与成片同一套曝光：env/hemi/key/rim 下调，rim 保持冷白 `0xe8edf5`
- 预览 canvas 不透明清成页面色 `#f6f6f3`；cap 仍白底
- 生产预览 `uBezel/uBezelPop = 0`（与成片一致，消除展开变色）
- 保留 cap 侧键外探 + inner overscan

## 验收

- `?nofx=1` @180°：框在页面上可读，不融进白底；侧键可见；非香槟/石墨
- cap 16:9 展开成片同样
- 屏幕母版/几何/reveal 不变
