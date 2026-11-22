from datetime import datetime
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
    s.contact_phone AS contact_phone
FROM supplier s
WHERE NOT EXISTS (
    SELECT 1
    FROM supplier replaced
    WHERE replaced.replaces_supplier_id = s.supplier_id
)
"""


def get_suppliers(supplier_id=None):
    if supplier_id == "" or supplier_id is None:
        rows = db.query_all(_BASE_SUPPLIER_SELECT)
        db.close_db()
        return [_format_supplier(r) for r in rows]

    row = db.query_one(
        f"{_BASE_SUPPLIER_SELECT} AND s.supplier_id = %s", (supplier_id,)
    )
    db.close_db()
    return _format_supplier(row) if row else None


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
## Getting supplier data (with linked products)
def get_suppliers(supplier_id=None):
    sql = """
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
        ps.product_supplier_id AS product_supplier_id,
        p.product_id AS product_id,
        p.product_name AS product_name,
        ps.supplier_price AS supplier_price,
        ps.units_per_package AS units_per_package
     FROM supplier s
    LEFT JOIN product_supplier ps ON s.supplier_id = ps.supplier_id
    LEFT JOIN product p ON ps.product_id = p.product_id
    """
    is_single = supplier_id != "" and supplier_id is not None

    if is_single:
        sql += " WHERE s.supplier_id = %s ORDER BY p.product_name ASC"
        suppliers = db.query_all(sql, (supplier_id,))
    else:
        sql += " ORDER BY s.supplier_id ASC, p.product_name ASC"
        suppliers = db.query_all(sql)
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