# coding:utf8
"""easyquotation 命令行包装器 —— 给 Hermes / 脚本用的统一入口。

用法:
    quote.py real 600519 000001 [--source sina|tencent] [--prefix]
    quote.py snapshot [--source sina|tencent] [--limit N] [--prefix]
    quote.py hk 00700 00001
    quote.py kline 00700 [--days 350]
    quote.py etf [--rp 25] [--page 1] [--cookie ...]
    quote.py qdii [--cookie ...]
    quote.py cb --cookie ...
    quote.py fx [--currency usa|hkd|eur|jpy|...]
    quote.py codes [--realtime]

输出统一为 JSON（UTF-8, ensure_ascii=False）。
"""
import argparse
import json
import sys
from typing import cast

import easyquotation
from easyquotation.jsl import Jsl


def _jsl() -> Jsl:
    """拿到 Jsl 实例（带类型，Pyright 才知道有 etfindex/qdii/cb）。"""
    return cast(Jsl, easyquotation.use("jsl"))


def _dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


def cmd_real(args):
    q = easyquotation.use(args.source)
    return q.real(args.codes, prefix=args.prefix)


def cmd_snapshot(args):
    q = easyquotation.use(args.source)
    data = q.market_snapshot(prefix=args.prefix)
    if args.limit:
        data = dict(list(data.items())[: args.limit])
    return data


def cmd_hk(args):
    q = easyquotation.use("hkquote")
    return q.real(args.codes)


def cmd_kline(args):
    q = easyquotation.use("daykline")
    data = q.real(args.codes)
    out = {}
    for code, rows in data.items():
        out[code] = rows[-args.days :] if args.days else rows
    return out


def cmd_etf(args):
    q = _jsl()
    if args.cookie:
        q.set_cookie(args.cookie)
    data = q.etfindex(
        index_id=args.index_id or "",
        min_volume=args.min_volume,
        max_discount=args.max_discount,
        min_discount=args.min_discount,
        rp=args.rp,
        page=args.page,
    )
    if args.limit:
        data = dict(list(data.items())[: args.limit])
    return data


def cmd_qdii(args):
    q = _jsl()
    if args.cookie:
        q.set_cookie(args.cookie)
    return q.qdii(min_volume=args.min_volume)


def cmd_cb(args):
    q = _jsl()
    return q.cb(min_volume=args.min_volume, cookie=args.cookie)


def cmd_fx(args):
    q = easyquotation.use("boc")
    return q.get_exchange_rate(args.currency)  # type: ignore[attr-defined]


def cmd_codes(args):
    if args.realtime:
        return {"stock": easyquotation.update_stock_codes()["stock"]}
    codes = easyquotation.get_stock_codes()
    return {"count": len(codes), "sample": codes[:20]}


def main():
    p = argparse.ArgumentParser(prog="quote.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("real", help="指定股票的实时行情")
    r.add_argument("codes", nargs="+", help="股票代码，如 600519 / sh000001")
    r.add_argument("--source", default="sina", choices=["sina", "tencent", "qq"])
    r.add_argument("--prefix", action="store_true", help="返回键带 sh/sz/bj 前缀")
    r.set_defaults(func=cmd_real)

    s = sub.add_parser("snapshot", help="全市场行情快照")
    s.add_argument("--source", default="sina", choices=["sina", "tencent", "qq"])
    s.add_argument("--limit", type=int, default=0, help="只输出前 N 条，0=全部")
    s.add_argument("--prefix", action="store_true")
    s.set_defaults(func=cmd_snapshot)

    h = sub.add_parser("hk", help="港股实时行情")
    h.add_argument("codes", nargs="+")
    h.set_defaults(func=cmd_hk)

    k = sub.add_parser("kline", help="港股日K线（前复权）")
    k.add_argument("codes", nargs="+")
    k.add_argument("--days", type=int, default=60, help="返回最近 N 天")
    k.set_defaults(func=cmd_kline)

    e = sub.add_parser("etf", help="集思路 ETF 列表")
    e.add_argument("--index-id", default="", help="只取跟踪该指数的 ETF")
    e.add_argument("--min-volume", type=float, default=0, help="最小成交量")
    e.add_argument("--max-discount", default=None, help="最高溢价率，如 -0.4 或 -0.4%%")
    e.add_argument("--min-discount", default=None, help="最低溢价率，如 -1.3 或 -1.3%%")
    e.add_argument("--rp", type=int, default=25, help="每页条数（游客最多 20 条）")
    e.add_argument("--page", type=int, default=1, help="页码")
    e.add_argument("--limit", type=int, default=0, help="只输出前 N 条，0=全部")
    e.add_argument("--cookie", default=None, help="集思路登录 Cookie（游客只能看到前 20 条）")
    e.set_defaults(func=cmd_etf)

    d = sub.add_parser("qdii", help="集思路 QDII 基金列表")
    d.add_argument("--min-volume", type=float, default=0, help="最小交易量（万元）")
    d.add_argument("--cookie", default=None, help="集思路登录 Cookie")
    d.set_defaults(func=cmd_qdii)

    b = sub.add_parser("cb", help="集思路可转债列表（需要登录 Cookie）")
    b.add_argument("--min-volume", type=float, default=0, help="最小交易量（万元）")
    b.add_argument("--cookie", default=None, help="集思路登录 Cookie（必填）")
    b.set_defaults(func=cmd_cb)

    f = sub.add_parser("fx", help="中国银行外汇牌价")
    f.add_argument(
        "--currency",
        default="usa",
        help="币种代码，如 usa/hkd/eur/jpy/gbp/aud/cad/chf/sgd/nzd/krw；也接受中文名",
    )
    f.set_defaults(func=cmd_fx)

    c = sub.add_parser("codes", help="股票代码表")
    c.add_argument("--realtime", action="store_true", help="从上游拉最新代码表")
    c.set_defaults(func=cmd_codes)

    args = p.parse_args()
    try:
        result = args.func(args)
    except Exception as e:  # noqa
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(_dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
