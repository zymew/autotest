# 第一阶段超细化边做边操作清单 Day 2

> 本文件是 Day2 存档版。
>
> Day2 的目标不是完成全部产线测试，而是打通：
>
> DUT -> PXE -> iPXE -> WinPE -> Python Agent -> 控制机 -> 结果 JSON
>
> 截至本次存档，这条主链已经在 1 台 DUT 上跑通。Agent 已运行并生成结果，但 overall_result 为 FAIL。Dashboard 和 Trace 的端到端展示验证，以及测试项失败原因分析，留到后续阶段。

---

## A. 明确 Day2 目标

在哪台机器

- Windows 开发机

通过的方法/步骤

1. 只关注一条主链：
   - DUT 能从 PXE 启动
   - DUT 能进入 WinPE
   - WinPE 能自动启动 Agent
   - Agent 能联系控制机
   - 控制机能收到结果
2. 本日不要求完成：
   - BurnInTest 长时间老化
   - 第二台 DUT
   - 多机并行
   - MQTT/Grafana
   - USB、显示口、IO 自动化

实现什么结果

- Day2 的范围不会和完整产线目标混在一起。

打勾：

- [x] 已明确 Day2 只做主链联调

---

## B. 确认控制机基础服务

在哪台机器

- Ubuntu 控制机

现场固定参数

- 测试网口：eno1
- 控制机 IP：192.168.10.1/24
- DHCP 地址池：192.168.10.100 到 192.168.10.200
- Controller：前台运行的 python3 app.py
- dnsmasq、nginx：systemd 服务

通过的方法/步骤

1. 查看网口：

    ip -br link

2. 如果网口状态是 DOWN，先拉起：

    sudo ip link set eno1 up

3. 检查 dnsmasq 和 nginx：

    sudo systemctl status dnsmasq --no-pager
    sudo systemctl status nginx --no-pager

4. Controller 进入目录并前台启动：

    cd /opt/factory-sandbox/controller/server
    python3 app.py --host 0.0.0.0 --port 8080

5. 不要关闭 Controller 所在终端。另开终端验证：

    curl http://192.168.10.1:8080/healthz
    curl http://192.168.10.1:8080/api/specs/model_specs

实现什么结果

- dnsmasq、nginx 正常。
- healthz 能返回 200。
- Controller 前台窗口保持运行。

打勾：

- [x] dnsmasq 正常
- [x] nginx 正常
- [x] Controller 前台启动
- [x] healthz 正常

---

## C. 同步新版 controller

在哪台机器

- Windows 开发机
- Ubuntu 控制机

通过的方法/步骤

1. 将仓库里的 controller 目录复制到 U 盘或可访问位置。
2. 如果目标目录没有权限，先复制到 Ubuntu 用户目录，例如：

    /home/zxcc/Desktop/controller

3. 再在终端提权复制：

    sudo mkdir -p /opt/factory-sandbox
    sudo cp -r ~/Desktop/controller /opt/factory-sandbox/

4. 确认至少存在：

    /opt/factory-sandbox/controller/server/app.py
    /opt/factory-sandbox/controller/server/task_store.py
    /opt/factory-sandbox/controller/specs/model_specs.json

5. Controller 结果目录需要由当前用户写入。如果注册时出现 Permission denied，执行：

    sudo mkdir -p /opt/factory-sandbox/controller/results/archive
    sudo chown -R zxcc:zxcc /opt/factory-sandbox/controller/results

实现什么结果

- 控制机拿到与仓库一致的新版 Controller。

打勾：

- [x] controller 已同步
- [x] Controller 结果目录权限已处理

---

## D. 创建并挂载正式 WinPE

在哪台机器

- Windows 开发机

用什么工具

- Windows ADK
- WinPE Add-on
- Deployment and Imaging Tools Environment 管理员终端
- DISM

通过的方法/步骤

1. 创建工作目录：

    copype amd64 C:\WinPE_amd64

2. 创建挂载目录并挂载 boot.wim：

    mkdir C:\WinPE_amd64\mount
    Dism /Mount-Image /ImageFile:C:\WinPE_amd64\media\sources\boot.wim /Index:1 /MountDir:C:\WinPE_amd64\mount

3. 需要重复制作时，先备份：

    copy /Y C:\WinPE_amd64\media\sources\boot.wim C:\WinPE_amd64\media\sources\boot.wim.bak

实现什么结果

