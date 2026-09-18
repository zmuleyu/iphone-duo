# REVIEW — v5.6 边框光亮过渡（G-B）

日期：2026-09-18
分支：work/v5.6-bezel-light → 默认链收尾

## 交付

展开过程中设备物理边框的钛银扫光 + open 完成 pop：

1. **钛银扫光**（uBezel = angle/180 全程跟随）：冷白高光带从铰链出发（75° 实证铰链脊线起光），随展开行经边框中段，160° 到达外侧边缘（实证贴近上外缘细线）。
2. **Open pop**：角度跨越 179.9° 瞬间全框冷白提亮（×3.0），~0.35s 衰减；reduced-motion 下禁用 pop。
3. 实现：USD body/hinge/shell 材质 onBeforeCompile 注入（顶点 project_vertex 处取 object-space x，fragment opaque_fragment 后加性发光，pre-tonemap）；`?bezeldebug=1` bd 假彩色调试层；`__duo.setBezel(sweep, pop)` 确定性探针（pop 带 hold 防衰减干扰验证）。

## 设计决策（重要）

- **折缝红光阶段已删除**：验证发现屏幕着色器的 uLeak 阶段已在屏幕内容上绘制红色泄露（v4_crease 帧左外缘红线的真实来源），物理折缝在 40-54° 自遮挡严重，第二重红光既不可见又重复。红叙事归屏幕、钛叙事归边框——与 Apple 钛合金边框叙事一致。
- 强度定为「克制可读」（UI 红线：动效只解释状态）：160° 外缘细亮线 + pop 一线提亮，不追求霓虹感。

## 验证

- bd 假彩色图：铰链蓝→外缘红，场分布正确（115° 实证）
- 扫光旅程：75° 铰链起光 ✓ / 160° 外缘细线 ✓ / 130° 中段为边缘判定（动态连续，静帧边际）
- pop：手动跨越 179.9° 触发 ✓（hold 探针）；衰减后无残留 ✓（settled 帧）
- 0 console errors；预览路径常规渲染无变化（仅 body 材质追加发光项）

## 调试教训（沉淀）

three.js `customProgramCacheKey` 不变时，onBeforeCompile 源码改动会被旧程序缓存静默吞掉——前两轮调参全部空转。改注入代码必须同步 bump cache key（v56c→d→e 实证）。

## 待用户目检

生产上线后目检扫光/pop 强度；如需更强：`band * 1.6` / `uBezelPop * 3.0` 两个增益 + 同步 bump cache key。
