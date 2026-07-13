# 第一阶段超细化边做边操作清单 Day 1

这份清单只覆盖最关键、最适合今天直接动手的部分：

1. 把控制机网络和服务搭起来
2. 把项目控制机服务跑起来
3. 验证规格接口能访问

做完这份，你就完成了第一天最重要的基础工作。

---

## A. 接线检查

`在哪台机器`

- 交换机
- Ubuntu 控制机
- 2 台 DUT

`用什么工具`

- 网线

`通过的方法/步骤`

1. 控制机关机状态下，确认网线从控制机接到交换机 `Port 1`
2. 确认 DUT-1 接 `Port 2`
3. 确认 DUT-2 接 `Port 3`
4. 交换机通电
5. 控制机开机
6. 暂时先不要给 DUT 通电

`实现什么结果`

- 控制机已经接入测试交换机

打勾：

- [ ] 控制机接在 Port 1
- [ ] DUT-1 接在 Port 2
- [ ] DUT-2 接在 Port 3
- [ ] DUT 还未通电

---

## B. 找到控制机网口名

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- 终端

`通过的方法/步骤`

1. 打开终端
2. 输入：

```bash
ip addr
```

3. 找到状态为 `UP` 或插线后出现链路的网口
4. 记下名字，例如：
   - `enp1s0`
   - `eth0`

`实现什么结果`

- 知道配置静态 IP 时要写哪个网口名

打勾：

- [ ] 已执行 `ip addr`
- [ ] 已记下控制机网口名：`__________`

---

## C. 给控制机配置静态 IP

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- 终端
- `nano`

`通过的方法/步骤`

1. 查看 netplan 文件：

```bash
ls /etc/netplan
```

2. 记下文件名，例如 `01-network-manager-all.yaml`
3. 备份原文件：

```bash
sudo cp /etc/netplan/你的文件名.yaml /etc/netplan/你的文件名.yaml.bak
```

4. 编辑原文件：

```bash
sudo nano /etc/netplan/你的文件名.yaml
```

5. 改成下面结构，把网口名换成你自己的：

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp1s0:
      dhcp4: no
      addresses:
        - 192.168.10.1/24
```

6. 保存退出
7. 应用配置：

```bash
sudo netplan apply
```

8. 验证：

```bash
ip addr
```

`实现什么结果`

- 控制机测试网口固定为 `192.168.10.1`

打勾：

- [ ] 已备份原 netplan
- [ ] 已写入静态 IP
- [ ] `ip addr` 中能看到 `192.168.10.1`

---

## D. 安装 dnsmasq、nginx、python3

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- 终端

`通过的方法/步骤`

1. 执行：

```bash
sudo apt update
sudo apt install dnsmasq nginx python3 -y
```

2. 创建目录：

```bash
sudo mkdir -p /srv/tftp
sudo mkdir -p /srv/http
sudo mkdir -p /opt/factory-sandbox
```

3. 验证目录：

```bash
ls -ld /srv/tftp /srv/http /opt/factory-sandbox
```

`实现什么结果`

- 安装完成，目录准备完成

打勾：

- [ ] `dnsmasq` 已安装
- [ ] `nginx` 已安装
- [ ] `python3` 已安装
- [ ] `/srv/tftp` 已创建
- [ ] `/srv/http` 已创建
- [ ] `/opt/factory-sandbox` 已创建

---

## E. 配置 dnsmasq

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- `nano`
- `systemctl`

`通过的方法/步骤`

1. 备份配置：

```bash
sudo cp /etc/dnsmasq.conf /etc/dnsmasq.conf.bak
```

2. 编辑：

```bash
sudo nano /etc/dnsmasq.conf
```

3. 写入以下内容，把 `enp1s0` 换成你的网口名：

```ini
interface=enp1s0
bind-interfaces

dhcp-range=192.168.10.100,192.168.10.200,10m
dhcp-option=3
dhcp-option=6

dhcp-boot=ipxe.efi
enable-tftp
tftp-root=/srv/tftp
```

4. 保存后重启：

```bash
sudo systemctl restart dnsmasq
```

5. 检查状态：

```bash
sudo systemctl status dnsmasq
```

`实现什么结果`

- 控制机已具备 PXE 地址分配能力

打勾：

- [ ] 已备份 dnsmasq 配置
- [ ] 已写入测试配置
- [ ] `dnsmasq` 状态为 `active (running)`

---

## F. 配置 nginx

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- `nano`
- `nginx`

`通过的方法/步骤`

1. 创建配置：

```bash
sudo nano /etc/nginx/sites-available/pxe
```

2. 写入：

```nginx
server {
    listen 192.168.10.1:80;
    root /srv/http;

    add_header Accept-Ranges bytes;

    location /boot.wim {
        sendfile on;
        tcp_nopush on;
    }
}
```

3. 启用：

```bash
sudo ln -s /etc/nginx/sites-available/pxe /etc/nginx/sites-enabled/pxe
```

4. 如果默认站点存在，删掉：

```bash
sudo rm /etc/nginx/sites-enabled/default
```

5. 检查并重启：

```bash
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl status nginx
```

6. 验证：

```bash
curl http://192.168.10.1/
```

`实现什么结果`

- 控制机 HTTP 服务可用

打勾：

- [ ] 已创建 `pxe` 配置
- [ ] `nginx -t` 通过
- [ ] `nginx` 状态为 `active (running)`

---

## G. 将项目里的 controller 目录拷到控制机

`在哪台机器`

- Windows 开发机
- Ubuntu 控制机

`用什么工具`

- 文件管理器
- U 盘或局域网传输

`通过的方法/步骤`

1. 找到本地项目里的 `controller` 目录
2. 复制到 Ubuntu 控制机
3. 放到：

```text
/opt/factory-sandbox/controller
```

4. 在 Ubuntu 终端执行：

```bash
find /opt/factory-sandbox/controller -maxdepth 3 -type f
```

`实现什么结果`

- 控制机具备规格库与结果接收服务代码

打勾：

- [ ] `controller` 已复制到 Ubuntu
- [ ] 能看到 `server/app.py`
- [ ] 能看到 `specs/model_specs.json`

---

## H. 启动项目控制机服务

`在哪台机器`

- Ubuntu 控制机

`用什么工具`

- 终端

`通过的方法/步骤`

1. 进入目录：

```bash
cd /opt/factory-sandbox/controller/server
```

2. 启动服务：

```bash
python3 app.py --host 0.0.0.0 --port 8080
```

3. 不要关闭这个终端
4. 新开另一个终端，执行：

```bash
curl http://192.168.10.1:8080/healthz
```

5. 再执行：

```bash
curl http://192.168.10.1:8080/api/specs/model_specs
```

`实现什么结果`

- 控制机轻量服务已正常运行

打勾：

- [ ] 服务已启动
- [ ] `/healthz` 可访问
- [ ] `/api/specs/model_specs` 可访问

---

## I. 今日结束前必须确认

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

2. 三项都正常后，记录“Day 1 完成”

`实现什么结果`

- 控制机基础环境完成，下一步就可以做 WinPE 和 PXE 文件准备
- 但此时还没有实际准备 `ipxe.efi`、`wimboot`、`boot.wim`

打勾：

- [ ] `dnsmasq` 正常
- [ ] `nginx` 正常
- [ ] `app.py` 正常
- [ ] Day 1 完成
