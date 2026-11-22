from datetime import date, datetime, timedelta
import calendar
import math
import statistics
from flask import current_app

from config import get_config
import db

# =============================================================================
# SUPPLY CHAIN FORMULAS
# =============================================================================


def _get_config_value(key: str, default=None):
    if current_app:
        return current_app.config.get(key, default)
    return getattr(get_config(), key, default)


def calculate_eoq(
    annual_demand: float, holding_cost: float, setup_cost: float, conversion: int
) -> int:
    """
    Calculates the Economic Order Quantity (EOQ) using the classical Wilson lot-size formula.

    Formula:
        Q = sqrt((2 * D * S) / H)
    """
    if holding_cost <= 0 or annual_demand <= 0 or setup_cost <= 0:
        return 0
    box_size = max(int(conversion), 1)
    raw_eoq = math.sqrt(
        (2.0 * float(annual_demand) * float(setup_cost)) / float(holding_cost)
    )
    box_eoq = math.ceil(raw_eoq / box_size) * box_size
    return int(round(box_eoq))


def calculate_ss(
    service_level: float,
    std_lt: float | None,
    std_demand: float | None,
    lt: float | int | None,
    avg_daily_demand: float | None = 0.0,
) -> int:
    """
    Computes required Safety Stock (SS) under stochastic demand and supplier lead time.

    Formula:
        SS = z * sqrt(LT * sigma_d^2 + d_bar^2 * sigma_LT^2)
    """
    effective_lt = max(float(lt) if lt is not None else 1.0, 1.0)
    sigma_d = max(float(std_demand) if std_demand is not None else 0.0, 0.0)
    sigma_lt = max(float(std_lt) if std_lt is not None else 0.0, 0.0)
    d_bar = max(float(avg_daily_demand) if avg_daily_demand is not None else 0.0, 0.0)

    variance_lead_time_demand = (effective_lt * (sigma_d**2)) + (
        (d_bar**2) * (sigma_lt**2)
    )
    std_lead_time_demand = math.sqrt(variance_lead_time_demand)

    clamped_sl = min(max(float(service_level), 0.50), 0.999)
    try:
        z = statistics.NormalDist(mu=0.0, sigma=1.0).inv_cdf(clamped_sl)
    except Exception:
        z = 1.64485  # Fallback for ~95% cycle service level

    return int(round(z * std_lead_time_demand))


def calculate_rop(daily_demand: float, effective_lt: float, safety_stock: int) -> int:
    """
    Calculates the Reorder Point (ROP) inventory threshold that triggers replenishment.

    Formula:
        ROP = (d_bar * L_eff) + SS
    """
    raw_rop = (float(daily_demand) * float(effective_lt)) + float(safety_stock)
    return int(round(raw_rop))


def calculate_abc(products_list: list[dict]) -> list[dict]:
    """
    Calculates ABC classification for each product based on value = demand * price.
    """
    if not products_list:
        return []

    a_threshold = float(_get_config_value("ABC_A_THRESHOLD", 80.0))
    b_threshold = float(_get_config_value("ABC_B_THRESHOLD", 95.0))

    def assign_tier(cum_pct: float) -> str:
        if cum_pct <= a_threshold:
            return "A"
        if cum_pct <= b_threshold:
            return "B"
        return "C"

    enriched = []
    for p in products_list:
        item = dict(p)
        item["value"] = float(item["demand"]) * float(item["price"])
        enriched.append(item)

    skus_sorted = sorted(enriched, key=lambda item: item["value"], reverse=True)
    total_value = sum(item["value"] for item in skus_sorted)

    running_total = 0.0
    for item in skus_sorted:
        if total_value > 0:
            running_total += item["value"]
            item["cum_pct"] = (running_total / total_value) * 100.0
            item["tier"] = assign_tier(item["cum_pct"])
        else:
            item["cum_pct"] = 0.0
            item["tier"] = "C"

    return skus_sorted


# =============================================================================
# SIMULATION & SVG VISUALIZATION
# =============================================================================


def simulation_eoq(
    starting_inventory: int = 200,
    open_order_date: str = "",
    dates: list = None,
    demands: list = None,
    rop: int = 0,
    eoq: int = 0,
    effective_lt: int = 2,
) -> list:
    """
    Simulates the daily continuous inventory balance trajectory over a date series.

    Formula / Simulation Execution:
        At each daily time step t:
            Inventory_t = max(Inventory_{t-1} + Replenish_t - Demand_t, 0)
        Order Placement Rule:
            If Inventory_t <= ROP and no replenishment order is currently in transit,
            schedule a replenishment batch of size EOQ arriving at step (t + effective_lt).
    """
    if not dates or not demands:
        return []

    n_days = min(len(dates), len(demands))
    if n_days == 0:
        return []

    sim_records = []
    replenish_schedule = [0] * n_days
    lead_time = max(int(round(effective_lt)), 1)
    order_qty = max(int(eoq), 0)

    if open_order_date and order_qty > 0:
        open_str = str(open_order_date)[:10]
        if open_str in dates:
            open_idx = dates.index(open_str)
            replenish_schedule[open_idx] += order_qty

    # Initial day 0 balance
    init_demand = max(int(demands[0] or 0), 0)
    init_replenish = replenish_schedule[0]
    init_inv = max(int(starting_inventory) + init_replenish - init_demand, 0)
    sim_records.append({
        "date": dates[0],
        "demand": init_demand,
        "inventory": init_inv,
        "replenish": init_replenish,
    })

    current_inv = init_inv

    for i in range(1, n_days):
        day_demand = max(int(demands[i] or 0), 0)
        day_replenish = replenish_schedule[i]

        # Calculate balance after delivery arrival and sales satisfaction
        current_inv = max(current_inv + day_replenish - day_demand, 0)

        # Trigger reorder if at or below ROP and no batch is currently in transit
        window_end = min(i + lead_time, n_days)
        in_transit = sum(replenish_schedule[i:window_end])

        if (
            current_inv <= rop
            and in_transit == 0
            and order_qty > 0
            and (i + lead_time < n_days)
        ):
            replenish_schedule[i + lead_time] += order_qty

        sim_records.append({
            "date": dates[i],
            "demand": day_demand,
            "inventory": current_inv,
            "replenish": day_replenish,
        })

    return sim_records


