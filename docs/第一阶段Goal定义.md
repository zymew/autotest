# 第一阶段 Goal 定义

## 目标

第一阶段目标不是完成全部产线自动化测试，而是验证沙盒主链路能够稳定跑通：

`通电 -> PXE/iPXE 自动引导 -> WinPE 自动启动 Agent -> 读取 CPU/内存/硬盘信息并按机型规格比对 -> 通过则启动 BurnInTest 24-48 小时老化 -> 结果 JSON 回传控制机`

## 本阶段必须完成

- 控制机提供 `dnsmasq + nginx + 规格库下载 + 结果接收`
- DUT 通电后零人工干预进入 WinPE
- WinPE 启动后自动运行 Python Agent
- Agent 能读取硬件身份字段并归一成 `model_code`
- Agent 能从控制机拉取规格库
- Agent 能输出 CPU、内存、硬盘的实际信息与基础健康状态
- Agent 能按机型规格规则给出匹配/不匹配结论
- 规格不匹配时阻断 BurnInTest 并整体判 `FAIL`
- 规格匹配时按机型选择 BurnInTest 配置并启动老化
- 最终结果能以 JSON 形式回传到控制机

## 本阶段刻意不做

- 不接 MES、数据库、MQTT、Grafana
- 不完成全部接口功能脚本
- 不要求运行时动态生成 BurnInTest 配置
- 不要求 Agent 自动改写 `.bitcfg`
- 不做页面展示

## 验收标准

- 两台 DUT 都能完成 `PXE -> iPXE -> WinPE -> Agent 启动`
- 至少一台 DUT 因规格匹配而成功进入 BurnInTest
- 至少一次人为制造规格不匹配，并被 Agent 正确阻断
- 控制机成功收到每台 DUT 的汇总结果 JSON
- 结果 JSON 至少包含：
  - `sn`
  - `model_code`
  - `hardware_identity`
  - `hardware_check_result`
  - `burnin_started`
  - `burnin_profile`
  - `burnin_result`
  - `overall_result`
  - `failure_reason`
  - `start_time`
  - `end_time`
