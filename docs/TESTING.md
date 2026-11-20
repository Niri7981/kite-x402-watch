# 测试与部署

需要 Python 3.10+，在仓库根目录运行：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m unittest discover -s tests -v
WHEEL_DIR=$(mktemp -d)
python -m pip wheel --no-deps . -w "$WHEEL_DIR"
python -m pip install --force-reinstall "$WHEEL_DIR"/*.whl
python examples/demo.py
```

源码测试覆盖字段变化、基准不覆盖、HTTP 503、断开连接、响应超时、无效或多选报价，以及主网和测试网金额显示。演示在临时目录运行已安装的命令，检查退出码 `0`、`1` 和 `2`，并验证原基准保持不变。项目 CI 在 Python 3.10 和 3.12 上运行同样的源码测试、wheel 构建和安装演示。测试使用本地模拟，没有真实付款。

部署时将 wheel 安装到 CI 或应用的 Python 环境，提供已审核的基准文件。CLI 本身不读取 `.env`；如果你的启动脚本用环境变量传参，可以参考 [`.env.example`](../.env.example)：

```sh
. ./.env.example
kite-watch check --baseline "$KITE_WATCH_BASELINE" --timeout "$KITE_WATCH_TIMEOUT" --json
```

| 现象 | 排查方式 |
| --- | --- |
| HTTP 200 | 确认用的是需要付款的 GET 路径。 |
| HTTP 3xx | 核对最终 URL 后重新创建并审核基准。 |
| HTTP 503 / 连接失败 | 检查卖家服务、DNS、端口及 CI 的网络访问。 |
| `endpoint request timed out` | 检查卖家响应时间；确认正常但慢时再调整 `--timeout`。 |
| 缺少报价头或格式不支持 | 确认卖家提供一个 x402 v2 `exact` EVM 报价，并通过 `PAYMENT-REQUIRED` 返回。 |
| `changed` | 核对变化字段与卖家公告；批准后才更新基准。 |