def generate_eoq_simulation_svg(
    sim_data: list,
    rop: int,
    ss: int,
    zoom: str = "month",
    product_name: str = "Product",
) -> str:
    """
    Generates a clean, modern, pure-SVG line chart of the EOQ inventory sawtooth.
    """
    if not sim_data:
        return (
            '<svg viewBox="0 0 750 280" class="graph-svg">'
            '<text x="375" y="140" text-anchor="middle" fill="#64748b">'
            "No simulation data available</text></svg>"
        )

    width = 750
    height = 290
    pad_left = 55
    pad_right = 30
    pad_top = 35
    pad_bottom = 45

    chart_w = width - pad_left - pad_right
    chart_h = height - pad_top - pad_bottom

    inv_values = [r["inventory"] for r in sim_data]
    max_val = max(max(inv_values, default=100), rop * 1.3, ss * 1.5, 50)
    y_max = math.ceil(max_val / 50.0) * 50  # Round up to clean step

    n = len(sim_data)

    def get_x(idx):
        if n <= 1:
            return pad_left + chart_w / 2.0
        return pad_left + (idx * chart_w / (n - 1))

    def get_y(val):
        return pad_top + chart_h - (min(max(val, 0), y_max) * chart_h / y_max)

    points = []
    area_points = [f"{pad_left},{pad_top + chart_h}"]
    for idx, r in enumerate(sim_data):
        x = get_x(idx)
        y = get_y(r["inventory"])
        points.append(f"{x:.1f},{y:.1f}")
        area_points.append(f"{x:.1f},{y:.1f}")
    area_points.append(f"{get_x(n - 1):.1f},{pad_top + chart_h}")

    line_coords = " ".join(points)
    area_coords = " ".join(area_points)

    rop_y = get_y(rop)
    ss_y = get_y(ss)

    y_ticks_svg = []
    for step in range(5):
        val = int(step * y_max / 4)
        y_pos = get_y(val)
        y_ticks_svg.append(
            f'<line x1="{pad_left}" y1="{y_pos:.1f}" x2="{width - pad_right}" y2="{y_pos:.1f}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />'
            f'<text x="{pad_left - 8}" y="{y_pos + 4:.1f}" text-anchor="end" fill="#94a3b8" font-size="11" font-family="sans-serif">{val}</text>'
        )

    today = date.today()
    current_year = today.year
    current_month_abbr = today.strftime("%b")
    current_month_full = today.strftime("%B")

    x_ticks_svg = []
    if zoom == "month":
        tick_indices = [0, 4, 9, 14, 19, 24, n - 1]
        for t_idx in tick_indices:
            if t_idx < n:
                x_pos = get_x(t_idx)
                d_str = str(sim_data[t_idx]["date"])
                day_lbl = f"{int(d_str.split('-')[-1])} {current_month_abbr}"
                x_ticks_svg.append(
                    f'<line x1="{x_pos:.1f}" y1="{pad_top + chart_h}" x2="{x_pos:.1f}" y2="{pad_top + chart_h + 5}" stroke="#64748b" stroke-width="1" />'
                    f'<text x="{x_pos:.1f}" y="{pad_top + chart_h + 18}" text-anchor="middle" fill="#94a3b8" font-size="11" font-family="sans-serif">{day_lbl}</text>'
                )
    else:
        months_seen = set()
        m_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for idx, r in enumerate(sim_data):
            d_str = str(r["date"])
            month_key = d_str[:7]
            if month_key not in months_seen and d_str.endswith("-01"):
                months_seen.add(month_key)
                x_pos = get_x(idx)
                m_num = int(month_key.split("-")[1])
                m_lbl = m_names[m_num - 1]
                x_ticks_svg.append(
                    f'<line x1="{x_pos:.1f}" y1="{pad_top + chart_h}" x2="{x_pos:.1f}" y2="{pad_top + chart_h + 5}" stroke="#64748b" stroke-width="1" />'
                    f'<text x="{x_pos:.1f}" y="{pad_top + chart_h + 18}" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="sans-serif">{m_lbl}</text>'
                )

    period_heading = (
        f"{current_month_full} {current_year}"
        if zoom == "month"
        else f"Calendar Year {current_year}"
    )

    svg_content = f"""
    <svg viewBox="0 0 {width} {height}" class="graph-svg" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="eoqGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#10b981" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="#10b981" stop-opacity="0.02"/>
        </linearGradient>
        <linearGradient id="dangerZoneGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#ef4444" stop-opacity="0.12"/>
          <stop offset="100%" stop-color="#ef4444" stop-opacity="0.02"/>
        </linearGradient>
      </defs>

      <!-- Active Product & Period Display Header -->
      <text x="{pad_left}" y="22" fill="#38bdf8" font-size="13" font-weight="700" font-family="sans-serif">Displaying: {product_name} · Timeline: {period_heading}</text>

      <!-- Background Grid & Ticks -->
      {"".join(y_ticks_svg)}
      {"".join(x_ticks_svg)}

      <!-- Safety Stock Shaded Danger Zone -->
      <rect x="{pad_left}" y="{ss_y:.1f}" width="{chart_w}" height="{max(pad_top + chart_h - ss_y, 0):.1f}" fill="url(#dangerZoneGrad)" />

      <!-- Reorder Point (ROP) Reference Line -->
      <line x1="{pad_left}" y1="{rop_y:.1f}" x2="{width - pad_right}" y2="{rop_y:.1f}" stroke="#38bdf8" stroke-width="2" stroke-dasharray="6,4" />
      <text x="{width - pad_right - 4}" y="{rop_y - 6:.1f}" text-anchor="end" fill="#38bdf8" font-size="11" font-weight="600" font-family="sans-serif">Reorder Point (ROP = {rop})</text>

      <!-- Safety Stock (SS) Reference Line -->
      <line x1="{pad_left}" y1="{ss_y:.1f}" x2="{width - pad_right}" y2="{ss_y:.1f}" stroke="#ef4444" stroke-width="2" stroke-dasharray="5,3" />
      <text x="{width - pad_right - 4}" y="{ss_y - 6:.1f}" text-anchor="end" fill="#ef4444" font-size="11" font-weight="600" font-family="sans-serif">Safety Stock (SS = {ss})</text>

      <!-- Inventory Area Fill -->
      <polygon points="{area_coords}" fill="url(#eoqGradient)" />

      <!-- Inventory Continuous Trajectory Polyline -->
      <polyline fill="none" stroke="#10b981" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" points="{line_coords}" />

      <!-- Y Axis & X Axis Base Lines -->
      <line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + chart_h}" stroke="#64748b" stroke-width="1.5" />
      <line x1="{pad_left}" y1="{pad_top + chart_h}" x2="{width - pad_right}" y2="{pad_top + chart_h}" stroke="#64748b" stroke-width="1.5" />
    </svg>
    """
    return svg_content


