from datetime import datetime
import math
import statistics
import db
from flask import current_app
from config import get_config

# =============================================================================
# SUPPLY CHAIN FORMULAS
# =============================================================================

def _get_config_value(key: str, default=None):
    if current_app:
        return current_app.config.get(key, default)
    return getattr(get_config(), key, default)

## Economic Order Quantity
def calculate_eoq(annual_demand: float, holding_cost: float, setup_cost: float, conversion: int) -> int:
    """
    Calculates the Economic Order Quantity (EOQ) using the classical Wilson lot-size formula.

    Formula:
        Q = sqrt((2 * D * S) / H)
        where:
            D = Annual demand in physical units
            S = Fixed setup / ordering cost per procurement batch
            H = Annual inventory holding cost per unit per year

    Inputs:
        annual_demand (float): Total expected or historical units consumed per year (D).
        holding_cost (float): Holding / carrying cost per unit per annum (H).
        setup_cost (float): Order placement, logistics, and processing cost per order (S).
        conversion (int): Amount of units in an ordered box.

    Returns:
        int: The cost-minimizing order batch quantity (Q), rounded up to the nearest box quantity.

    Assumptions / Edge Cases:
        - If holding_cost <= 0, annual_demand <= 0, or setup_cost <= 0, returns 0 to
          prevent ZeroDivisionError and domain errors under negative square roots.
        - Demand rate is assumed deterministic and uniform across the planning horizon.
    """
    if holding_cost <= 0 or annual_demand <= 0 or setup_cost <= 0:
        return 0
    conversion = max(int(conversion), 1)
    raw_eoq = math.sqrt(
        (2.0 * float(annual_demand) * float(setup_cost)) / float(holding_cost)
    )
    box_eoq = math.ceil(raw_eoq / conversion) * conversion
    return int(round(box_eoq))


## Safety Stock
def calculate_ss(service_level: float,std_lt: float | None,std_demand: float | None,lt: float | int | None,avg_daily_demand: float | None = 0.0,) -> int:
    """
    Computes required Safety Stock (SS) under stochastic demand and supplier lead time.

    Formula:
        SS = z * sqrt(LT * sigma_d^2 + d_bar^2 * sigma_LT^2)
        where:
            z = Inverse cumulative standard normal distribution value for service level
            LT = Mean vendor lead time in days (clamped to >= 1)
            sigma_d = Standard deviation of daily demand (units/day)
            d_bar = Mean daily demand (units/day)
            sigma_LT = Standard deviation of supplier lead time in days

    Inputs:
        service_level (float): Target cycle service level (e.g. 0.95 for 95% protection).
        std_lt (float): Standard deviation of replenishment lead time.
        std_demand (float): Standard deviation of daily units consumed/sold.
        lt (int): Average lead time in calendar days.
        avg_daily_demand (float): Average daily demand in units.

    Returns:
        int: Buffer stock units required to prevent stockouts during replenishment lead time.

    Assumptions / Edge Cases:
        Uses Python standard library statistics.NormalDist(0, 1).inv_cdf() for exact z score.
        Clamps minimum effective lead time to 1 day to prevent zero multiplication.
        Assumes clinical demand and vendor delivery lead times follow independent normal distributions.
    """
    effective_lt = max(float(lt) if lt is not None else 1.0, 1.0)
    sigma_d = max(float(std_demand) if std_demand is not None else 0.0, 0.0)
    sigma_lt = max(float(std_lt) if std_lt is not None else 0.0, 0.0)
    d_bar = max(float(avg_daily_demand) if avg_daily_demand is not None else 0.0, 0.0)

    variance_lead_time_demand = (effective_lt * (sigma_d**2)) + ((d_bar**2) * (sigma_lt**2))
    std_lead_time_demand = math.sqrt(variance_lead_time_demand)

    clamped_sl = min(max(float(service_level), 0.50), 0.999)
    try:
        z = statistics.NormalDist(mu=0.0, sigma=1.0).inv_cdf(clamped_sl)
    except Exception:
        z = 1.64485  # Fallback for 95% cycle service level

    ss_value = z * std_lead_time_demand
    return int(round(ss_value))


