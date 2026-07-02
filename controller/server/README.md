# 控制机轻量服务

这个目录提供第一阶段沙盒验证所需的最小控制机服务：

- 提供规格库下载接口
- 接收 DUT 回传的结果 JSON
- 按日期 / 机型 / SN 自动归档

## 文件约定

- `../specs/model_specs.json`
- `../specs/model_identity_rules.json`
- `../results/`

你可以先把模板文件复制为正式文件：

```text
controller/specs/model_specs.template.json         -> controller/specs/model_specs.json
controller/specs/model_identity_rules.template.json -> controller/specs/model_identity_rules.json
```

## 启动方式

```bash
python app.py --host 0.0.0.0 --port 8080
```

## 接口

- `GET /healthz`
- `GET /api/specs/model_specs`
- `GET /api/specs/model_identity_rules`
- `POST /api/results`

## POST /api/results 输入

请求体为单个 DUT 的汇总结果 JSON。服务会按下面格式归档：

```text
controller/results/YYYY-MM-DD/<model_code>/<sn>/final_result_<sn>.json
```