def generate_stacked_bar_svg(product_data: dict) -> str:
    """
    Generates a horizontal stacked bar chart visualizing Available, Reserved, and Sold allocations.
    """
    avail = max(int(product_data.get("available_qty", 0)), 0)
    res = max(int(product_data.get("reserved_qty", 0)), 0)
    sold = max(int(product_data.get("sold_qty", 0)), 0)
    total = max(avail + res + sold, 1)

    width = 780
    height = 230
    pad_left = 30
    pad_right = 30
    bar_y = 50
    bar_h = 42
    bar_w = width - pad_left - pad_right  # 720px

    pct_avail = avail / total
    pct_res = res / total
    pct_sold = sold / total

    w_avail = round(pct_avail * bar_w, 1)
    w_res = round(pct_res * bar_w, 1)
    w_sold = round(pct_sold * bar_w, 1)

    diff = bar_w - (w_avail + w_res + w_sold)
    w_avail += diff

    x_avail = pad_left
    x_res = x_avail + w_avail
    x_sold = x_res + w_res

    p_name = product_data.get("name", "All Products (Portfolio)")
    avail_val = float(product_data.get("available_val", 0.0))
    res_val = float(product_data.get("reserved_val", 0.0))
    sold_val = float(product_data.get("sold_val", 0.0))
    total_val = float(product_data.get("total_val", 0.0))

    txt_avail = (
        f"<text x='{x_avail + w_avail/2:.1f}' y='{bar_y + bar_h/2 + 4:.1f}' fill='#ffffff' font-size='12' font-weight='700' text-anchor='middle' font-family='sans-serif'>{avail:,} u</text>"
        if w_avail > 42
        else ""
    )
    txt_res = (
        f"<text x='{x_res + w_res/2:.1f}' y='{bar_y + bar_h/2 + 4:.1f}' fill='#ffffff' font-size='11' font-weight='700' text-anchor='middle' font-family='sans-serif'>{res:,} u</text>"
        if w_res > 38
        else ""
    )
    txt_sold = (
        f"<text x='{x_sold + w_sold/2:.1f}' y='{bar_y + bar_h/2 + 4:.1f}' fill='#ffffff' font-size='12' font-weight='700' text-anchor='middle' font-family='sans-serif'>{sold:,} u</text>"
        if w_sold > 42
        else ""
    )

    svg = f"""
    <svg viewBox="0 0 {width} {height}" class="graph-svg" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
      <!-- Title & Focus -->
      <text x="{pad_left}" y="24" fill="#38bdf8" font-size="13" font-weight="700" font-family="sans-serif">Focus: {p_name}</text>
      <text x="{width - pad_right}" y="24" text-anchor="end" fill="#94a3b8" font-size="11" font-family="sans-serif">Total Lifecycle: {total:,} units · R {total_val:,.2f}</text>

      <!-- Track Background -->
      <rect x="{pad_left}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="8" fill="#1e293b" />

      <!-- Horizontal Stacked Segments -->
      <rect x="{x_avail:.1f}" y="{bar_y}" width="{max(w_avail, 2):.1f}" height="{bar_h}" rx="8" fill="#10b981" />
      <rect x="{x_res:.1f}" y="{bar_y}" width="{max(w_res, 2):.1f}" height="{bar_h}" fill="#f59e0b" />
      <rect x="{x_sold:.1f}" y="{bar_y}" width="{max(w_sold, 2):.1f}" height="{bar_h}" rx="8" fill="#ef4444" />

      <!-- In-Segment Text Labels -->
      {txt_avail}
      {txt_res}
      {txt_sold}

      <!-- Detailed Metrics Callout Cards Below the Horizontal Bar -->
      <g transform="translate({pad_left}, 112)">
        <rect x="0" y="0" width="225" height="54" rx="6" fill="rgba(16, 185, 129, 0.12)" stroke="rgba(16, 185, 129, 0.3)" />
        <circle cx="14" cy="18" r="6" fill="#10b981" />
        <text x="26" y="22" fill="#10b981" font-size="12" font-weight="700" font-family="sans-serif">Available On-Hand</text>
        <text x="14" y="42" fill="#f8fafc" font-size="12" font-weight="600" font-family="sans-serif">{avail:,} units ({pct_avail*100:.1f}%) · R {avail_val:,.2f}</text>
      </g>

      <g transform="translate({pad_left + 247}, 112)">
        <rect x="0" y="0" width="225" height="54" rx="6" fill="rgba(245, 158, 11, 0.12)" stroke="rgba(245, 158, 11, 0.3)" />
        <circle cx="14" cy="18" r="6" fill="#f59e0b" />
        <text x="26" y="22" fill="#f59e0b" font-size="12" font-weight="700" font-family="sans-serif">Reserved for Jobs</text>
        <text x="14" y="42" fill="#f8fafc" font-size="12" font-weight="600" font-family="sans-serif">{res:,} units ({pct_res*100:.1f}%) · R {res_val:,.2f}</text>
      </g>

      <g transform="translate({pad_left + 495}, 112)">
        <rect x="0" y="0" width="225" height="54" rx="6" fill="rgba(239, 68, 68, 0.12)" stroke="rgba(239, 68, 68, 0.3)" />
        <circle cx="14" cy="18" r="6" fill="#ef4444" />
        <text x="26" y="22" fill="#f43f5e" font-size="12" font-weight="700" font-family="sans-serif">Demand Satisfied (Sold)</text>
        <text x="14" y="42" fill="#f8fafc" font-size="12" font-weight="600" font-family="sans-serif">{sold:,} units ({pct_sold*100:.1f}%) · R {sold_val:,.2f}</text>
      </g>

      <!-- Bottom Summary Note -->
      <text x="{pad_left}" y="195" fill="#64748b" font-size="11" font-family="sans-serif">Horizontal valuation and allocation breakdown across active clinical inventory cycles</text>
    </svg>
    """
    return svg