## Re-order Point
def calculate_rop(daily_demand: float, effective_lt: float, safety_stock: int) -> int:
    """
    Calculates the Reorder Point (ROP) inventory threshold that triggers replenishment.

    Formula:
        ROP = (d_bar * L_eff) + SS
        where:
            d_bar = Average daily demand rate
            L_eff = Effective lead time modulus (lead time within the replenishment cycle)
            SS = Safety stock buffer units

    Inputs:
        daily_demand (float): Mean units consumed/sold per calendar day (d_bar).
        effective_lt (float): Lead time modulo cycle time (L_eff).
        safety_stock (int): Buffer stock units (SS).

    Returns:
        int: Total inventory units at or below which a purchase order must be placed.

    Assumptions / Edge Cases:
        - When on-hand inventory drops to or below ROP, the system triggers restock.
        - If lead time exceeds cycle time, effective lead time accounts for orders already in transit.
    """
    raw_rop = (float(daily_demand) * float(effective_lt)) + float(safety_stock)
    return int(round(raw_rop))


## ABC Classification
def calculate_abc(products_list: list) -> list:
    """
    Calculate the Classification for each product.

    Inputs:
        products_list (list): List of product dictionary objects, each containing:
            - 'product_id' (int): Primary product identifier
            - 'price' (float): Clinical unit selling price
            - 'demand' (int): Cumulative historical 5-year consumption

    Returns:
        list: Sorted product list enriched with 'value', 'cum_pct', and 'tier'.
    """
    A = float(_get_config_value("ABC_A_THRESHOLD", 80.0))
    B = float(_get_config_value("ABC_B_THRESHOLD", 95.0))
    def assign_tier(cum_pct: float) -> str:
        if cum_pct <= A:
            return "A"
        elif cum_pct <= B:
            return "B"
        else:
            return "C"

    if not products_list:
        return []

    for p in products_list:
        p["value"] = float(p["demand"]) * float(p["price"])

    skus_sorted = sorted(
        products_list, key=lambda item: item["value"], reverse=True
    )

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
# JSON FUNCTIONS
# =============================================================================


def _to_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))

# PRODUCT FUNCTIONS
## Getting raw product data
def get_products_raw(product_id=None):
    if product_id == "" or product_id is None:
        sql = """
        SELECT
            p.product_id AS id,
            p.product_name AS name,
            p.product_price AS price,
            p.year_starting_inventory AS starting_inv,
            p.product_holding_cost AS hc,
            p.created_at,
            p.updated_at
        FROM product p
        """
        products = db.query_all(sql)
        formatted_products = []
        for p in products:
            formatted_products.append({
                "id": int(p["id"]),
                "name": str(p["name"]),
                "price": float(p["price"]),
                "year_starting_inventory": int(p["starting_inv"]),
                "holding_cost": float(p["hc"]),
                "created_at": _to_datetime(p["created_at"]),
                "updated_at": _to_datetime(p["updated_at"]),
            })
        return formatted_products
    else:
        sql = """
        SELECT
            p.product_id AS id,
            p.product_name AS name,
            p.product_price AS price,
            p.year_starting_inventory AS starting_inv,
            p.product_holding_cost AS hc,
            p.created_at,
            p.updated_at
        FROM product p
        WHERE p.product_id = %s
        """
        p = db.query_one(sql, (product_id,))
        if not p:
            return None
        return {
            "id": int(p["id"]),
            "name": str(p["name"]),
            "price": float(p["price"]),
            "year_starting_inventory": int(p["starting_inv"]),
            "holding_cost": float(p["hc"]),
            "created_at": _to_datetime(p["created_at"]),
            "updated_at": _to_datetime(p["updated_at"]),
        }


