# 控制机服务（第一阶段产线化骨架）

这个目录现在不再只是“收一个最终结果 JSON”的轻量服务，而是第一阶段产线自动化的最小控制面：

- 给 DUT/Agent 分配测试任务
- 提供轻量测试配置
- 接收生命周期、事件、遥测、最终结果
- 生成工位看板和按 `SN` 的追溯视图

## 启动方式

```bash
python app.py --host 0.0.0.0 --port 8080
```

## 主要接口

- `GET /healthz`
- `GET /dashboard`
- `GET /trace/<sn>`
- `GET /api/dashboard/summary`
- `GET /api/tasks`
- `GET /api/tasks/<task_id>`
- `GET /api/duts/<sn>`
- `GET /api/specs/model_specs`
- `GET /api/specs/model_identity_rules`
- `POST /api/tasks/register`
- `POST /api/events`
- `POST /api/results`

## 任务注册

`POST /api/tasks/register` 请求体至少包含：

```json
{
  "sn": "SYSTEM-SN-001",
  "station_id": "LINE-A-01",
  "hardware_identity": {
    "bios_serial_number": "SYSTEM-SN-001"
  },
  "capabilities": {
    "inventory_check": true,
    "lan_check": true,
    "serial_loopback_check": true,
    "burnin_check": true
  }
}
```

返回值会包含：

- `task_id`
- `model_code`
- `status`
- `test_plan`
- `archive_dir`

## 事件上报

`POST /api/events` 使用统一消息结构：

```json
{
  "channel": "event",
  "task_id": "123456abcdef",
  "sn": "SYSTEM-SN-001",
  "station_id": "LINE-A-01",
  "model_code": "EC_SAMPLE_A",
  "event_type": "test_finished",
  "test_item": "lan_check",
  "status": "PASS",
  "timestamp": "2026-07-03T11:00:00",
  "payload": {
    "detail": "LAN ok"
  }
}
```

`channel` 目前支持：

- `lifecycle`
- `telemetry`
- `event`
- `result`

## 目录约定

结果会按任务维度归档到：

```text
controller/results/
├── tasks/<task_id>.json
└── archive/YYYY-MM-DD/<sn>/<task_id>/
    ├── task.json
    ├── lifecycle.jsonl
    ├── telemetry.jsonl
    ├── event.jsonl
    └── result.jsonl
```

旧版 `POST /api/results` 仍然保留，用于兼容原来的最终结果上传方式。
