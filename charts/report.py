from __future__ import annotations
import pandas as pd

class Report:
    @staticmethod
    def equity_and_drawdown(equity: pd.Series, outpath: str) -> list[str]:
        """Save equity and drawdown charts.
        Returns a list of saved file paths. If matplotlib is not installed,
        prints a friendly message and returns an empty list.
        """
        try:
            import matplotlib.pyplot as plt  # import here to avoid dependency issues
        except ModuleNotFoundError:
            print("[Charts] matplotlib is not installed. Skipping chart generation.\n"
                  "Install with: pip install matplotlib")
            return []
        paths: list[str] = []
        # Plot equity curve
        plt.figure()
        equity.plot(title="Equity Curve")
        plt.tight_layout()
        eq_path = outpath.replace(".png","_equity.png")
        plt.savefig(eq_path)
        plt.close(); paths.append(eq_path)
        # Plot drawdown
        plt.figure()
        dd = equity / equity.cummax() - 1.0
        dd.plot(title="Drawdown")
        plt.tight_layout()
        dd_path = outpath.replace(".png","_drawdown.png")
        plt.savefig(dd_path)
        plt.close(); paths.append(dd_path)
        return paths