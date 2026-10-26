"""Generate single-stock review HTML."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.codes import resolve_code
from src.fundamentals import build_fundamental_panel, fetch_dividends
from src.market import fetch_daily
from src.render_report import render_html
from src.valuation import build_valuation_series, current_snapshot

def main():
    query = sys.argv[1] if len(sys.argv) > 1 else '宁德时代'
    code, name = resolve_code(query)
    if name == code:
        name = query
    print('[1/4] daily', code)
    daily = fetch_daily(code, start_date='2018-01-01')
    print('  bars', len(daily), 'last', daily['date'].iloc[-1].date(), 'close', round(float(daily['close'].iloc[-1]), 2))
    print('[2/4] fundamentals')
    fundamentals = build_fundamental_panel(code)
    dividends = fetch_dividends(code)
    print('  quarters', len(fundamentals), 'dividends', len(dividends))
    print('[3/4] valuation')
    valuation = build_valuation_series(fundamentals, daily, dividends)
    snap = current_snapshot(fundamentals, daily, dividends)
    pe = snap['pe_ttm_deduct']; pb = snap['pb']; dv = snap['div_yield_pct']
    print('  points', len(valuation), 'PE', None if pe is None else round(pe,1), 'PB', None if pb is None else round(pb,2), 'div', None if dv is None else round(dv,2))
    out = ROOT / 'output' / ('%s_%s_复盘.html' % (code, name))
    print('[4/4] render')
    path = render_html(name=name, code=code, daily=daily, fundamentals=fundamentals, valuation=valuation, snap=snap, out_path=out)
    cache = ROOT / 'output' / ('%s_cache' % code)
    cache.mkdir(parents=True, exist_ok=True)
    daily.to_csv(cache / 'daily.csv', index=False)
    fundamentals.to_csv(cache / 'fundamentals.csv', index=False)
    valuation.to_csv(cache / 'valuation.csv', index=False)
    print('DONE', path)
    print('Open in browser:', path.resolve().as_uri())

if __name__ == '__main__':
    main()