def get_product_eoq_simulation(product_id: int, zoom: str = "month") -> dict:
    """
    Builds daily dates/demands and returns simulation records + SVG markup for a product.
    """
    product = get_products(product_id)
    if not product:
        return {"simulation": [], "svg": generate_eoq_simulation_svg([], 0, 0, zoom=zoom)}

    today = date.today()
    if zoom == "year":
        start_dt = date(today.year, 1, 1)
        end_dt = date(today.year, 12, 31)
    else:
        last_day = calendar.monthrange(today.year, today.month)[1]
        start_dt = date(today.year, today.month, 1)
        end_dt = date(today.year, today.month, last_day)

    total_days = (end_dt - start_dt).days + 1
    dates = [(start_dt + timedelta(days=i)).isoformat() for i in range(total_days)]

    sales_rows = db.query_all(
        """
        SELECT DATE(sold_date) AS sale_day, COALESCE(SUM(sold_qty), 0) AS qty
        FROM sale
        WHERE product_id = %s
          AND DATE(sold_date) BETWEEN %s AND %s
        GROUP BY DATE(sold_date)
        """,
        (product_id, start_dt.isoformat(), end_dt.isoformat()),
    )
    sales_by_day = {str(r["sale_day"]): int(r["qty"] or 0) for r in sales_rows}
    demands = [sales_by_day.get(d, 0) for d in dates]

    sim_data = simulation_eoq(
        starting_inventory=product["current_inventory"],
        dates=dates,
        demands=demands,
        rop=product["rop"],
        eoq=product["eoq"],
        effective_lt=2,
    )
    svg = generate_eoq_simulation_svg(
        sim_data=sim_data,
        rop=product["rop"],
        ss=product["ss"],
        zoom=zoom,
        product_name=product["name"],
    )
    return {"product": product, "simulation": sim_data, "svg": svg}