## Getting relevant product data
def get_products(product_id=None):
    r_product = get_products_raw(product_id)
    historical_years = max(int(_get_config_value("HISTORICAL_YEARS", 5)), 1)
    if not r_product:
        return None if product_id is not None else []

    products_to_process = (
        [r_product] if product_id is not None else r_product
    )
    output_product = []

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
    product_list = db.query_all(abc_sql)
    abc_data = calculate_abc(product_list)
    abc_lookup = {int(item["id"]): item["tier"] for item in abc_data}

    eoq_sql = """
    WITH yearly_sales AS (
        SELECT
            product_id,
            YEAR(sold_date) AS sales_year,
            SUM(sold_qty) AS yearly_qty
        FROM sale
        WHERE sold_date >= MAKEDATE(YEAR(CURDATE()) - %s, 1)
          AND sold_date < MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY
            product_id,
            YEAR(sold_date)
    ),
    avg_yearly_sales AS (
        SELECT
            product_id,
            SUM(yearly_qty) / %s AS avg_annual_sold_qty
        FROM yearly_sales
        GROUP BY product_id
    ),
    current_setup AS (
        SELECT
            product_id,
            units_per_package,
            supplier_price,
            ROW_NUMBER() OVER (
                PARTITION BY product_id
                ORDER BY created_at DESC, product_supplier_id DESC
            ) AS rn
        FROM product_supplier
    )
    SELECT
        COALESCE(ays.avg_annual_sold_qty, 0) AS annual_demand,
        COALESCE(cs.supplier_price, 0) AS setup_cost,
        COALESCE(cs.units_per_package, 1) AS box_conversion
    FROM product p
    LEFT JOIN avg_yearly_sales ays
        ON p.product_id = ays.product_id
    LEFT JOIN current_setup cs
        ON p.product_id = cs.product_id
       AND cs.rn = 1
    WHERE p.product_id = %s;
    """

    ss_sql = """
    WITH target_product AS (
        SELECT %s AS product_id
    ),
    filtered_po AS (
        SELECT
            po.order_id,
            po.order_date
        FROM purchase_order po
        JOIN purchase_order_item poi
            ON po.order_id = poi.order_id
        CROSS JOIN target_product tp
        WHERE po.order_status = 'Received'
          AND poi.product_id = tp.product_id
          AND po.order_date >= MAKEDATE(YEAR(CURDATE()) - %s, 1)
          AND po.order_date < MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY po.order_id, po.order_date
    ),
    receipt_dates AS (
        SELECT
            order_id,
            MAX(DATE(update_date)) AS receipt_date
        FROM inventory_update
        WHERE order_id IS NOT NULL
        GROUP BY order_id
    ),
    lead_time_metrics AS (
        SELECT
            AVG(DATEDIFF(rd.receipt_date, fpo.order_date)) AS avg_lt,
            STDDEV_SAMP(DATEDIFF(rd.receipt_date, fpo.order_date)) AS std_lt
        FROM filtered_po fpo
        JOIN receipt_dates rd
            ON fpo.order_id = rd.order_id
        WHERE rd.receipt_date >= fpo.order_date
    ),
    daily_sales AS (
        SELECT
            DATE(s.sold_date) AS sale_day,
            SUM(s.sold_qty) AS daily_qty
        FROM sale s
        CROSS JOIN target_product tp
        WHERE s.product_id = tp.product_id
          AND s.sold_date >= MAKEDATE(YEAR(CURDATE()) - %s, 1)
          AND s.sold_date < MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY DATE(s.sold_date)
    ),
    demand_metrics AS (
        SELECT
            AVG(daily_qty) AS avg_daily_demand,
            STDDEV_SAMP(daily_qty) AS std_d
        FROM daily_sales
    )
    SELECT
        tp.product_id AS id,
        lt.avg_lt,
        lt.std_lt,
        dm.avg_daily_demand,
        dm.std_d
    FROM target_product tp
    CROSS JOIN lead_time_metrics lt
    CROSS JOIN demand_metrics dm;
    """

    current_inv_sql = """
    WITH sales_agg AS (
        SELECT
            s.product_id AS id,
            SUM(s.sold_qty) AS sales
        FROM sale s
        WHERE s.sold_date >= MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY s.product_id
    ),
    matching_jobs AS (
        SELECT DISTINCT
            ji.job_id
        FROM job_instance ji
        WHERE ji.status != 'Cancelled'
          AND ji.operation_date >= MAKEDATE(YEAR(CURDATE()), 1)
    ),
    consumables_agg AS (
        SELECT
            jc.product_id AS id,
            SUM(jc.qty_of_product_used) AS used
        FROM job_consumables jc
        JOIN matching_jobs mj
            ON mj.job_id = jc.job_id
        GROUP BY jc.product_id
    ),
    updates_agg AS (
        SELECT
            iui.product_id AS id,
            SUM(iui.update_amount) AS update_total
        FROM inventory_update_item iui
        JOIN inventory_update iu
            ON iu.update_id = iui.update_id
        WHERE iu.update_date >= MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY iui.product_id
    )
    SELECT
        p.product_id AS id,
        (
            p.year_starting_inventory
            - COALESCE(sa.sales, 0)
            - COALESCE(ca.used, 0)
            + COALESCE(ua.update_total, 0)
        ) AS current_inventory
    FROM product p
    LEFT JOIN sales_agg sa
        ON sa.id = p.product_id
    LEFT JOIN consumables_agg ca
        ON ca.id = p.product_id
    LEFT JOIN updates_agg ua
        ON ua.id = p.product_id
    WHERE p.product_id = %s;
    """
    month_sold_sql = """
    SELECT 
        s.product_id AS id, 
        SUM(s.sold_qty) AS sold 
    FROM sale s 
    WHERE s.sold_date >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
        AND s.sold_date < DATE_FORMAT(CURDATE(), '%%Y-%%m-01') + INTERVAL 1 MONTH
        AND s.product_id = %s;
    """

    for p in products_to_process:
        p_id = p["id"]
        data_eoq = db.query_one(eoq_sql, (historical_years,historical_years,p_id,))
        data_ss = db.query_one(ss_sql, (p_id,historical_years,historical_years,))
        data_cur_inv = db.query_one(current_inv_sql, (p_id,))
        data_sold = db.query_one(month_sold_sql, (p_id,))

        if data_eoq:
            annual_demand = float(data_eoq["annual_demand"] or 0)
            setup_cost = float(data_eoq["setup_cost"] or 0)
            box_conversion = max(int(data_eoq["box_conversion"] or 1), 1)
            eoq = calculate_eoq(
                annual_demand, p["holding_cost"], setup_cost, box_conversion
            )
        else:
            eoq = 0

        if data_ss:
            service_level = float(_get_config_value("DEFAULT_SERVICE_LEVEL", 0.95))
            std_lt = float(data_ss["std_lt"] or 0)
            std_d = float(data_ss["std_d"] or 0)
            lt = float(data_ss["avg_lt"] or 0)
            daily_demand = float(data_ss["avg_daily_demand"] or 0)
            ss = calculate_ss(service_level, std_lt, std_d, lt, daily_demand)
        else:
            lt = 0.0
            ss = 0
            daily_demand = 0.0

        if daily_demand > 0 and eoq > 0:
            t = eoq / daily_demand
            effective_lt = lt % t
            rop = calculate_rop(daily_demand, effective_lt, ss)
        else:
            rop = ss

        p_class = abc_lookup.get(p_id, "C")

        if data_cur_inv:
            current_inv = int(data_cur_inv["current_inventory"])
        else:
            current_inv = 0

        if data_sold:
            sold = int(data_sold["sold"])
        else:
            sold=0

        output_product.append({
            "id": int(p["id"]),
            "name": str(p["name"]),
            "price": float(p["price"]),
            "holding_cost": float(p["holding_cost"]),
            "eoq": int(eoq),
            "ss": int(ss),
            "rop": int(rop),
            "class": str(p_class),
            "current_inventory": int(current_inv),
            "sold":int(sold),
        })

    return output_product[0] if product_id is not None else output_product


