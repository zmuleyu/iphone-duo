# GOAL — V6.4 外壳保真（P1）+ 出片（P2）

日期：2026-09-19
拍板：用户确认「按建议先 P1+P2 出片」（对照官方图/onmyduo 录屏/上游仓）
分支：work/v6.4-shell-fidelity

## 侦察结论

- USDZ 模型自带两颗右侧边按键（x 4.64–4.72, y +1.6 / −2.62，各 ~1.7–1.9 长）——官方 "controls moved to the side" 实证；此前不可见 = 外探量亚像素 + 过曝洗白。
- 场景光照过曝（RoomEnvironment 1.35 + Hemi 1.8 + key 2.6 + rim 2.6）→ 星光白边框在白底被「吃掉」。

## 变更（cap 路径限定）

- 按键按 bbox 签名识别后 position.x += 0.12（record 出片可读；预览不动）
- 框材暖钛化（亮中性色族 ×0.935/0.895/0.82）+ scene.environmentIntensity 1.35→1.0（去爆白）
- debug：`__duo._scene/_phone` 暴露（探针用，无行为影响）

## 验证

- vision 三轮迭代定稿：边框暖钛可读、上键清晰、下键可辨、白底分离、Apple 产品页美学通过
- QC PASS（无冻结、居中 -0.11%）；母版=原始 RedBlack_Final 不动；叙事/波前不变

## 交付

duo_v6.4_16x9_1080p_final.mp4（唯一画幅）
