# 第一阶段超细化边做边操作清单 Day 2

这份 Day2 清单已经按新的项目状态重写了。  
它不再要求你今天就把整个产线方案做完，而是只做最有价值的事情：

- 把新版控制机服务部署起来
- 把新版 WinPE 脚本带进去
- 让 1 台 DUT 开始和控制机“说上话”

今天做完以后，最理想的结果是：

1. 控制机能跑新版服务
2. 你能打开 `/dashboard`
3. WinPE 已经带上新版 agent
4. 至少 1 台 DUT 能进 WinPE
5. DUT 开始向控制机注册任务或开始回传事件

---

## A. 确认今天的目标别跑偏

`在哪台机器`

- Windows 开发机

`用什么工具`

- 文档

`通过的方法/步骤`

1. 先看一遍：
   - [docs/第一阶段实操总清单.md](/C:/Users/19306/Documents/自动测试/docs/第一阶段实操总清单.md)
   - [docs/第一阶段产线自动化重构实施说明.md](/C:/Users/19306/Documents/自动测试/docs/第一阶段产线自动化重构实施说明.md)
2. 记住 Day2 只追求一件事：
   - 让 `DUT -> WinPE -> Agent -> 控制机` 主链开始联调
3. 今天先不追：
   - MQTT 真接入
   - Grafana
   - USB 自动化
   - 显示口
   - IO

`实现什么结果`

- 你知道今天不是“做完整产线”，而是“开始真机联调”

打勾：

- [ ] 已重新明确 Day2 目标

---

## B. 检查本地仓库关键文件

`在哪台机器`

- Windows 开发机

`用什么工具`

- 文件管理器
- 文本编辑器

`通过的方法/步骤`

1. 确认这些文件存在：
   - [controller/server/app.py](/C:/Users/19306/Documents/自动测试/controller/server/app.py)
   - [controller/server/task_store.py](/C:/Users/19306/Documents/自动测试/controller/server/task_store.py)
   - [controller/specs/model_specs.json](/C:/Users/19306/Documents/自动测试/controller/specs/model_specs.json)
   - [winpe/scripts/agent.py](/C:/Users/19306/Documents/自动测试/winpe/scripts/agent.py)
   - [winpe/scripts/hardware_probe.py](/C:/Users/19306/Documents/自动测试/winpe/scripts/hardware_probe.py)
   - [winpe/scripts/spec_client.py](/C:/Users/19306/Documents/自动测试/winpe/scripts/spec_client.py)
   - [winpe/scripts/run_bit.py](/C:/Users/19306/Documents/自动测试/winpe/scripts/run_bit.py)
   - [winpe/scripts/startnet.cmd](/C:/Users/19306/Documents/自动测试/winpe/scripts/startnet.cmd)
2. 只需要确认“文件都在”，暂时不深究全部代码细节

`实现什么结果`

- 你知道今天要部署的是哪一套新文件

打勾：

- [ ] 已确认控制机服务文件
- [ ] 已确认 WinPE 脚本文件

---

## C. 确认 Ubuntu 控制机基础服务仍正常

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- 终端

`通过的方法/步骤`

1. 执行：

```bash
sudo systemctl status dnsmasq
sudo systemctl status nginx
curl http://192.168.10.1:8080/healthz
```

2. 确认：
   - `dnsmasq` 是 `active (running)`
   - `nginx` 是 `active (running)`
   - `healthz` 能返回 `ok`

3. 如果 `healthz` 不通，优先确认你是否已经在控制机启动过新版 `app.py`

`实现什么结果`

- 控制机网络/PXE/HTTP 基础环境还在

打勾：

- [ ] `dnsmasq` 正常
- [ ] `nginx` 正常
- [ ] `healthz` 正常

---

## D. 把新版 controller 目录同步到控制机

`在哪台机器`

- Windows 开发机
- Ubuntu 控制机

`用什么工具`

- U 盘或局域网传输
- 文件管理器

`通过的方法/步骤`

