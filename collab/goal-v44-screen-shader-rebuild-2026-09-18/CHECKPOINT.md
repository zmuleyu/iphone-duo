# CHECKPOINT — v4.4（2026-09-18 00:55 +08:00）

## 当前状态

- 代码：v4.4 已提交并推送 main（5b0fe9e feat + 1e75ec8 cleanup）。
- 部署：Vercel 自动部署中/已完成（以生产 badge v4.4 为准，核验命令见下）。
- 验收：Test A–D 本地 CDP 全过；证据在 `evidence/`。

## 剩余 gate（归用户）

**最终视觉验收**：在 https://iphone-duo-lv3.vercel.app 上传 Reality/RedBlack 实图，
对照 Spline 参考目检 35/50/70% + worldMix 切换。通过后按 GOAL.md Stop Conditions
Freeze panorama 架构。

## 恢复方式

- 继续本 goal：读本目录 GOAL.md / PLAN.md / STATE.json。
- 本地复跑验收：repo 根起 `python -m http.server 8766`，chrome-debug:9222 起好后
  跑 `uv run --no-project --python 3.12 --with websockets python collab/goal-v44-screen-shader-rebuild-2026-09-18/cdp_acceptance.py`。
- 生产核验：`curl https://iphone-duo-lv3.vercel.app/build.json` 应为 4.4；
  `bootstrap.js` 应引用 `main_v44.js`。

## 遗留线索

- 「杀死比尔式空间转场」：另开 goal，需在 Review Pack 写具体参考镜头/手法。
- worldMix timing 精调：Freeze 后再议。
- 35% 时 outer cover 可见性是原版固有行为；如需改动先立设计决策再动。
