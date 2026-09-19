# GOAL — V6.9 录制 rim 保持（外壳不再洗成银白）

日期：2026-09-19
拍板：用户红框标注 `duo_v6.7_16x9_1080p_final.mp4` 展开外壳变白/银；要求保持暖钛。

## 根因（对照实证）

1. v6.8 现场 `?cap=1` @180° 静帧：边框已读香槟/暖钛。
2. v6.8 成片末帧边框 RGB≈(204–221, 206–224, 205–223)，warm≈0，与 v6.7 无差。
3. `driveRecord` 每帧执行 `rim.intensity = 2; rim.color = (0.91,0.93,0.96)`（生产 `STAGED_REVEAL=false` 时 rw=0），覆盖 v6.8 的暖 rim 1.4 / `0xf5e8d8`。
4. 录制结束再 `rim.color.setHex(0xe8edf5)`，定格尾帧被冷白洗成银。

## 修复（cap 路径限定）

- 抽出 `applyCapRim()`：intensity 1.4 + `0xf5e8d8`
- cap 且非 staged：录制循环与结束态保持该 rim，不再写回冷白
- 预览/非 cap 路径不动

## 验收

- 录制中 180° 静帧与成片末帧：边框暖钛，不与白底融成银白
- 母版 / 几何 / reveal / 剪辑配方不变

## 终局转向（2026-09-19 用户拍板）

暖钛方向被用户否决（官方=中性星光银白，白底下暖色读「银里透黄」）。**全部删除 v6.4-v6.9 外壳 tweak**（tint/satin/env/key/rim/hemi/applyCapRim/rim guard），回到 stock 渲染（=v5.1/plate 通过的同款）。A/B 实证：stock 白底=自然银白、按键可见、左缘亮带无回归。并行 lane 的 WIP 已 stash 保全（git stash list 可恢复）。
