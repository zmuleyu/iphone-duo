# GOAL — V6.0 World Transition → Tower Activation

日期：2026-09-19
拍板：用户 V5.9 评审四点反馈 + 「下一版只做一件核心事：World Transition → Tower Activation」+ 16:9 open 水平居中
分支：work/v6.0-tower-activation

## 四点反馈 → 修复

1. 塔激活仍太早（0.8–0.9s 随背景同步）→ uTowerMix 窗口整体移到 foldEnd+0.05→+0.35s（0.3s 快激活）；
   塔区遮罩从内容mask（只覆盖亮格）改为**几何椭圆全区**（towerMask）——塔+周围天空口袋整体保持 Reality 蓝到完全展开，真正第二击。
2. 铰链 0.5–0.8s 机械感（银白窄条抢眼）→ record 折叠段 uBezel ×0.35 弱化扫光/折缝红光；open pop 不动。
3. Red/Black 不够纯（窗灯多、摄影纹理）→ 母图 B 确定性图形化（非 AI 再生）：天空两段平涂红渐变、城市近纯黑、窗灯 -56%、塔区原样保护。
   产物 = 独立新文件 `1-1 Tokyo_Tower_RedBlack_Graphic_2670x1878.png`（原 RedBlack_Final 不动；随时可换回）。
4. 1.2s 后静止过长 → 激活窗口本身移入 hold 段头部（foldEnd+0.05s 起），hold 不再纯静止。

附加：16:9 open 态水平居中——实测设备偏左 251px（-13% crop 宽），panX 0→-134。

## 验收（QC 探针 qc_capture.py 同目录）

- red onset ≥0.30s；0.4–1.3s 无冻结帧；1.3s 全红
- 塔区蓝通道 1.10s 仍高于 1.75s（Reality 保持到完全展开）
- 塔核 top5 亮度 1.30→1.75s 升幅 ≥15%（第二击）
- 16:9 hold 帧设备质心水平偏移 ≤2%
- 预览/V5.1 冻结契约零回归（所有改动 record/cap 路径限定）

## Stop Conditions

用户目检 V6.0 成片 + 图形化母图效果后 Freeze。
