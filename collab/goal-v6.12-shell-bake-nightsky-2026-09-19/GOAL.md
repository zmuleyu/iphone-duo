# GOAL — V6.12 外壳资产烘焙 + Night Sky 变体 + chrome 修正

日期：2026-09-19
拍板：1) 外壳 Star White 主 + Night Sky 变体、去右缘亮边；2) chrome 修正 + 铰链回平 + 资产烘焙

## 变更

1. `scripts/patch-shell-asset.py`：上键簇 +0.12x 烘焙进 `iPhone_Duo_Render.usdc`（幂等）；运行时按键/铰链偏移全删
2. 铰链：v6.11 凸出回退（官方=齐平）
3. `?shell=nightsky`：钛框族染深石墨；Star White 仍是默认
4. rim 1.4→0.85：去右缘亮带
5. chrome：Wi-Fi 内移防裁切；9:41 放大到官方占比（0.165h@0.215，date 0.034h@0.085）

## 验收

- cap 16:9：右轨单颗长键、四缘亮度均匀无右缘亮带、铰链齐平、Wi-Fi 完整、时钟大
- nightsky 静帧：框深黑统一、键可读
- reveal R→L / 曝光锁 / 母版不动