1. 从当前仓库复制整个 `controller` 目录
2. 覆盖到 Ubuntu 控制机：

```text
/opt/factory-sandbox/controller
```

3. 到 Ubuntu 控制机终端检查：

```bash
find /opt/factory-sandbox/controller -maxdepth 3 -type f
```

4. 确认至少能看到：
   - `server/app.py`
   - `server/task_store.py`
   - `specs/model_specs.json`

`实现什么结果`

- 控制机拿到最新代码

打勾：

- [ ] 新版 `controller` 已同步到控制机
- [ ] 控制机上能看到 `task_store.py`

---

## E. 启动新版控制机服务

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- 终端

`通过的方法/步骤`

1. 进入目录：

```bash
cd /opt/factory-sandbox/controller/server
```

2. 启动：

```bash
python3 app.py --host 0.0.0.0 --port 8080
```

3. 保持这个终端不要关
4. 新开一个终端验证：

```bash
curl http://192.168.10.1:8080/healthz
curl http://192.168.10.1:8080/api/dashboard/summary
```

5. 如果环境允许，再用浏览器打开：

```text
http://192.168.10.1:8080/dashboard
```

`实现什么结果`

- 控制机新版服务能启动并暴露看板/接口

打勾：

- [ ] 新版 `app.py` 已启动
- [ ] `/healthz` 正常
- [ ] `/api/dashboard/summary` 正常
- [ ] `/dashboard` 可打开

---

## F. 看一眼当前测试计划配置

`在哪台机器`

- Windows 开发机

`用什么工具`

- 文本编辑器

`通过的方法/步骤`

1. 打开：
   - [controller/specs/model_specs.json](/C:/Users/19306/Documents/自动测试/controller/specs/model_specs.json)
2. 重点只看这几块：
   - `defaults`
   - `test_items`
   - `lan_check`
   - `serial_loopback_check`
   - `burnin_profile`
3. 暂时不要求你今天就把所有真实参数改完
4. 今天的目的只是知道：
   - 当前主线测哪些项
   - 哪些项是占位

`实现什么结果`

- 你知道系统今天默认会跑什么测试

打勾：

- [ ] 已看过 `model_specs.json`
- [ ] 已知道 `USB / 显示 / IO` 目前只是占位

---

## G. 确认 WinPE 里要带哪些脚本

`在哪台机器`

- Windows 开发机

`用什么工具`

- 文件管理器

`通过的方法/步骤`

1. 确认 WinPE 里至少要带：
   - `agent.py`
   - `hardware_probe.py`
   - `spec_client.py`
   - `run_bit.py`
   - `startnet.cmd`
2. 如果你已经有现成 WinPE 工作目录，就准备把这些新版文件覆盖进去
3. 如果你还没有现成 WinPE，就先只记住今天需要更新的是 `winpe/scripts/`

`实现什么结果`

- 你知道 WinPE 更新的最小范围

打勾：

- [ ] 已确认 WinPE 需更新的脚本清单

---

## H. 更新 WinPE 里的脚本

`在哪台机器`

- Windows 开发机

`用什么工具`

- 文件管理器
- DISM
- 你当前已有的 WinPE 工作目录

`通过的方法/步骤`

1. 如果你已有挂载好的 WinPE 工作目录：
   - 用新版 `winpe/scripts/` 覆盖进去
2. 如果你还没挂载：
   - 先进入你之前的 WinPE 工作目录
   - 挂载 `boot.wim`
   - 再把新版脚本覆盖到对应 `X:\scripts` 预期目录
3. 确认 `startnet.cmd` 最终会调用新版 `agent.py`

`实现什么结果`

- WinPE 带上新版 agent 骨架

打勾：

- [ ] 已覆盖新版 `agent.py`
- [ ] 已覆盖新版 `hardware_probe.py`
- [ ] 已覆盖新版 `spec_client.py`
- [ ] 已覆盖新版 `run_bit.py`
- [ ] 已确认 `startnet.cmd`

---

## I. 重新生成并放置 `boot.wim`

