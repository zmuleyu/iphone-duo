# GOAL — T3 母带捕获管线（v5.4）

日期：2026-09-18
前置：v5.3 Dock Density 生产在线；T2 剪辑 spec 已交付（collab/goal-lv3-transition-2026-09-18/T2_EDITING_SPEC.md）
拍板：鸟线弃用（rd 分支归档不晋升）；「开始做 T2 以后的任务」→ T3 = 素材捕获 + QC + 交付
分支：work/v5.4-capture（基 main v5.3）

## 范围

1. **页内确定性捕获器**（`?cap=1` 门控，常态零行为变化）：
   - record 启动时 `canvas.captureStream(recordFps)` + MediaRecorder（VP9/webm，20Mbps）
   - `recordDone` 自动停止并按 `duo_v{build}_{format}_{fps}fps_{preset}.webm` 命名下载
   - `documentElement.dataset.captureDone` 供自动化轮询
2. **三画幅母带捕获**（本地 1440×900，Fast Viral 60fps；各 format 单独录）：
   16:9 / 9:16 / 1:1 各一条 webm 母带（safe frame 构图前置，不后期裁比例——裁切只裁到 safe frame 矩形）
3. **QC**：Export Acceptance 自动项全绿 + 抽帧核验（closed/open 端点角度、折叠段连续、无色带）
4. **交付**：webm +（有 ffmpeg 时）按 spec §4 裁切/缩放到交付分辨率 mp4，落 `Downloads/duo/交付/` + 清单

## 验收

- 三条母带：逐帧时长 = 预设总时长（Fast Viral 1.85s ±1 帧），端点角度 0/180 正确
- Export Acceptance 自动 QC 全绿；抽帧 vision 自检通过
- 生产页面无 `?cap=1` 时行为零变化（badge/build.json 不变更语义）

## 不做

- 不配音乐、不做剪辑拼接（spec 约定音乐后期叠加，属人工/NLE）
- 不改折叠/着色器/操作区任何既有行为
- 不重开鸟线
