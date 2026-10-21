"""The engine log text without emoji (v0.17.1): Smiggles' log lines -> plain section headings.

Applied to Smiggles' engine script source by tools/port_smiggles.py, and by the tests to the
original Smiggles script before running the two side by side, so the logs still match exactly
and this list is the only difference. Each must match exactly once.
"""

LOG_TEXT = [
    ("🕐 {{ now()", "Run: {{ now()"),
    ("🔄 Mode:", "Mode:"),
    ("💰 Prices:", "Prices:"),
    ("currentSellPrice %}💰{% endif %}{% if spikePrice2", "currentSellPrice %} (Spike 1){% endif %}{% if spikePrice2"),
    ("%}💰{% endif %}", "%} (Spike 2){% endif %}"),
    ("🔒 Min Sell:", "Min Sell:"),
    ("🔋 Battery:", "Battery:"),
    ("📊 SOC Limits:", "SOC Limits:"),
    ("☀️ Solar:", "Solar:"),
    ("(Bad!\n        ⛅){% endif %}", "(Bad!){% endif %}"),
    ("⚡ Actions:", "Actions:"),
    ("📈 Sell Forecasts:", "Sell Forecasts:"),
    ("📉 Buy Forecasts:", "Buy Forecasts:"),
    ("ℹ️ Version:", "Version:"),
    ("ℹ️ Debug ", "Debug: "),
    ("title: ☀️ Solar System Control", "title: Solar System Control"),
]


def plain_log(script_text: str) -> str:
    for old, new in LOG_TEXT:
        n = script_text.count(old)
        if n != 1:
            raise ValueError(f"log text {old!r} found {n} times (expected once)")
        script_text = script_text.replace(old, new)
    return script_text