## Creating a product
def insert_product(
    name: str = "",
    price: float = 0.0,
    holding_cost: float = 0.0,
    starting_inventory: int = 0,
):
    sql = """
    INSERT INTO product (product_name, product_price, product_holding_cost, year_starting_inventory)
    VALUES (%s, %s, %s, %s)
    """
    product_id = db.execute(sql, (name, price, holding_cost, starting_inventory))
    db.close_db()
    return product_id


## Editing product
def update_product(
    name: str,
    price: float,
    holding_cost: float,
    starting_inventory: int,
    product_id: int,
):
    sql = """
    UPDATE product
    SET product_name = %s, product_price = %s, product_holding_cost = %s, year_starting_inventory = %s
    WHERE product_id = %s
    """
    rows_affected = db.execute(
        sql, (name, price, holding_cost, starting_inventory, product_id)
    )
    db.close_db()
    return rows_affected


## Deleting product
def delete_product(product_id: int):
    sql = """
    DELETE FROM product WHERE product_id = %s
    """
    rows_affected = db.execute(sql, (product_id,))
    db.close_db()
    return rows_affected

## SUPPLIER FUNCTIONS
## Getting supplier data
def get_suppliers(supplier_id=None):
    if supplier_id == '' or supplier_id is None:
        sql = """
        SELECT 
            s.supplier_id AS id,
            s.supplier_name AS name,
            s.supplier_from_date AS from_date,   
            s.reason_for_changing_supplier AS change_reason,
            s.created_at AS created_at,
            s.updated_at AS updated_at,
            s.contact_email AS contact_email,
            s.contact_phone AS contact_phone
        FROM supplier s
        """
        suppliers = db.query_all(sql)
        db.close_db()
        formatted_suppliers = []
        for s in suppliers:
            formatted_suppliers.append({
                'id': int(s['id']),
                'name': str(s['name']),
                'from_date': str(s['from_date']) if s['from_date'] else '',
                'change_reason': str(s['change_reason'] or ''),
                'created_at': str(s['created_at']) if s['created_at'] else '',
                'updated_at': str(s['updated_at']) if s['updated_at'] else '',
                'contact_email': str(s['contact_email'] or ''),
                'contact_phone': str(s['contact_phone'] or '')
            })
        return formatted_suppliers
    else:
        sql = """
        SELECT 
            s.supplier_id AS id,
            s.supplier_name AS name,
            s.supplier_from_date AS from_date,   
            s.reason_for_changing_supplier AS change_reason,
            s.created_at AS created_at,
            s.updated_at AS updated_at,
            s.contact_email AS contact_email,
            s.contact_phone AS contact_phone
        FROM supplier s
        WHERE s.supplier_id = %s
        """
        s = db.query_one(sql, (supplier_id,))
        db.close_db()
        if not s:
            return None
        return {
            'id': int(s['id']),
            'name': str(s['name']),
            'from_date': str(s['from_date']) if s['from_date'] else '',
            'change_reason': str(s['change_reason'] or ''),
            'created_at': str(s['created_at']) if s['created_at'] else '',
            'updated_at': str(s['updated_at']) if s['updated_at'] else '',
            'contact_email': str(s['contact_email'] or ''),
            'contact_phone': str(s['contact_phone'] or '')
        }

