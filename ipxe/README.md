# iPXE 文件说明

## 当前复现方式

本项目当前不要求在 Windows 上安装 WSL、make 或 gcc 编译 iPXE。

现场复现时直接从官方地址下载现成的 `ipxe.efi`，放到 Ubuntu 控制机：

```text
/srv/tftp/ipxe.efi
```

再从 iPXE 官方 wimboot 发布页下载 `wimboot`，放到：

```text
/srv/http/wimboot
```

完整的 `autoexec.ipxe`、`boot.ipxe` 和 WinPE 文件关系，以 [Day2 清单](../docs/第一阶段超细化边做边操作清单-Day2.md) 为准。

## build-ipxe.ps1

`build-ipxe.ps1` 是可选的源码编译尝试，不是当前 Day2 复现的必要步骤。它要求本目录下另有 iPXE 源码和可用的 `make` 环境；现场没有使用这条路径。
