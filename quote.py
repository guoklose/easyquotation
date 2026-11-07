# coding:utf8
"""easyquotation 命令行包装器 —— 给 Hermes / 脚本用的统一入口。

用法:
    quote.py real 600519 000001 [--source sina|tencent] [--prefix]
    quote.py snapshot [--source sina|tencent] [--limit N] [--prefix]
    quote.py hk 00700 00001
    quote.py kline 00700 [--days 350]
    quote.py etf
    quote.py fx
    quote.py codes [--realtime]

输出统一为 JSON（UTF-8, ensure_ascii=False）。
"""
import argparse
import json
import sys

import easyquotation


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
    q = easyquotation.use("jsl")
    return q.etfindex()


def cmd_fx(args):
    q = easyquotation.use("boc")
    return q.get_exchange_rate()


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
    e.set_defaults(func=cmd_etf)

    f = sub.add_parser("fx", help="中国银行外汇牌价")
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