def get_allocation_breakdown(product_id: int | None = None) -> dict:
    """
    Computes Available, Reserved, and Sold quantities/valuations and returns SVG markup.
    """
    if product_id is not None:
        p = get_products(product_id)
        if not p:
            return {"data": {}, "svg": generate_stacked_bar_svg({})}
        avail = max(int(p.get("current_inventory", 0)), 0)
        sold = max(int(p.get("sold", 0)), 0)
        res = 0
        price = float(p.get("sell_price", p.get("price", 0.0)))
        payload = {
            "name": p["name"],
            "available_qty": avail,
            "reserved_qty": res,
            "sold_qty": sold,
            "available_val": avail * price,
            "reserved_val": res * price,
            "sold_val": sold * price,
            "total_val": (avail + res + sold) * price,
        }
        return {"data": payload, "svg": generate_stacked_bar_svg(payload)}

    products = get_products()
    avail = sum(max(int(p.get("current_inventory", 0)), 0) for p in products)
    sold = sum(max(int(p.get("sold", 0)), 0) for p in products)
    res = 0
    avail_val = sum(
        max(int(p.get("current_inventory", 0)), 0) * float(p.get("sell_price", 0.0))
        for p in products
    )
    sold_val = sum(
        max(int(p.get("sold", 0)), 0) * float(p.get("sell_price", 0.0))
        for p in products
    )
    payload = {
        "name": "All Products (Portfolio)",
        "available_qty": avail,
        "reserved_qty": res,
        "sold_qty": sold,
        "available_val": avail_val,
        "reserved_val": 0.0,
        "sold_val": sold_val,
        "total_val": avail_val + sold_val,
    }
    return {"data": payload, "svg": generate_stacked_bar_svg(payload)}


# =============================================================================
# HELPERS & FORMATTERS
# =============================================================================