## Getting products for supplier
def get_products_supplier(supplier_id=None):
    supplier = get_suppliers(supplier_id)
    if not supplier:
        return None
    
    sql = """
    SELECT ps.supplier_id, ps.product_id
    FROM product_supplier ps
    WHERE ps.supplier_id = %s
    """
    products= db.query_all(sql, (supplier_id,))
    products_dict = []
    for p in products:
        product = get_products(int(p['product_id']))
        if product:
            products_dict.append(product)
    return{
        'supplier_data':supplier,
        'products_data':products_dict
    }

## Creating a supplier
def insert_supplier(
        name: str = '', 
        from_date: str = '', 
        change_reason: str = '', 
        contact_email: str = '', 
        contact_phone: str = '',
    ):
    sql = """
    INSERT INTO supplier (supplier_name, supplier_from_date, reason_for_changing_supplier, created_at, updated_at, contact_email, contact_phone)
    VALUES (%s, %s, %s, NOW(), NOW(), %s, %s)
    """
    new_id = db.execute(sql, (name, from_date, change_reason, contact_email, contact_phone))
    db.close_db()
    return new_id


## Editing a supplier
def update_supplier(
        name: str, 
        from_date: str, 
        change_reason: str, 
        supplier_id: int, 
        contact_email: str = '', 
        contact_phone: str = ''
    ):
    sql = """
    UPDATE supplier
    SET supplier_name = %s, supplier_from_date = %s, reason_for_changing_supplier = %s, contact_email = %s, contact_phone = %s, updated_at = NOW()
    WHERE supplier_id = %s
    """
    rows_affected = db.execute(sql, (name, from_date, change_reason, contact_email, contact_phone, supplier_id))
    db.close_db()
    return rows_affected


