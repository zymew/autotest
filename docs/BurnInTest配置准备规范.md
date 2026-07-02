# BurnInTest 配置准备规范

## 目标

BurnInTest 在第一阶段只承担老化压测职责，不承担机型识别和规则判断职责。机型选择由 Agent 完成，BurnInTest 只负责执行对应 `.bitcfg`。

## 版本建议

- 使用 BurnInTest 便携版
- 每个目标机型至少准备一个 `.bitcfg`
- 不建议第一阶段依赖运行时动态修改 `.bitcfg`

## 每机型必须确认的内容

- 配置文件名称
- 对应 `model_code`
- 对应老化时长：`24h / 36h / 48h`
- 串口数量与端口名
- 波特率
- 是否存在额外 GPU/网卡驱动要求

## GUI 配置要求

### 测试项

- CPU：100%
- RAM：100%
- Video Playback：100%
- GPGPU：100%
- 2D Graphics：100%
- 3D Graphics：100%
- Network：100%
- Com Port(s)：加入全部目标串口
- Disk：关闭
- Sound：关闭
- USB：关闭

### 串口配置

- 默认只测 `COM1` 的旧配置不可接受
- 必须逐个把该机型所有目标串口加入
- 每个串口的通信模式和波特率要与机型规格一致
- 需要在机型准备表里同步记录这些串口

## 命名建议

```text
bit_<model_code>_<duration>.bitcfg
```

例如：

```text
bit_EC_A_1440.bitcfg
bit_EC_A_2160.bitcfg
bit_EC_B_2880.bitcfg
```

## 与 Agent 的对接

- Agent 根据 `model_code` 找到规格库中的 `burnin_profile`
- `burnin_profile` 至少包含：
  - `name`
  - `cfg_file`
  - `duration_minutes`
  - `serial_ports_expected`

## 沙盒阶段验收点

- 规格匹配时，Agent 能正确调用该机型 `.bitcfg`
- 配置中的串口不再只包含 `COM1`
- 老化时长与机型策略一致
- 便携版在 WinPE 中可正常启动