- 得到可编辑的 C:\WinPE_amd64 工作目录。

打勾：

- [x] ADK 和 WinPE Add-on 已安装
- [x] WinPE 工作目录已创建
- [x] boot.wim 已挂载

---

## E. 把新版脚本复制进 WinPE

通过的方法/步骤

1. 创建目标目录：

    mkdir C:\WinPE_amd64\mount\scripts

2. 复制仓库脚本：

    xcopy /E /I /Y C:\Users\19306\Documents\自动测试\winpe\scripts C:\WinPE_amd64\mount\scripts

3. 至少确认这些文件存在：

    agent.py
    hardware_probe.py
    model_identity_rules.json
    run_bit.py
    spec_client.py
    startnet.cmd

4. 真正的 WinPE 启动入口不是 scripts 目录里的副本，而是：

    C:\WinPE_amd64\mount\Windows\System32\startnet.cmd

5. 启动入口最终调用：

    X:\python\python.exe X:\scripts\agent.py

实现什么结果

- WinPE 中的脚本与仓库版本一致。
- WinPE 启动后会自动执行 Agent。

打勾：

- [x] 脚本已复制
- [x] 真正的 Windows\System32\startnet.cmd 已修改
- [x] startnet.cmd 会调用 agent.py

---

## F. 注入 Python 和硬件探测依赖

通过的方法/步骤

1. 将官方 Python 3.11 amd64 embeddable package 解压到：

    C:\WinPE_amd64\mount\python

2. 确认至少存在：

    python.exe
    python311.dll
    python311.zip
    python311._pth

3. 编辑 python311._pth，保留：

    python311.zip
    .
    ..\scripts

4. WinPE 基础镜像没有完整 PowerShell/CIM 能力，按依赖顺序加入以下组件，并同时加入对应的 zh-cn 语言包：

    WinPE-WMI.cab
    WinPE-NetFX.cab
    WinPE-Scripting.cab
    WinPE-PowerShell.cab

5. hardware_probe.py 已改为调用：

    X:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe

6. 不要再依赖 wmic。WinPE 中找不到 wmic 是已确认的问题。

实现什么结果

- Python 能找到 scripts 下的模块。
- Agent 能用 Get-CimInstance 读取 BIOS、CPU、内存、硬盘、网卡和串口。

打勾：

- [x] Python 已注入
- [x] python311._pth 已补 scripts 路径
- [x] PowerShell/CIM 组件已加入
- [x] wmic 问题已通过 hardware_probe.py 修正

---

## G. 保存 WinPE 镜像

通过的方法/步骤

1. 关闭所有打开 mount 目录的窗口和编辑器。
2. 提交并卸载：

    Dism /Unmount-Image /MountDir:C:\WinPE_amd64\mount /Commit

3. 如果提示目录被占用：
   - 关闭文件管理器和编辑器
   - 重新执行卸载
   - 用 Dism /Get-MountedWimInfo 查看状态
   - 确认没有需要保留的挂载后，再使用 Dism /Cleanup-Wim 清理残留

4. 最终文件为：

    C:\WinPE_amd64\media\sources\boot.wim

实现什么结果

- 得到已经包含脚本、Python 和依赖组件的新版 boot.wim。

打勾：

- [x] WinPE 修改已提交
- [x] boot.wim 已生成并保存

---

## H. 补齐 wimboot 所需启动文件

在哪台机器

- Windows 开发机
- Ubuntu 控制机

通过的方法/步骤

将以下文件放到 Ubuntu 控制机的 /srv/http：

    boot.wim
    bootmgr
    BCD
    boot.sdi
    wimboot

将 ipxe.efi 和 autoexec.ipxe 放到 /srv/tftp：

    ipxe.efi
    autoexec.ipxe

其中 bootmgr、BCD、boot.sdi 不能漏掉。只放 boot.wim 会导致 Windows Boot Manager 报 BCD 缺失。

实现什么结果

- 控制机具备完整的 PXE -> iPXE -> wimboot -> WinPE 文件链。

打勾：

- [x] boot.wim 已放到 /srv/http
- [x] bootmgr 已放到 /srv/http
- [x] BCD 已放到 /srv/http
- [x] boot.sdi 已放到 /srv/http
- [x] wimboot 已放到 /srv/http
- [x] ipxe.efi 已放到 /srv/tftp
- [x] autoexec.ipxe 已放到 /srv/tftp

