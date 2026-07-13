# 自动测试项目

这是一个“控制机 + PXE/WinPE + DUT Agent”的自动测试沙盒项目。

## 从哪里开始

如果你第一次接触这个项目，请按下面顺序阅读：

1. [第一阶段 Day1 操作清单](docs/第一阶段超细化边做边操作清单-Day1.md)
2. [第一阶段 Day2 操作清单与存档](docs/第一阶段超细化边做边操作清单-Day2.md)
3. [第一阶段实操总清单](docs/第一阶段实操总清单.md)
4. [第一阶段目标定义](docs/第一阶段Goal定义.md)

Day1 和 Day2 清单已经按现场实际情况修订。具体复现以这两份清单和项目代码为准。

## 项目目录

```text
controller/     Ubuntu 控制机服务、规格配置、结果模板
winpe/scripts/  注入 WinPE 的 Agent 和测试模块
ipxe/           iPXE 相关脚本和说明
docs/           中文目标、操作、复现和存档文档
```

## 当前结论

截至 Day2 结束，已经验证：

```text
PXE -> iPXE -> wimboot -> WinPE -> Python Agent -> Controller -> 结果 JSON
```

当前 DUT 的 `overall_result` 为 `FAIL`，说明主链已经跑通，剩余工作是分析具体测试项失败原因，并完成真实机型、串口环回和 BurnInTest 的现场验证。

## 重要现场约定

- 控制机测试网口当前使用 `eno1`。
- 控制机地址为 `192.168.10.1/24`。
- `healthz` 由前台运行的 `python3 app.py` 提供，不是 systemd 服务。
- `dnsmasq` 和 `nginx` 才是 systemd 服务。
- 生产文件 `boot.wim`、`ipxe.efi`、`wimboot` 是现场生成或下载后放置的文件，不直接提交到本仓库。
