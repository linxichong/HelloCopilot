# 09. Dask + Prefect 大数据处理

这一章用于学习把 Prefect 的编排能力和 Dask 的分布式计算能力组合起来。

## 设计思路

- Prefect 负责 flow、task、重试、参数和日志。
- Dask 负责把大量记录切成 partition 并行处理。
- 本项目默认使用 Dask threaded scheduler，也支持传入远程 Dask scheduler 地址。
- 本地 threaded scheduler 适合在脚本、容器和 CI 环境里运行。
- 示例 flow 会从外部 JSON API 拉取数据，按需要放大数据量，再用 Dask 统计记录数、状态分布和金额总和。

代码入口：

```text
app/dask_dwh_flow.py
```

## 本地运行

先安装依赖：

```bash
pip install -r requirements-dev.txt
```

使用 JSONPlaceholder 做学习数据源：

```bash
export EXTERNAL_SOURCE_API_URL=https://jsonplaceholder.typicode.com/todos

python -m app.dask_dwh_flow
```

放大数据量，模拟更大的输入：

```bash
python - <<'PY'
from app.dask_dwh_flow import dask_prefect_dwh_summary

result = dask_prefect_dwh_summary(
    source_url="https://jsonplaceholder.typicode.com/todos",
    scale_factor=1000,
    npartitions=16,
    local_workers=4,
    threads_per_worker=1,
    memory_limit="1GiB",
)
print(result)
PY
```

`/todos` 原始数据是 200 条，`scale_factor=1000` 会扩展成 200,000 条，适合观察 Dask 分区计算。

## 连接远程 Dask Scheduler

如果已经有 Dask 集群，可以传入 scheduler 地址：

```bash
python - <<'PY'
from app.dask_dwh_flow import dask_prefect_dwh_summary

dask_prefect_dwh_summary(
    source_url="https://jsonplaceholder.typicode.com/todos",
    scale_factor=1000,
    npartitions=64,
    scheduler_address="tcp://dask-scheduler:8786",
)
PY
```

## 什么时候用 Dask

Dask 适合：

- 单机 pandas 处理变慢或内存不够。
- 数据可以按文件、时间、租户、分区键拆分。
- 需要在 Python 生态里并行处理 CSV、Parquet、JSON 或自定义对象。

不适合：

- 数据很小，普通 Python 或 SQL 就能很快完成。
- 强事务写入场景。
- 需要复杂 SQL 优化器和超大规模交互式分析，这类通常更适合 Spark、Trino 或 ClickHouse。