---

## I. 确认 iPXE 脚本关系

autoexec.ipxe 负责 DHCP 和跳转：

    #!ipxe
    echo AUTOEXEC REACHED
    dhcp
    echo DHCP ADDRESS: DUT_IP
    chain http://192.168.10.1/boot.ipxe

boot.ipxe 负责加载 WinPE：

    #!ipxe
    kernel http://192.168.10.1/wimboot
    initrd http://192.168.10.1/bootmgr bootmgr
    initrd http://192.168.10.1/BCD BCD
    initrd http://192.168.10.1/boot.sdi boot.sdi
    initrd http://192.168.10.1/boot.wim boot.wim
    boot

本次使用官网现成 ipxe.efi 和 wimboot，不依赖 WSL、make 或 gcc。

打勾：

- [x] DHCP 后能拿到 DUT 地址
- [x] TFTP 能发送 ipxe.efi
- [x] iPXE 能执行 autoexec.ipxe
- [x] HTTP 能发送 wimboot 和 WinPE 文件

---

## J. 首轮 DUT 真机联调

通过的方法/步骤

1. 控制机保持 app.py、dnsmasq、nginx 正常运行。
2. DUT 进入 BIOS/Boot Menu。
3. 关闭 Secure Boot，开启 UEFI PXE。
4. 选择 PXE IPv4，不选择 HTTP IPv4。
5. 观察 DUT 是否依次出现：
   - DHCP 地址
   - ipxe.efi 下载
   - iPXE 初始化
   - wimboot/boot.wim 下载
   - WinPE 命令窗口
   - Phase 1 Agent Starting
6. 控制机可观察：

    sudo journalctl -u dnsmasq -f
    sudo tcpdump -i eno1 'port 69 or port 80'

实现什么结果

- DUT 能从 PXE 进入 WinPE，并自动启动 Agent。

打勾：

- [x] DUT 已进入 PXE
- [x] DUT 已进入 WinPE
- [x] Agent 已自动启动
- [x] 控制机观察到 DUT 请求

---

## K. 验证 Agent 和控制机已经“说上话”

通过的方法/步骤

1. 查看 Controller 前台窗口，确认出现 DUT 的 healthz、注册或事件请求。
2. 确认结果目录可以写入。
3. DUT 运行结束后，确认 WinPE 中出现结果 JSON。
4. WinPE 不使用 findstr 时，先执行：

    dir X:\ /s /b

5. 找到文件后直接执行：

    type 完整路径\inventory_check_文件名.json
    type 完整路径\final_result_文件名.json

实现什么结果

- Agent 完成硬件探测、任务注册和结果生成。
- Controller 收到结果并归档。

打勾：

- [x] Agent 已读取硬件身份
- [x] Agent 已注册任务
- [x] Controller 已收到请求
- [x] 结果 JSON 已生成
- [x] 结果已归档

---

## L. Day2 结尾状态

截至 Day2 结束，已实际验证：

    PXE -> iPXE -> wimboot -> WinPE -> Python Agent -> Controller -> 结果 JSON

本次 DUT 的最终结果为：

    overall_result = FAIL

这个 FAIL 属于应用层测试判定，不代表主链失败。

Day2 已完成：

- [x] 控制机基础服务正常
- [x] 新版 Controller 已部署
- [x] WinPE 已制作并保存
- [x] Python 和硬件探测依赖已注入
- [x] PXE 主链文件齐全
- [x] 1 台 DUT 已进入 WinPE
- [x] Agent 已自动运行
- [x] Controller 已收到任务/事件
- [x] 结果 JSON 已生成
- [x] Day2 主链路完成

Day2 结束时尚未完成：

- [ ] 分析 final_result 中具体哪一项导致 FAIL
- [ ] Dashboard 端到端展示验证
- [ ] Trace 端到端追溯验证
- [ ] 真实机型规格和识别规则收敛
- [ ] 真实串口环回治具验证
- [ ] BurnInTest 便携版、许可证和 bitcfg 注入及验证
- [ ] 第二台 DUT 和多机并行验证

这些项目记录为后续工作总览，本文件不展开 Day3 具体动作。

---

## M. Day2 存档结论

Day2 不是“所有测试项都 PASS”，而是“第一台 DUT 已经能从 PXE 启动并把结果送回控制机”。

本次已经达到 Day2 的结束标准，可以进行版本存档和 GitHub 上传。
