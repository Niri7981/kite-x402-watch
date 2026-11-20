# Kite x402 Watch

给调用 Kite 付费 API 的开发者：在部署或启动 Agent 前，通过一次不带付款凭证的 GET，检查卖家公布的付款条件是否偏离你认可的基准。无钱包、无运行时第三方依赖。

## 五分钟上手

需要 Python 3.10+。在本仓库根目录：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
python examples/demo.py
```

演示使用本地模拟卖家与临时基准，调用已安装的 `kite-watch`，验证以下结果：

```text
snapshot exit 0: saved
check    exit 0: unchanged
check    exit 1: changed
         1 -> 2 USDC.e (1000000 -> 2000000 atomic units)
check    exit 2: error
         expected HTTP 402, got HTTP 503
inspect  exit 0: inspected
```

## 监控你的接口

把示例 URL 换成你要监控的 Kite x402 GET 接口：

```sh
mkdir -p watch
kite-watch snapshot https://api.example.com/paid --baseline watch/approved.json
kite-watch inspect --baseline watch/approved.json
kite-watch check --baseline watch/approved.json --timeout 5
```

查看基准中的网络、代币、原子金额和收款地址，确认与**独立可信来源**一致后再用于监控。`snapshot` 记录卖家当时的报价，不能证明卖家身份；已有基准也不会被覆盖。要接受新报价，先保存到不同路径并人工审核，再替换原基准。

想用 GitHub Actions 检查时，把[工作流示例](examples/github-actions/kite-quote-watch.yml)复制到调用方仓库。详见 [CLI 参数、退出码和 CI 接入](docs/USAGE.md)。

## 范围

读取 x402 v2 的 Base64 PAYMENT-REQUIRED 头，仅支持单一 exact EVM 报价。初始网络限 Kite 主网 2366 或测试网 2368；后续切换至其他 EVM 网络也报告变化。按原子单位整数比较，地址忽略大小写；仅对已知链和合约组合显示 USDC.e 或 pieUSD 小数金额。映射依据：[Kite 官方 x402 模板](https://github.com/gokite-ai/kite-x402-services/tree/893a27509648b660bbba626b0da59619a94f04ab/templates)。

当前监控 `network`、`asset`、`amount`、`payTo`。不检查 EIP-712 域、报价有效期、余额、成交价或实际结算；不跟随重定向，不签名或付款。不支持多选报价、鉴权请求、POST 或只在响应正文提供挑战的卖家。演示卖家完全在本地模拟，无链上交易。远程端点应使用 HTTPS。

## 结构、测试与部署

- [架构与开发](docs/ARCHITECTURE.md)：模块、基准格式、数据流和 Kite 集成位置。
- [测试与部署](docs/TESTING.md)：从干净环境构建和安装、检查覆盖范围和排障。
- [贡献说明](CONTRIBUTING.md) · [变更记录](CHANGELOG.md) · [MIT 许可证](LICENSE)
