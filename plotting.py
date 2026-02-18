"""
Shared utilities for plot saving and table data generation.
Eliminates boilerplate duplication across analysis modules.
"""

import io
import pandas as pd
import matplotlib.pyplot as plt


def save_plot_to_buffer(fig=None):
    """
    Saves the current (or given) matplotlib figure to a BytesIO buffer.
    Closes the figure to free memory.
    Returns the buffer (seeked to 0).
    """
    buf = io.BytesIO()
    target = fig if fig is not None else plt.gcf()
    target.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(target)
    return buf


def build_table_data(df, column_formatters, sort_ascending=False):
    """
    Vectorized table data builder. Converts a DataFrame into a list of dicts
    suitable for Jinja template rendering.

    Args:
        df: pandas DataFrame (index may be used via 'index' key in formatters).
        column_formatters: dict mapping output key -> (source_column, format_func).
            If source_column is '__index__', uses the DataFrame index.
            format_func signature: value -> str
        sort_ascending: if False (default), reverses the list (newest first).

    Returns:
        list[dict] ready for template rendering.
    """
    records = []
    for idx, row in df.iterrows():
        record = {}
        for out_key, (source, fmt_fn) in column_formatters.items():
            if source == '__index__':
                record[out_key] = fmt_fn(idx)
            else:
                record[out_key] = fmt_fn(row[source])
        records.append(record)

    if not sort_ascending:
        records.reverse()

    return records
