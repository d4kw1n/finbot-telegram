"""Chart generation service using matplotlib.

Generates PNG charts for Telegram with a dark theme that looks good
on both light and dark Telegram themes.
"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import tempfile
import os
from datetime import date

from src.utils.constants import CATEGORY_TYPE_LABELS

# ─── Theme ────────────────────────────────────────────────────────────
BG_COLOR = '#1a1a2e'
TEXT_COLOR = '#e0e0e0'
GRID_COLOR = '#2a2a4a'
ACCENT_COLORS = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
    '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
    '#F8C471', '#82E0AA', '#F1948A', '#AED6F1', '#D2B4DE',
]

plt.rcParams.update({
    'figure.facecolor': BG_COLOR,
    'axes.facecolor': BG_COLOR,
    'text.color': TEXT_COLOR,
    'axes.labelcolor': TEXT_COLOR,
    'xtick.color': TEXT_COLOR,
    'ytick.color': TEXT_COLOR,
    'axes.edgecolor': GRID_COLOR,
    'grid.color': GRID_COLOR,
    'font.size': 12,
})


def _save_chart(fig) -> str:
    """Save figure to temp PNG file and return path."""
    tmpfile = tempfile.NamedTemporaryFile(
        suffix='.png', delete=False, prefix='finbot_chart_'
    )
    fig.savefig(
        tmpfile.name, dpi=150, bbox_inches='tight',
        facecolor=BG_COLOR, edgecolor='none'
    )
    plt.close(fig)
    return tmpfile.name


def create_pie_chart(data: dict[str, float], title: str) -> str:
    """Create a donut-style pie chart.

    Args:
        data: {label: value} dict
        title: Chart title

    Returns:
        Path to generated PNG file.
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    labels = list(data.keys())
    values = list(data.values())
    colors = ACCENT_COLORS[:len(labels)]

    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct='%1.1f%%',
        colors=colors, startangle=90, pctdistance=0.80,
        wedgeprops=dict(width=0.35, edgecolor=BG_COLOR, linewidth=2)
    )

    for autotext in autotexts:
        autotext.set_color(TEXT_COLOR)
        autotext.set_fontsize(10)

    # Total in center
    total = sum(values)
    from src.utils.formatter import format_currency
    ax.text(0, 0, format_currency(total, short=True),
            ha='center', va='center', fontsize=18,
            fontweight='bold', color=TEXT_COLOR)

    # Legend
    legend_labels = [
        f"{labels[i]}  ({format_currency(values[i], short=True)})"
        for i in range(len(labels))
    ]
    ax.legend(wedges, legend_labels, loc='center left',
              bbox_to_anchor=(1, 0.5), fontsize=10,
              frameon=False)

    ax.set_title(title, fontsize=16, fontweight='bold',
                 color=TEXT_COLOR, pad=20)

    plt.tight_layout()
    return _save_chart(fig)


def create_bar_chart(data: dict[str, float], title: str,
                     ylabel: str = "VND", horizontal: bool = False) -> str:
    """Create a bar chart.

    Args:
        data: {label: value} dict
        title: Chart title
        ylabel: Y-axis label
        horizontal: If True, create horizontal bars

    Returns:
        Path to generated PNG file.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    labels = list(data.keys())
    values = list(data.values())
    colors = ACCENT_COLORS[:len(labels)]

    if horizontal:
        bars = ax.barh(labels, values, color=colors, height=0.6,
                       edgecolor=BG_COLOR, linewidth=1)
        ax.set_xlabel(ylabel)
        # Add value labels
        from src.utils.formatter import format_currency
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max(values) * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    format_currency(val, short=True),
                    va='center', fontsize=10, color=TEXT_COLOR)
    else:
        bars = ax.bar(labels, values, color=colors, width=0.6,
                      edgecolor=BG_COLOR, linewidth=1)
        ax.set_ylabel(ylabel)
        # Add value labels on top
        from src.utils.formatter import format_currency
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    format_currency(val, short=True),
                    ha='center', va='bottom', fontsize=10, color=TEXT_COLOR)

    ax.set_title(title, fontsize=16, fontweight='bold',
                 color=TEXT_COLOR, pad=15)
    ax.grid(axis='y' if not horizontal else 'x',
            alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Format y-axis with K/M suffixes
    def fmt_amount(x, _):
        if x >= 1_000_000:
            return f'{x/1_000_000:.0f}M'
        elif x >= 1_000:
            return f'{x/1_000:.0f}K'
        return f'{x:.0f}'

    if horizontal:
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_amount))
    else:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_amount))

    plt.xticks(rotation=30 if not horizontal else 0, ha='right')
    plt.tight_layout()
    return _save_chart(fig)


def create_trend_chart(dates: list[str], values: list[float],
                       title: str) -> str:
    """Create a line chart showing spending trends.

    Args:
        dates: List of date strings (DD/MM)
        values: List of daily totals
        title: Chart title

    Returns:
        Path to generated PNG file.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(dates, values, color='#4ECDC4', linewidth=2.5,
            marker='o', markersize=6, markerfacecolor='#FF6B6B',
            markeredgecolor='white', markeredgewidth=1.5)

    # Fill area under line
    ax.fill_between(dates, values, alpha=0.15, color='#4ECDC4')

    ax.set_title(title, fontsize=16, fontweight='bold',
                 color=TEXT_COLOR, pad=15)
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Format y-axis
    def fmt_amount(x, _):
        if x >= 1_000_000:
            return f'{x/1_000_000:.1f}M'
        elif x >= 1_000:
            return f'{x/1_000:.0f}K'
        return f'{x:.0f}'

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_amount))

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    return _save_chart(fig)


def create_budget_comparison_chart(categories: list[dict],
                                   title: str) -> str:
    """Create a horizontal bar chart comparing spending vs budget.

    Args:
        categories: List of dicts with name, emoji, total_spent, budget_limit
        title: Chart title

    Returns:
        Path to generated PNG file.
    """
    fig, ax = plt.subplots(figsize=(10, max(4, len(categories) * 0.8)))

    labels = [f"{c['emoji']} {c['name']}" for c in categories]
    spent = [c['total_spent'] for c in categories]
    budgets = [c.get('budget_limit', 0) for c in categories]

    y = range(len(labels))

    # Budget bars (background)
    if any(b > 0 for b in budgets):
        ax.barh(y, budgets, height=0.4, color='#2a2a4a', label='Ngân sách',
                edgecolor=GRID_COLOR)

    # Spent bars (foreground)
    colors = ['#FF6B6B' if s > b and b > 0 else '#4ECDC4'
              for s, b in zip(spent, budgets)]
    ax.barh(y, spent, height=0.4, color=colors, label='Đã chi',
            edgecolor=BG_COLOR)

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_title(title, fontsize=16, fontweight='bold',
                 color=TEXT_COLOR, pad=15)
    ax.legend(frameon=False)

    def fmt_amount(x, _):
        if x >= 1_000_000:
            return f'{x/1_000_000:.1f}M'
        elif x >= 1_000:
            return f'{x/1_000:.0f}K'
        return f'{x:.0f}'

    ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_amount))
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()
    return _save_chart(fig)