## Deleting a supplier
def delete_supplier(supplier_id: int):
    sql = """
    DELETE FROM supplier WHERE supplier_id = %s
    """
    rows_affected = db.execute(sql, (supplier_id,))
    db.close_db()
    return rows_affected



## SALE FUNCTIONS
## Getting sale data
def get_sales(sale_id=None):
    if sale_id == '' or sale_id is None:
        sql = """
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
        JOIN product p ON s.product_id = p.product_id
        ORDER BY s.sold_date DESC, s.sale_id DESC
        """
        sales = db.query_all(sql)
        db.close_db()
        formatted_sales = []
        for s in sales:
            formatted_sales.append({
                'id': int(s['id']),
                'product_id': int(s['product_id']),
                'product_name': str(s['product_name']),
                'unit_price': float(s['unit_price']),
                'sale_qty': int(s['sale_qty']),
                'total_sale_value': float(s['total_sale_value']),
                'sale_date': str(s['sale_date']) if s['sale_date'] else '',
                'created_at': str(s['created_at']) if s['created_at'] else '',
                'updated_at': str(s['updated_at']) if s['updated_at'] else ''
            })
        return formatted_sales
    else:
        sql = """
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
        JOIN product p ON s.product_id = p.product_id
        WHERE s.sale_id = %s
        """
        s = db.query_one(sql, (sale_id,))
        db.close_db()
        if not s:
            return None
        return {
            'id': int(s['id']),
            'product_id': int(s['product_id']),
            'product_name': str(s['product_name']),
            'unit_price': float(s['unit_price']),
            'sale_qty': int(s['sale_qty']),
            'total_sale_value': float(s['total_sale_value']),
            'sale_date': str(s['sale_date']) if s['sale_date'] else '',
            'created_at': str(s['created_at']) if s['created_at'] else '',
            'updated_at': str(s['updated_at']) if s['updated_at'] else ''
        }

## Creating a sale
def insert_sale(
        product_id: int, 
        sale_qty: int, 
        sale_date: str
    ):
    sql = """
    INSERT INTO sale (product_id, sold_qty, sold_date, created_at, updated_at)
    VALUES (%s, %s, %s, NOW(), NOW())
    """
    new_id = db.execute(sql, (product_id, sale_qty, sale_date))
    db.close_db()
    return new_id

# Updating a sale
def update_sale(
        product_id: int, 
        sale_qty: int, 
        sale_date: str, 
        sale_id: int
    ):
    sql = """
    UPDATE sale
    SET product_id = %s, sold_qty = %s, sold_date = %s, updated_at = NOW()
    WHERE sale_id = %s
    """
    rows_affected = db.execute(sql, (product_id, sale_qty, sale_date, sale_id))
    db.close_db()
    return rows_affected

# Deleting a sale
def delete_sale(sale_id: int):
    sql = """
    DELETE FROM sale WHERE sale_id = %s
    """
    rows_affected = db.execute(sql, (sale_id,))
    db.close_db()
    return rows_affected