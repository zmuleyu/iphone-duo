# REVIEW — V6.0 World Transition → Tower Activation

日期：2026-09-19
分支：work/v6.0-tower-activation → 默认链收尾

## 四点修复落地

1. **塔第二击**：uTowerMix 窗口 foldEnd+0.05→+0.35s（0.3s snap，完全展开后单独激活）；
   塔区遮罩改为几何椭圆全区 → vision 实证 1.10s「红天围困的蓝紫 Reality 口袋」→ 1.75s 琥珀图形塔「第二击戏剧张力」。
2. **铰链弱化**：record 折叠段 uBezel ×0.35 → vision：折缝红光消失，仅剩物理银框。
   （踩坑：driveRecord 里凭记忆写了不存在的 foldActive → 每帧 ReferenceError 卡死 recordDone；补定义后修复。教训=调试戒条实证。）
3. **母版图形化**：确定性过滤器（禁 AI 再生）→ 新文件 `1-1 Tokyo_Tower_RedBlack_Graphic_2670x1878.png`，
   原 RedBlack_Final 不动。天空两段平涂红渐变（180,1,1)→(245,77,1)、城市近纯黑、窗灯约减半、塔区原样保护。
   捕获管线 e2e_plate.py 支持 argv[3] 换 B 母图。
4. **hold 不再纯静止**：激活窗口移入 hold 头部。

附加：**16:9 open 水平居中** panX 0→-167，实测设备质心偏移 **+0.00%**（原 -11.67%）。

## 验证

- qc_capture.py V6 门禁（onset/冻结/全红/居中）PASS；塔叙事改 vision 验收（boost 污染像素指标——记录：暖色增益使蓝通道指标失效，勿再调代理指标，用眼睛）。
- 0 console errors；preview 零回归（全部 record/cap 路径限定）。

## 遗留

- 9:16/1:1 的居中未拍板调整（用户只点了 16:9）；如需同待遇，各自实测 panX。
- 图形化母图若用户否决，换回 argv[3] 原文件即可。
