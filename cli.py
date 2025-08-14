from __future__ import annotations
import argparse, os, asyncio
from data.providers import YFinanceProvider, AlpacaRealtime
from brokers.paper import PaperBroker
from brokers.alpaca import AlpacaBroker
from strategy.sma_cross import MovingAverageCross
from risk.manager import RiskManager, RiskConfig
from risk.metrics import Risk
from backtest.engine import Backtester
from charts.report import Report

def _parser():
    p = argparse.ArgumentParser(description="Equities Backtesting & Live Trading System")
    sub = p.add_subparsers(dest="cmd", required=True)

    bt = sub.add_parser("backtest", help="Run a backtest")
    bt.add_argument("--symbol", required=True)
    bt.add_argument("--start", required=True)
    bt.add_argument("--end", required=True)
    bt.add_argument("--fast", type=int, default=20)
    bt.add_argument("--slow", type=int, default=50)
    bt.add_argument("--initial-cash", type=float, default=100000)
    bt.add_argument("--commission", type=float, default=0.0)
    bt.add_argument("--slippage-bps", type=float, default=1.0)
    bt.add_argument("--no-charts", action="store_true", help="Skip chart generation")

    lv = sub.add_parser("live", help="Run live trading")
    lv.add_argument("--symbol", required=True)
    lv.add_argument("--fast", type=int, default=20)
    lv.add_argument("--slow", type=int, default=50)
    lv.add_argument("--broker", choices=["paper","alpaca"], default="paper")
    lv.add_argument("--poll-secs", type=int, default=10)

    return p


def main(argv=None):
    args = _parser().parse_args(argv)

    if args.cmd == "backtest":
        provider = YFinanceProvider()
        df = provider.history(args.symbol, args.start, args.end)
        strat = MovingAverageCross(args.fast, args.slow)
        risk = RiskManager(RiskConfig())
        broker = PaperBroker(slippage_bps=args.slippage_bps, commission_per_share=args.commission)
        bt = Backtester(df, strat, args.initial_cash, broker, risk)
        res = bt.run(args.symbol)
        print("\nBacktest metrics:")
        width = max(len(k) for k in res.metrics)
        for k,v in res.metrics.items():
            try:
                print(f"{k:<{width}} : {v:.4f}")
            except Exception:
                print(f"{k:<{width}} : {v}")
        # Generate charts
        if not args.no_charts:
            out = f"report_{args.symbol}_{args.start}_{args.end}.png"
            paths = Report.equity_and_drawdown(res.equity_curve, out)
            if paths:
                print("Charts saved:")
                for pth in paths:
                    print(" -", pth)

    elif args.cmd == "live":
        from live.runner import LiveTrader
        provider = YFinanceProvider()  # fallback for demo
        strat = MovingAverageCross(args.fast, args.slow)
        risk = RiskManager(RiskConfig())
        broker = PaperBroker() if args.broker == "paper" else AlpacaBroker()
        if args.broker == "alpaca":
            # Try websocket first
            try:
                rt = AlpacaRealtime([args.symbol])
                trader = LiveTrader(provider, broker, strat, risk)
                asyncio.run(trader.run_websocket(args.symbol, rt.stream_trades()))
                return
            except Exception as e:
                print(f"Websocket failed ({e}), using polling instead.")
        trader = LiveTrader(provider, broker, strat, risk)
        trader.run_polling(args.symbol, args.poll_secs)

if __name__ == "__main__":
    main()
