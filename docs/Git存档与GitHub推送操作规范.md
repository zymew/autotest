# Git 存档与 GitHub 推送操作规范

这份文档用于把项目关键节点留档，并推送到你的 GitHub。

当前仓库状态说明：

- 当前分支：`master`
- 当前还没有配置 GitHub 远端

所以第一步不是直接 `push`，而是先把 GitHub 仓库连上。

---

## 1. 什么时候做一次 Git 存档

建议你每到一个关键节点就提交一次，不要等所有东西做完再一起提交。

第一阶段建议至少做这些里程碑提交：

1. `计划定版`
2. `控制机服务骨架完成`
3. `实操文档与超细化清单完成`
4. `控制机网络和 dnsmasq/nginx 配置完成`
5. `WinPE 基础镜像制作完成`
6. `Agent 注入 WinPE 完成`
7. `iPXE + wimboot + boot.wim 部署完成`
8. `单 DUT 跑通`
9. `规格不匹配阻断验证完成`
10. `双 DUT 跑通`
11. `BurnInTest 短时验证完成`
12. `BurnInTest 24-48 小时验证完成`

---

## 2. 提交信息怎么写

建议统一格式：

```text
phase1: <本次关键节点说明>
```

例如：

```text
phase1: finalize sandbox validation plan
phase1: add controller http service and templates
phase1: add operator runbook and day1 checklist
phase1: complete controller network and pxe service setup
phase1: build first winpe image with agent
phase1: validate single dut boot to winpe
```

---

## 3. 第一次连接 GitHub 远端

`在哪台机器`

- 当前这台项目仓库所在机器

`用什么工具`

- Git
- GitHub 仓库地址

`通过的方法/步骤`

1. 先去 GitHub 创建一个空仓库
2. 复制仓库地址，形式类似：

```bash
https://github.com/你的用户名/仓库名.git
```

3. 在项目目录执行：

```bash
git remote add origin https://github.com/你的用户名/仓库名.git
```

4. 验证：

```bash
git remote -v
```

`实现什么结果`

- 当前本地仓库已经关联到 GitHub

---

## 4. 每个关键节点如何提交

`在哪台机器`

- 当前项目仓库所在机器

`用什么工具`

- Git

`通过的方法/步骤`

1. 查看变更：

```bash
git status
```

2. 查看本次改动摘要：

```bash
git diff --stat
```

3. 暂存本次需要留档的文件：

```bash
git add docs controller winpe
```

如果只提交部分内容，就把路径改成更小范围。

4. 提交：

```bash
git commit -m "phase1: add operator runbook and day1 checklist"
```

5. 查看最近提交：

```bash
git log --oneline -n 5
```

`实现什么结果`

- 这个关键节点已经在本地 Git 中留档

---

## 5. 如何推送到 GitHub

`在哪台机器`

- 当前项目仓库所在机器

`用什么工具`

- Git

`通过的方法/步骤`

1. 第一次推送：

```bash
git push -u origin master
```

2. 后续推送：

```bash
git push
```

`实现什么结果`

- 关键节点已上传到 GitHub

---

## 6. 推荐分支策略

如果你想更稳一点，建议这样用：

- `master`：只放你确认稳定的节点
- `codex/phase1-setup`
- `codex/phase1-winpe`
- `codex/phase1-validation`

创建分支示例：

```bash
git checkout -b codex/phase1-setup
```

推送新分支：

```bash
git push -u origin codex/phase1-setup
```

---

## 7. 你当前这次最适合立刻提交的节点

你现在可以先提交这一次，因为我们已经完成了：

- 第一阶段 goal 文档
- 新版实施操作指南
- 控制机服务骨架
- WinPE Agent 骨架
- 今天新增的总清单、超细化清单、Git 规范

建议提交信息：

```bash
git add docs controller winpe
git commit -m "phase1: add sandbox docs runbooks and skeleton services"
```

如果你已经配置好了 GitHub 远端，再执行：

```bash
git push -u origin master
```

---

## 8. 每次实操后的最小动作

以后你每做完一个关键节点，固定做下面 4 条：

```bash
git status
git add <本次相关文件或目录>
git commit -m "phase1: <本次关键节点>"
git push
```

这样你即使中途改坏了，也能快速回到上一个稳定节点。
