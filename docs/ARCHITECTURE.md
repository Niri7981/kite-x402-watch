# 架构与开发

Kite x402 Watch 面向调用 Kite 付费接口的应用和 Agent 开发者。部署前可用它核对卖家当前公布的报价是否符合团队批准的基准。结果仅表示广告条款是否一致，不表示付款能成功或卖家可信。

| 路径 | 职责 |
| --- | --- |
| `kite_watch/cli.py` | 解析命令、发送 GET、读写基准、输出变化和退出码。 |
| `kite_watch/terms.py` | 解码 x402 v2 `PAYMENT-REQUIRED`，验证并规范化字段，按链和代币合约显示 Kite 金额。 |
| `examples/` | 本地可变报价模拟器、已安装 CLI 的演示、GitHub Actions 用法。 |
| `tests/` | 在回环地址使用真实 HTTP 验证 CLI 和报价解析。 |

`snapshot` 从显式 URL 请求一次 402，解析一个 `exact` 报价，仅接受最初的 Kite 主网 `eip155:2366` 或测试网 `eip155:2368`。写出的 JSON 包含 `version`、`url` 和 `terms`；`terms` 中 `network`、`asset`、`amount` 和 `payTo` 均为字符串。金额使用原子单位，地址规范化为小写。`check` 打开同一 URL，比较四个字段；后续若切到另一条 EVM 网络也能识别为变化。连接、HTTP 状态及解析错误不会被当成“报价一致”。

Kite 的具体集成在 `cli.py` 的初始基准校验与 `terms.py` 的 Kite 链 ID / 代币合约映射。无钱包权限，不读取余额，不发送 `PAYMENT-SIGNATURE`，不调用 facilitator。随仓库提供的模拟器生成 Kite 形状的报价用于本地复现；用真实 Kite 卖家时只取首次 402 挑战，无链上交易。

开发只需 Python 3.10+ 和虚拟环境；源码测试、构建及安装后的验证见[测试与部署](TESTING.md)。
