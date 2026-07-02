# 结果归档目录

控制机接收到 DUT 的结果 JSON 后，会按下面路径写入：

```text
results/YYYY-MM-DD/<model_code>/<sn>/final_result_<sn>.json
```

这个目录不需要手动维护，服务会自动创建子目录。
