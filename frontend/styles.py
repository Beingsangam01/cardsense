import streamlit as st

BANK_COLORS = {
    "hdfc":     ("#004C8F", "#FFFFFF"),
    "sbi":      ("#2D6BB5", "#FFFFFF"),
    "icici":    ("#B02A2A", "#FFFFFF"),
    "axis":     ("#97144D", "#FFFFFF"),
    "indusind": ("#007849", "#FFFFFF"),
    "jupiter":  ("#5A31F4", "#FFFFFF"),
    "csb":      ("#FF6600", "#FFFFFF"),
    "roar":     ("#1A1A2E", "#FFFFFF"),
    "idfc":     ("#9B1B30", "#FFFFFF"),
    "rbl":      ("#003399", "#FFFFFF"),
}

BANK_INITIALS = {
    "hdfc":     "HD",
    "sbi":      "SB",
    "icici":    "IC",
    "axis":     "AX",
    "indusind": "IN",
    "jupiter":  "JU",
    "csb":      "CS",
    "roar":     "RO",
    "idfc":     "ID",
    "rbl":      "RB",
}

STATUS_CONFIG = {
    "Paid":    ("#00C853", "#F0FFF4"),
    "Unpaid":  ("#FF3B30", "#FFF1F0"),
    "Partial": ("#FF9500", "#FFFBEB"),
    "Active":  ("#0EA5E9", "#F0F9FF"),
    "Closed":  ("#6B7280", "#F9FAFB"),
}

CATEGORY_COLORS = {
    "Food":          "#FF6B35",
    "Travel":        "#1976D2",
    "Shopping":      "#E91E63",
    "Fuel":          "#F57F17",
    "Entertainment": "#FF6B35",
    "Healthcare":    "#E91E63",
    "EMI":           "#7B1FA2",
    "Subscription":  "#3F51B5",
    "Utilities":     "#00838F",
    "Transfer":      "#2E7D32",
    "Cashback":      "#2E7D32",
    "Other":         "#616161",
}

CHART_COLORS = [
    "#6C63FF", "#0EA5E9", "#00C853", "#FF9500",
    "#FF3B30", "#8B5CF6", "#EC4899", "#14B8A6",
    "#F59E0B", "#64748B"
]


# UTILITY FUNCTIONS
def fmt(amount) -> str:
    return '₹{:,.2f}'.format(float(amount or 0))


def fmt_k(amount) -> str:
    v = float(amount or 0)
    if v >= 100000:
        return '₹{:.1f}L'.format(v / 100000)
    elif v >= 1000:
        return '₹{:.1f}K'.format(v / 1000)
    return '₹{:.0f}'.format(v)


def bank_logo_html(bank_name: str, size: int = 36) -> str:
    key      = bank_name.lower().strip()
    initials = BANK_INITIALS.get(key, bank_name[:2].upper())
    bg, fg   = BANK_COLORS.get(key, ("#6C63FF", "#FFFFFF"))
    return (
        '<div style="width:' + str(size) + 'px;height:' + str(size) + 'px;'
        'border-radius:' + str(size // 4) + 'px;'
        'background:' + bg + ';color:' + fg + ';'
        'display:inline-flex;align-items:center;justify-content:center;'
        'font-size:' + str(size // 3) + 'px;font-weight:800;'
        'flex-shrink:0;letter-spacing:-0.5px;">'
        + initials + '</div>'
    )


def status_badge_html(status: str) -> str:
    color, bg = STATUS_CONFIG.get(status, ("#6B7280", "#F9FAFB"))
    return (
        '<span style="display:inline-block;font-size:11px;font-weight:700;'
        'padding:3px 10px;border-radius:20px;'
        'background:' + bg + ';color:' + color + ';">'
        + status + '</span>'
    )


def category_icon_html(category: str, size: int = 18) -> str:
    color   = CATEGORY_COLORS.get(category, "#616161")
    initial = category[0].upper() if category else "?"
    return (
        '<div style="width:' + str(size + 10) + 'px;'
        'height:' + str(size + 10) + 'px;'
        'border-radius:50%;background:#F3F4F6;'
        'display:inline-flex;align-items:center;justify-content:center;'
        'flex-shrink:0;font-size:' + str(size - 4) + 'px;'
        'font-weight:700;color:' + color + ';">'
        + initial + '</div>'
    )


def svg_icon(name: str, size: int = 16, color: str = '#666') -> str:
    icons = {
        "card":       '<svg viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>',
        "calendar":   '<svg viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
        "alert":      '<svg viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        "statements": '<svg viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
        "note":       '<svg viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 16.5-16.5z"/></svg>',
        "loan":       '<svg viewBox="0 0 24 24" fill="none" stroke="' + color + '" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>',
    }
    svg = icons.get(name, icons['card'])
    return (
        '<span style="display:inline-flex;align-items:center;'
        'vertical-align:middle;width:' + str(size) + 'px;'
        'height:' + str(size) + 'px;">' + svg + '</span>'
    )


def page_header(title: str, subtitle: str = ''):
    st.markdown('## ' + title)
    if subtitle:
        st.caption(subtitle)