def _to_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _format_product_raw(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "supplier_id": int(row["supplier_id"]),
        "name": str(row["name"]),
        "supplier": str(row["supplier"]),
        "sell_price": float(row["sell_price"]),
        "cost_price": float(row["cost_price"]),
        "holding_cost": float(row["hc"]),
        "units_per_package": int(row["units_per_package"]),
        "year_starting_inventory": int(row["starting_inv"]),
        "storage_location": str(row["storage_location"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _format_supplier(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "name": str(row["name"]),
        "from_date": str(row["from_date"]) if row["from_date"] else "",
        "change_reason": str(row["change_reason"] or ""),
        "replaces_supplier_id": (
            int(row["replaces_supplier_id"])
            if row.get("replaces_supplier_id") is not None
            else None
        ),
        "created_at": str(row["created_at"]) if row["created_at"] else "",
        "updated_at": str(row["updated_at"]) if row["updated_at"] else "",
        "contact_email": str(row["contact_email"] or ""),
        "contact_phone": str(row["contact_phone"] or ""),
    }


def _format_sale(row: dict) -> dict:
    return {
        "id": int(row["id"]),
        "product_id": int(row["product_id"]),
        "product_name": str(row["product_name"]),
        "unit_price": float(row["unit_price"]),
        "sale_qty": int(row["sale_qty"]),
        "total_sale_value": float(row["total_sale_value"]),
        "sale_date": str(row["sale_date"]) if row["sale_date"] else "",
        "created_at": str(row["created_at"]) if row["created_at"] else "",
        "updated_at": str(row["updated_at"]) if row["updated_at"] else "",
    }


# =============================================================================
# PRODUCT FUNCTIONS
# =============================================================================

_BASE_PRODUCT_SELECT = """
SELECT
    p.product_id AS id,
    p.supplier_id AS supplier_id,
    p.product_name AS name,
    s.supplier_name AS supplier,
    p.product_price AS sell_price,
    p.supplier_price AS cost_price,
    p.product_holding_cost AS hc,
    p.units_per_package,
    p.year_starting_inventory AS starting_inv,
    p.storage_location,
    p.created_at,
    p.updated_at
FROM product p
JOIN supplier s
    ON p.supplier_id = s.supplier_id
"""


def get_products_raw(product_id=None):
    if product_id == "" or product_id is None:
        rows = db.query_all(_BASE_PRODUCT_SELECT)
        return [_format_product_raw(r) for r in rows]

    row = db.query_one(f"{_BASE_PRODUCT_SELECT} WHERE p.product_id = %s", (product_id,))
    return _format_product_raw(row) if row else None


def get_products(product_id=None):
    single_mode = product_id is not None and product_id != ""
    raw_data = get_products_raw(product_id if single_mode else None)

    if not raw_data:
        return None if single_mode else []

    products_to_process = [raw_data] if single_mode else raw_data
    historical_years = max(int(_get_config_value("HISTORICAL_YEARS", 5)), 1)
    service_level = float(_get_config_value("DEFAULT_SERVICE_LEVEL", 0.95))

    product_filter_sql = "AND product_id = %s" if single_mode else ""
    product_filter_params = (int(product_id),) if single_mode else ()

    abc_sql = """
    SELECT
        s.product_id AS id,
        p.product_price AS price,
        SUM(s.sold_qty) AS demand
    FROM sale s
    JOIN product p
        ON s.product_id = p.product_id
    WHERE s.sold_date >= MAKEDATE(YEAR(CURDATE()) - 1, 1)
      AND s.sold_date < MAKEDATE(YEAR(CURDATE()), 1)
    GROUP BY s.product_id, p.product_price
    """
    abc_rows = db.query_all(abc_sql)
    abc_lookup = {
        int(item["id"]): item["tier"] for item in calculate_abc(abc_rows)
    }

    eoq_sql = f"""
    WITH yearly_sales AS (
        SELECT
            product_id,
            YEAR(sold_date) AS sales_year,
            SUM(sold_qty) AS yearly_qty
        FROM sale
        WHERE sold_date >= MAKEDATE(YEAR(CURDATE()) - %s, 1)
          AND sold_date < MAKEDATE(YEAR(CURDATE()), 1)
          {product_filter_sql}
        GROUP BY product_id, YEAR(sold_date)
    )
    SELECT
        product_id,
        COALESCE(SUM(yearly_qty), 0) / NULLIF(%s, 0) AS annual_demand
    FROM yearly_sales
    GROUP BY product_id
    """
    eoq_rows = db.query_all(
        eoq_sql, (historical_years, *product_filter_params, historical_years)
    )
    eoq_lookup = {
        int(r["product_id"]): float(r["annual_demand"] or 0.0) for r in eoq_rows
    }

    lt_filter_sql = "AND poi.product_id = %s" if single_mode else ""
    lt_sql = f"""
    WITH filtered_po AS (
        SELECT DISTINCT
            po.order_id,
            poi.product_id,
            po.order_date
        FROM purchase_order po
        JOIN purchase_order_item poi
            ON po.order_id = poi.order_id
        WHERE po.order_status = 'Received'
          AND po.order_date >= MAKEDATE(YEAR(CURDATE()) - %s, 1)
          AND po.order_date < MAKEDATE(YEAR(CURDATE()), 1)
          {lt_filter_sql}
    ),
    receipt_dates AS (
        SELECT
            iu.order_id,
            MAX(DATE(iu.update_date)) AS receipt_date
        FROM inventory_update iu
        JOIN filtered_po fpo
            ON iu.order_id = fpo.order_id
        GROUP BY iu.order_id
    )
    SELECT
        fpo.product_id,
        AVG(DATEDIFF(rd.receipt_date, fpo.order_date)) AS avg_lt,
        COALESCE(STDDEV_SAMP(DATEDIFF(rd.receipt_date, fpo.order_date)), 0) AS std_lt
    FROM filtered_po fpo
    JOIN receipt_dates rd
        ON fpo.order_id = rd.order_id
    WHERE rd.receipt_date >= fpo.order_date
    GROUP BY fpo.product_id
    """
    lt_rows = db.query_all(lt_sql, (historical_years, *product_filter_params))
    lt_lookup = {int(r["product_id"]): r for r in lt_rows}

    demand_sql = f"""
    WITH daily_sales AS (
        SELECT
            product_id,
            DATE(sold_date) AS sale_day,
            SUM(sold_qty) AS daily_qty
        FROM sale
        WHERE sold_date >= MAKEDATE(YEAR(CURDATE()) - %s, 1)
          AND sold_date < MAKEDATE(YEAR(CURDATE()), 1)
          {product_filter_sql}
        GROUP BY product_id, DATE(sold_date)
    )
    SELECT
        product_id,
        COALESCE(AVG(daily_qty), 0) AS avg_daily_demand,
        COALESCE(STDDEV_SAMP(daily_qty), 0) AS std_d
    FROM daily_sales
    GROUP BY product_id
    """
    demand_rows = db.query_all(demand_sql, (historical_years, *product_filter_params))
    demand_lookup = {int(r["product_id"]): r for r in demand_rows}

    inv_product_where = "WHERE p.product_id = %s" if single_mode else ""
    inv_sql = f"""
    WITH sales_agg AS (
        SELECT
            product_id AS id,
            SUM(sold_qty) AS sales
        FROM sale
        WHERE sold_date >= MAKEDATE(YEAR(CURDATE()), 1)
          {product_filter_sql}
        GROUP BY product_id
    ),
    updates_agg AS (
        SELECT
            iui.product_id AS id,
            SUM(iui.update_amount) AS update_total
        FROM inventory_update_item iui
        JOIN inventory_update iu
            ON iu.update_id = iui.update_id
        WHERE iu.update_date >= MAKEDATE(YEAR(CURDATE()), 1)
          {"AND iui.product_id = %s" if single_mode else ""}
        GROUP BY iui.product_id
    )
    SELECT
        p.product_id AS id,
        (
            p.year_starting_inventory
            - COALESCE(sa.sales, 0)
            + COALESCE(ua.update_total, 0)
        ) AS current_inventory
    FROM product p
    LEFT JOIN sales_agg sa
        ON sa.id = p.product_id
    LEFT JOIN updates_agg ua
        ON ua.id = p.product_id
    {inv_product_where}
    """
    inv_params = (
        (*product_filter_params, *product_filter_params, *product_filter_params)
        if single_mode
        else ()
    )
    inv_rows = db.query_all(inv_sql, inv_params)
    inv_lookup = {
        int(r["id"]): int(r["current_inventory"] or 0) for r in inv_rows
    }

    month_sold_sql = f"""
    SELECT
        product_id AS id,
        COALESCE(SUM(sold_qty), 0) AS sold
    FROM sale
    WHERE sold_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
      AND sold_date < DATE_FORMAT(CURDATE(), '%%Y-%%m-01') + INTERVAL 1 MONTH
      {product_filter_sql}
    GROUP BY product_id
    """
    month_rows = db.query_all(month_sold_sql, product_filter_params)
    month_lookup = {int(r["id"]): int(r["sold"] or 0) for r in month_rows}

    output_products = []
    for p in products_to_process:
        p_id = p["id"]

        annual_demand = eoq_lookup.get(p_id, 0.0)
        eoq = calculate_eoq(
            annual_demand,
            p["holding_cost"],
            p["cost_price"],
            p["units_per_package"],
        )

        lt_info = lt_lookup.get(p_id)
        demand_info = demand_lookup.get(p_id)

        lt = float(lt_info["avg_lt"] or 0.0) if lt_info else 0.0
        std_lt = float(lt_info["std_lt"] or 0.0) if lt_info else 0.0
        daily_demand = (
            float(demand_info["avg_daily_demand"] or 0.0) if demand_info else 0.0
        )
        std_d = float(demand_info["std_d"] or 0.0) if demand_info else 0.0

        ss = calculate_ss(service_level, std_lt, std_d, lt, daily_demand)

        if daily_demand > 0 and eoq > 0:
            cycle_time = eoq / daily_demand
            effective_lt = lt % cycle_time
            rop = calculate_rop(daily_demand, effective_lt, ss)
        else:
            rop = ss

        output_products.append({
            "id": p_id,
            "supplier_id": p["supplier_id"],
            "name": p["name"],
            "price": p["sell_price"],
            "sell_price": p["sell_price"],
            "cost_price": p["cost_price"],
            "holding_cost": p["holding_cost"],
            "year_starting_inventory": p["year_starting_inventory"],
            "storage_location": p["storage_location"],
            "eoq": int(eoq),
            "ss": int(ss),
            "rop": int(rop),
            "class": abc_lookup.get(p_id, "C"),
            "current_inventory": inv_lookup.get(p_id, 0),
            "sold": month_lookup.get(p_id, 0),
        })

    return output_products[0] if single_mode else output_products


def insert_product(
    name: str = "",
    price: float = 0.0,
    holding_cost: float = 0.0,
    starting_inventory: int = 0,
    storage_location: str = "",
    supplier_id: int | None = None,
    supplier_price: float = 0.0,
    units_per_package: int = 1,
):
    sql = """
    INSERT INTO product (
        supplier_id,
        product_name,
        product_price,
        supplier_price,
        units_per_package,
        product_holding_cost,
        year_starting_inventory,
        storage_location
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    product_id = db.execute(
        sql,
        (
            supplier_id,
            name,
            price,
            supplier_price,
            max(int(units_per_package), 1),
            holding_cost,
            starting_inventory,
            storage_location,
        ),
    )
    db.close_db()
    return product_id


def update_product(
    name: str,
    price: float,
    holding_cost: float,
    starting_inventory: int,
    product_id: int,
    storage_location: str = "",
    supplier_id: int | None = None,
    supplier_price: float | None = None,
    units_per_package: int | None = None,
):
    assignments = [
        "product_name = %s",
        "product_price = %s",
        "product_holding_cost = %s",
        "year_starting_inventory = %s",
        "storage_location = %s",
    ]
    params: list = [
        name,
        price,
        holding_cost,
        starting_inventory,
        storage_location,
    ]

    if supplier_id is not None:
        assignments.append("supplier_id = %s")
        params.append(supplier_id)
    if supplier_price is not None:
        assignments.append("supplier_price = %s")
        params.append(supplier_price)
    if units_per_package is not None:
        assignments.append("units_per_package = %s")
        params.append(max(int(units_per_package), 1))

    params.append(product_id)
    sql = f"UPDATE product SET {', '.join(assignments)} WHERE product_id = %s"
    rows_affected = db.execute(sql, tuple(params))
    db.close_db()
    return rows_affected


def delete_product(product_id: int):
    rows_affected = db.execute("DELETE FROM product WHERE product_id = %s", (product_id,))
    db.close_db()
    return rows_affected


# =============================================================================
# SUPPLIER FUNCTIONS
# =============================================================================

_BASE_SUPPLIER_SELECT = """
SELECT
    s.supplier_id AS id,
    s.supplier_name AS name,
    s.supplier_from_date AS from_date,
    s.reason_for_changing_supplier AS change_reason,
    s.replaces_supplier_id AS replaces_supplier_id,
    s.created_at AS created_at,
    s.updated_at AS updated_at,
    s.contact_email AS contact_email,
    s.contact_phone AS contact_phone,
    p.product_id AS product_id,
    p.product_name AS product_name,
    p.supplier_price AS supplier_price,
    p.units_per_package AS units_per_package
FROM supplier s
LEFT JOIN product p ON s.supplier_id = p.supplier_id
WHERE NOT EXISTS (
    SELECT 1
    FROM supplier replaced
    WHERE replaced.replaces_supplier_id = s.supplier_id
)
"""

def get_suppliers(supplier_id=None):
    is_single = supplier_id != "" and supplier_id is not None

    if is_single:
        sql = f"{_BASE_SUPPLIER_SELECT} AND s.supplier_id = %s ORDER BY p.product_name ASC"
        rows = db.query_all(sql, (supplier_id,))   
    else:
        sql = f"{_BASE_SUPPLIER_SELECT} ORDER BY s.supplier_id ASC, p.product_name ASC"
        rows = db.query_all(sql)
    db.close_db()

    if not rows:
        return None if is_single else []

    suppliers_map = {}
    for r in rows:
        supplier_id = int(r["id"])
        if supplier_id not in suppliers_map:
            suppliers_map[supplier_id] = {
                **_format_supplier(r),
                "products": []
            }
        if r["product_id"] is not None:
            suppliers_map[supplier_id]["products"].append({
                "product_id": int(r["product_id"]),
                "product_name": str(r["product_name"]),
                "supplier_price": float(r["supplier_price"]),
                "units_per_package": int(r["units_per_package"]),
            })

    result = list(suppliers_map.values())
    return result[0] if is_single else result

def get_products_supplier(supplier_id=None):
    if supplier_id == "" or supplier_id is None:
        return None

    supplier = get_suppliers(supplier_id)
    if not supplier:
        return None

    rows = db.query_all(
        "SELECT product_id FROM product WHERE supplier_id = %s", (supplier_id,)
    )
    db.close_db()

    products_data = []
    for row in rows:
        product = get_products(int(row["product_id"]))
        if product:
            products_data.append(product)

    return {
        "supplier_data": supplier,
        "products_data": products_data,
    }


def insert_supplier(
    name: str = "",
    from_date: str | None = None,
    change_reason: str = "",
    contact_email: str = "",
    contact_phone: str = "",
    replaces_supplier_id: int | None = None,
):
    sql = """
    INSERT INTO supplier (
        supplier_name,
        supplier_from_date,
        reason_for_changing_supplier,
        replaces_supplier_id,
        contact_email,
        contact_phone
    )
    VALUES (%s, COALESCE(%s, CURDATE()), %s, %s, %s, %s)
    """
    new_id = db.execute(
        sql,
        (
            name,
            from_date or None,
            change_reason,
            replaces_supplier_id,
            contact_email,
            contact_phone,
        ),
    )
    db.close_db()
    return new_id


def update_supplier(
    name: str,
    from_date: str,
    change_reason: str,
    supplier_id: int,
    contact_email: str = "",
    contact_phone: str = "",
    replaces_supplier_id: int | None = None,
):
    sql = """
    UPDATE supplier
    SET
        supplier_name = %s,
        supplier_from_date = %s,
        reason_for_changing_supplier = %s,
        replaces_supplier_id = %s,
        contact_email = %s,
        contact_phone = %s
    WHERE supplier_id = %s
    """
    rows_affected = db.execute(
        sql,
        (
            name,
            from_date,
            change_reason,
            replaces_supplier_id,
            contact_email,
            contact_phone,
            supplier_id,
        ),
    )
    db.close_db()
    return rows_affected


def delete_supplier(supplier_id: int):
    rows_affected = db.execute(
        "DELETE FROM supplier WHERE supplier_id = %s", (supplier_id,)
    )
    db.close_db()
    return rows_affected


# =============================================================================
# SALE FUNCTIONS
# =============================================================================

_BASE_SALE_SELECT = """
SELECT
    s.sale_id AS id,
    s.product_id AS product_id,
    p.product_name AS product_name,
    p.product_price AS unit_price,
    s.sold_qty AS sale_qty,
    (s.sold_qty * p.product_price) AS total_sale_value,
    s.sold_date AS sale_date,
    s.created_at AS created_at,
    s.updated_at AS updated_at
FROM sale s
JOIN product p
    ON s.product_id = p.product_id
"""


def get_sales(sale_id=None):
    if sale_id == "" or sale_id is None:
        rows = db.query_all(
            f"{_BASE_SALE_SELECT} ORDER BY s.sold_date DESC, s.sale_id DESC"
        )
        db.close_db()
        return [_format_sale(r) for r in rows]

    row = db.query_one(f"{_BASE_SALE_SELECT} WHERE s.sale_id = %s", (sale_id,))
    db.close_db()
    return _format_sale(row) if row else None


def insert_sale(product_id: int, sale_qty: int, sale_date: str):
    sql = """
    INSERT INTO sale (product_id, sold_qty, sold_date)
    VALUES (%s, %s, %s)
    """
    new_id = db.execute(sql, (product_id, sale_qty, sale_date))
    db.close_db()
    return new_id


def update_sale(product_id: int, sale_qty: int, sale_date: str, sale_id: int):
    sql = """
    UPDATE sale
    SET product_id = %s, sold_qty = %s, sold_date = %s
    WHERE sale_id = %s
    """
    rows_affected = db.execute(sql, (product_id, sale_qty, sale_date, sale_id))
    db.close_db()
    return rows_affected


def delete_sale(sale_id: int):
    rows_affected = db.execute("DELETE FROM sale WHERE sale_id = %s", (sale_id,))
    db.close_db()
    return rows_affected