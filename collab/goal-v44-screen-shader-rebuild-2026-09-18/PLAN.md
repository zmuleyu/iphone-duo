# PLAN — v4.4 Original Screen Shader Rebuild

单 writer：本 Hermes session。步骤按序执行，每步验证后推进。

1. **控制面**：本目录 GOAL/PLAN/STATE。
2. **实现 `main_v44.js`**：以 `main_v41d4.js` 为骨架保留 renderer/scene/背景控制/
   framing 3.7.2/播放/UI 接线/USD 加载/fold geometry/uv 烘焙（兼容 motionblur381 的
   `isMovingShell` 与 `#angle` 耦合）；纹理与 shader 层按原版重建：
   - 删双 canvas 对 → 每世界单 1600×1125 canvas
   - 删 coverFx/coverOpacity/isOuter uniforms 与 outer transparent hack
   - 注入原版 screenShader 结构 + `transitionTarget`/`worldMix`，
     `map_fragment` → `diffuseColor.rgb *= screenColor();`
   - custom 模式两屏统一 `frame=innerUIFrame`、`gradient=(.5, 0|1)`、`pixel=1/1600,1/1125`
   - outer cover：原版 `color=0 @ angle>=180`
   - `window.__duo = { setAngle, setWorldMix, state }` debug 钩子
3. **切换加载链**：`bootstrap.js` 只加载 `motionblur381.js` + `main_v44.js`；
   `BUILD_ID='4.4'`；`build.json` 升 4.4。
4. **本地 CDP 验收**（chrome-debug:9222 + localhost:8766）：
   - Test A：生成 1600×1125 校准图（100px 网格+X 数字+过 hinge 红线+右侧单一大圆），
     Reality/RedBlack 同图，35/50/70% 截图
   - Test B/C：包内 `evidence/source_artwork/Reality.png` + `RedBlack.png`，35/50/70% 截图
   - Test D：固定角度，`__duo.setWorldMix(0/0.5/1)` 截图
   - 截图 vision 自检两档
5. **死模块清理**（独立 commit）：停止加载并删除 `main_v41d4.js`、`physicaldisplay431.js`、
   `unifiedpanorama43.js`、`geometrytiming42.js`、`physicalcross41c.js`、`worldtransition41d*.js`、
   `cinematicdof41b*.js`、`defocus41.js`、`motionblur38.js`、`framing373.js`、旧 `main.js`
   （删除前确认无引用）。
6. **push main → Vercel 核验**：生产拉取确认 badge v4.4 + `build.json` + bootstrap 引用
   `main_v44.js`。
7. **交接**：REVIEW.md + CHECKPOINT.md；最终视觉验收归用户（上传实机截图/录屏确认后 Freeze）。
