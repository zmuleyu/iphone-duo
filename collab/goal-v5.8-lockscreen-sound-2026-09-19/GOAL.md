# GOAL — v5.8 锁屏 chrome 修正 + 音效成片（G-E/G-F）

日期：2026-09-19
拍板：用户确认按助手推荐集执行（锁屏按参考图1布局 / 合成 Kill Bill 风味 sting / 微推镜+片尾板+轻晕影全做）
分支：work/v5.8-lockscreen-sound

## G-E 范围（运行态）

1. 锁屏 chrome 重写：大号细体 9:41 + Wed Apr 1 顶中、右上小 WiFi、右下手电筒/相机双圆钮竖排、home 条
2. 仅画入 redblack（展开态所见）；reality/覆盖屏保持纯壁纸（对齐参考图2）
3. record hold 微推镜 zoom ×1→1.015（仅录制路径）

## G-F 范围（交付管线）

4. 合成 Kill Bill 风味 sting（警笛滑音+拨弦）+ 风声垫底，pop 点对齐混音
5. 三画幅重捕（?cap=1&ui=1 openHold2.5 2x）→ 颗粒+晕影+片尾板+音频终出

## 验收

- [ ] ?ui=1 open 帧对照参考图1布局（vision）
- [ ] 无参基线零变化；closed/cover 无 chrome
- [ ] 0 console errors；生产 badge v5.8
- [ ] 成片三画幅有声交付 + 抽帧终检
