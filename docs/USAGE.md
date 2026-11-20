# CLI 与 GitHub Actions

```text
kite-watch snapshot URL [--baseline FILE] [--timeout SECONDS] [--json]
kite-watch check [--baseline FILE] [--timeout SECONDS] [--json]
kite-watch inspect [--baseline FILE] [--json]
```

默认基准路径为 `kite-baseline.json`。超时默认 5 秒，可设为大于 0、至多 60 的秒数。它传给网络连接的阻塞操作；CI 可额外设置整个作业的时限。使用可信的 HTTPS GET 地址，避免把凭证放进 URL 或提交到基准中。`check` 不修改基准，也不跟随重定向。

`inspect` 离线显示基准中保存的 URL、网络、代币、金额和收款地址，并把已知 Kite 代币的原子金额换算为可读价格。它不会请求卖家或改写文件；要看当前报价是否变化，请用 `check`。

| 退出码 | 含义 | `--json` 中的 `status` |
| --- | --- | --- |
| `0` | 已保存或查看基准，或当前报价与基准一致 | `saved` / `inspected` / `unchanged` |
| `1` | 至少一项支付条件变化 | `changed` |
| `2` | 无法比较，例如超时、503、响应不支持、基准无效 | `error` |

`changed` 的 `changes` 按变化字段给出 `before` 和 `after`；`error` 的 `error` 给出原因。命令语法不合法时，参数解析会以 `2` 退出并在标准错误输出用法。

例如，检查发现 `1 USDC.e` 变成了 `2 USDC.e`：

```json
{"status":"changed","url":"https://api.example.com/paid","changes":{"amount":{"before":"1000000","after":"2000000"}}}
```

在调用方仓库使用 [工作流示例](../examples/github-actions/kite-quote-watch.yml)：

1. 把工作流复制到 `.github/workflows/kite-quote-watch.yml`，并把已人工审核的基准提交到 `watch/approved.json`。不要在检查前重新生成基准。
2. 在仓库 **Settings → Secrets and variables → Actions → Variables** 中，把 `KITE_WATCH_REV` 设置为已经审核的 `kite-x402-watch` Git 提交的完整 SHA。这个值不含密钥。
3. 在 **Actions → Watch Kite x402 payment terms → Run workflow** 手动运行。报价一致时通过；报价变化与检查失败都会使作业失败，并分别给出提示。需要定时检查时，可以给工作流添加 `schedule` 触发器。

先在自己的测试端点验证工作流，再把同一个比较命令接到部署前检查中。只使用可信分支上审核过的基准。
