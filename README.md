# Kite x402 Watch

给调用 Kite 付费 API 的开发者：在部署或启动 Agent 前，通过一次不带付款凭证的 GET，检查卖家公布的付款条件是否偏离你认可的基准。无钱包、无运行时第三方依赖。

## 安装与演示

需要 Python 3.10+。在本仓库根目录：

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
cp examples/terms.json /tmp/kite-demo-terms.json
python examples/seller.py /tmp/kite-demo-terms.json
```

在同一目录打开第二个终端：

```sh
. .venv/bin/activate
kite-watch snapshot http://127.0.0.1:8408/quote
cat kite-baseline.json
kite-watch check
```

查看基准中的网络、代币、原子金额和收款地址，确认与**独立可信来源**一致后再用于监控。snapshot 记录端点当前的说法，不验证卖家身份，已有文件不会覆盖。要接受新报价，请用不同的 `--baseline` 路径创建新文件，人工对照后替换。

把 **/tmp/kite-demo-terms.json** 中的 amount 从 "1000" 改成 "10000"，无需重启，再次运行 `kite-watch check`：

```text
changed
amount: 1000 -> 10000
price: 0.001 USDC.e -> 0.01 USDC.e
```

## 接口与 CI

- `kite-watch snapshot URL [--baseline FILE] [--json]` 创建基准。
- `kite-watch check [--baseline FILE] [--json]` 从文件读取同一个 URL，再发出一次 GET；不会修改文件。
- 默认基准路径为当前目录的 `kite-baseline.json`。URL 会以明文保存，请使用没有密钥的公开只读端点。
- 退出码 **0**：已保存或无变化；**1**：付款条件变化；**2**：不能比较（例如超时、503、响应不是 402、格式不支持或文件错误）。CI 应区分 1 与 2，二者都不应当作“检查通过”。
- 在 CI 安装 CLI、提供经审核的基准文件后，直接执行 `kite-watch check --baseline approved.json --json`。变化输出包含 `status: changed`、URL 和逐字段的 `before` / `after`；错误输出包含 `status: error` 和原因。不要每次运行前重新生成基准。

## 范围

读取 x402 v2 的 Base64 PAYMENT-REQUIRED 头，仅支持单一 exact EVM 报价。初始网络限 Kite 主网 2366 或测试网 2368；后续切换至其他 EVM 网络也报告变化。按原子单位整数比较，地址忽略大小写；仅对已知链和合约组合显示 USDC.e 或 pieUSD 小数金额。映射依据：[Kite 官方 x402 模板](https://github.com/gokite-ai/kite-x402-services/tree/893a27509648b660bbba626b0da59619a94f04ab/templates)。

第一版仅监控 network、asset、amount、payTo；不监控 EIP-712 域、超时时间、余额、成交价或实际结算，不跟随重定向，不主动签名或重试付款。不支持多选报价、鉴权请求、POST 或只在响应正文提供挑战的卖家。演示卖家完全在本地模拟，无链上交易。远程端点应使用 HTTPS。

## 结构、测试与部署

`kite_watch/terms.py` 解码和规范化字段；`kite_watch/cli.py` 发请求、管理基准并生成文本或 JSON；`examples/` 提供本地可变报价；`tests/` 验证真实本地 HTTP 和命令行退出码。

```sh
python -m unittest discover -s tests -v
python -m pip wheel --no-deps . -w dist
python -m pip install dist/*.whl
kite-watch --help
```

部署只需把 wheel 安装到运行监控的机器并提供基准文件。出现 HTTP 200 时检查是否误用了免费路径；出现连接拒绝时先检查卖家进程和端口。项目不要求环境变量，配置均由命令行和基准文件提供。
