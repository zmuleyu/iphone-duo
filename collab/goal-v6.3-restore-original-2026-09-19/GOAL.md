# GOAL — V6.3 回归原始母版 + reveal 逐面板接续

日期：2026-09-19
拍板：用户指定 duo_ai_plate open 内容为正确基准（原始 RedBlack_Final 摄影感母版），回到该状态
分支：work/v6.3-restore-original

## 根因

- 图形化母图 v1/v2 过滤过度：碾掉塔自然 halo、塔吊红灯、左侧红招牌、左下暖光带、窗灯密度——背离原始效果。
- reveal v6.2 全局波前：红先铺满斜置左屏读不出因果 + 右缘蓝残留（front 余量不足）。

## 变更

1. **捕获母图回退**：`RedBlack_Final` 原始文件（管线 argv[3] 换回原文件；图形化文件保留但不用于成片）。
2. **reveal 逐面板接续**（record 路径）：左屏窗口 easedFold/0.55、右屏窗口 (easedFold-0.45)/0.55，
   各自从左到右扫过（local front ×1.25 软边 0.25）——左屏展开完成=左屏转变完成，右屏无缝接力，fold 末全覆盖。
   塔口袋保持 + 0.3s 激活不变；boost 关闭、扫光退出成片不变。
3. 外壳：与 plate 基准一致（正面视角无按钮=正确），不动。

## 验收

- 只出 16:9 终片
- QC 门禁（onset/冻结/全红/居中）+ vision：open hold 帧对照 plate（窗灯密度/塔吊/红招牌/塔 halo 回归）
- vision：波前序列帧左屏先变、右屏接力、右缘无蓝残留