`在哪台机器`

- Windows 开发机
- Ubuntu 控制机

`用什么工具`

- DISM
- 文件管理器
- 局域网传输或 U 盘

`通过的方法/步骤`

1. 提交 WinPE 改动并生成新的 `boot.wim`
2. 把新的 `boot.wim` 复制到 Ubuntu 控制机：

```text
/srv/http/boot.wim
```

3. 确认控制机文件在位：

```bash
find /srv/http -maxdepth 2 -type f
```

`实现什么结果`

- DUT 启动时拿到的是新版 WinPE

打勾：

- [ ] 已生成新 `boot.wim`
- [ ] 已覆盖控制机上的 `boot.wim`

---

## J. 确认 PXE 主链文件仍齐全

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- 终端

`通过的方法/步骤`

1. 执行：

```bash
find /srv/tftp -maxdepth 2 -type f
find /srv/http -maxdepth 2 -type f
```

2. 重点确认：
   - `/srv/tftp/ipxe.efi`
   - `/srv/http/wimboot`
   - `/srv/http/boot.wim`

`实现什么结果`

- PXE 启动主链文件齐全

打勾：

- [ ] `ipxe.efi` 在位
- [ ] `wimboot` 在位
- [ ] `boot.wim` 在位

---

## K. 用 1 台 DUT 做首轮真机联调

`在哪台机器`

- 1 台 DUT
- Ubuntu 控制机

`用什么工具`

- DUT 屏幕
- 键盘
- 控制机终端

`通过的方法/步骤`

1. 让 DUT 进入 PXE/网络启动
2. 观察是否进入 WinPE
3. 观察 WinPE 是否开始执行 agent
4. 回到控制机查看：

```bash
curl http://192.168.10.1:8080/api/dashboard/summary
```

5. 如果有浏览器，打开：

```text
http://192.168.10.1:8080/dashboard
```

6. 如果能拿到 SN，再查看：

```text
http://192.168.10.1:8080/trace/你的SN
```

`实现什么结果`

- 第一台 DUT 开始进入“任务注册/事件回传”联调

打勾：

- [ ] DUT 已进入 WinPE
- [ ] Agent 已启动
- [ ] 控制机看板能看到任务

---

## L. 如果真机还没完全跑通，优先怎么看问题

`在哪台机器`

- DUT
- Ubuntu 控制机

`用什么工具`

- 屏幕
- 终端

`通过的方法/步骤`

1. 如果 DUT 连 WinPE 都进不去：
   - 先查 PXE 文件
   - 再查 BIOS 启动项
2. 如果 WinPE 进去了但没跑 agent：
   - 先查 `startnet.cmd`
   - 再查脚本是否真正被注入
3. 如果 agent 跑了但控制机没显示任务：
   - 先查 `app.py` 是否在运行
   - 再查 `192.168.10.1:8080` 是否可访问
4. 如果任务注册了但测试失败：
   - 先看 `inventory_check`
   - 再看 `lan_check`
   - 最后看串口

`实现什么结果`

- 你知道排查顺序，不会乱查

打勾：

- [ ] 已明确故障排查顺序

---

## M. Day2 结束前确认

`在哪台机器`

- Ubuntu 控制机
- Windows 开发机

`用什么工具`

- 终端
- 文件管理器

`通过的方法/步骤`

1. 确认控制机服务仍正常：

```bash
curl http://192.168.10.1:8080/healthz
curl http://192.168.10.1:8080/api/dashboard/summary
```

2. 确认新版 `boot.wim` 已放到控制机
3. 确认至少 1 台 DUT 已开始首轮联调
4. 不要求今天必须做到：
   - 串口全通过
   - BurnIn 全通过
   - MQTT/Grafana 完成

`实现什么结果`

- Day2 成功把项目从“只看代码”推进到“开始真机联调”

打勾：

- [ ] 控制机服务正常
- [ ] 新版 WinPE 已就位
- [ ] 第一台 DUT 已开始联调
- [ ] Day2 完成
