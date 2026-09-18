# AI 动效底板使用文档（G-D 交付）

日期：2026-09-18
底板（交付目录 `C:\Users\Admin\Downloads\duo\交付\`）：

| 文件 | 规格 | 说明 |
|---|---|---|
| duo_ai_plate_9x16_1080x1920_openhold2.5s.mp4 | 1080×1920 · 60fps · ~3.9s | 主用（竖屏平台） |
| duo_ai_plate_16x9_1080p_openhold2.5s.mp4 | 1920×1080 · 60fps · ~3.5s | 备用（横屏） |

结构：0-1.33s 折叠（闭合→180°展开，含 v5.6 钛银扫光+pop）→ 1.33s 起 open hold ~2.2-2.5s 静态 RedBlack。**AI 动效只动 hold 段的红天区域。**

## 推荐工具（任选其一，属外部账号卡点）

- **Kling 2.x（可灵）**：局部重绘/蒙版编辑，中文 prompt 友好，国内可直接用
- **Runway Gen-3/4**：inpainting mask + motion brush
- **Hailuo（海螺）**：图生视频，取 hold 段首帧起做

## 飞鸟方案（首选实验）

- **作用段**：hold 段（第 ~80 帧之后），取 2-3s
- **蒙版**：仅红色天空区域（设备屏幕内、塔尖以上的纯红区），**严禁覆盖塔身/设备边框**——AI 会涂抹硬边
- **prompt（EN）**：`A distant flock of small black silhouette birds flies slowly from left to right across the solid red sky, high above the city skyline, subtle and cinematic, poster style, flat illustration, no photorealism`
- **prompt（中）**：`远处一小群黑色剪影飞鸟，从红天左侧缓慢飞向右侧，高于城市天际线，平面插画风格，克制、电影感`
- **参数**：低运动强度（0.2-0.3）；2-3s；保持背景静止（camera motion: none）

## 塔身方案（备选，谨慎）

- 不推荐 AI 直接动塔（硬边涂抹风险）。若要塔灯闪烁/薄雾：mask 限塔周围 10% 天空过渡带，prompt `subtle warm light shimmer on tower lights, very low intensity`；不满意回退底板。
- 塔内光效更稳的路线是 App 内做（窗灯逐层点亮序列 shader），需要时开 goal。

## 回贴流程

1. AI 产出与底板同画幅同帧率片段（不一致先 ffmpeg 归一）
2. 用 ffmpeg overlay/替换 hold 段：`ffmpeg -i plate.mp4 -i ai_clip.mp4 -filter_complex "[0:v]trim=0:1.33[a];[a][1:v]concat=n=2:v=1" ` 或在 opencut 里拖放
3. 导出 H.264 CRF16 + `noise=alls=2:allf=t` 保持颗粒一致

## 回退

任何 AI 结果不满意：底板本身就是可交付成品（hold 段静态），无损失。
