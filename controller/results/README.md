# 结果归档目录

第一阶段产线化骨架中，控制机结果目录不再只存一个最终结果文件，而是同时保存任务摘要、事件流和最终结论。

```text
results/
├── tasks/
│   └── <task_id>.json
└── archive/
    └── YYYY-MM-DD/
        └── <sn>/
            └── <task_id>/
                ├── task.json
                ├── lifecycle.jsonl
                ├── telemetry.jsonl
                ├── event.jsonl
                ├── result.jsonl
                └── final_result_<sn>.json   # 仅兼容旧流程时生成
```

说明：

- `tasks/` 保存当前任务的最新摘要，便于看板快速查询
- `archive/` 保存按 `SN + task_id` 的完整电子档案
- `telemetry.jsonl` 预留给 MQTT/Grafana 链路的过程遥测落盘与追溯
