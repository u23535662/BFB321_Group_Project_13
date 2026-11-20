import db
import math
import statistics

# =============================================================================
# SUPPLY CHAIN FORMULAS
# =============================================================================

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
    raw_eoq = math.sqrt((2.0 * float(annual_demand) * float(setup_cost)) / float(holding_cost))
    box_eoq = math.ceil(raw_eoq / conversion) * conversion
    return int(round(box_eoq))


## Safety Stock
def calculate_ss(service_level: float, std_lt: float, std_demand: float, lt: int) -> int:
    """
    Computes required Safety Stock (SS) under stochastic demand and supplier lead time.
    
    Formula:
        SS = z * sqrt(sigma_d^2 + sigma_LT^2) * sqrt(LT)
        where:
            z = Inverse cumulative standard normal distribution value for service level
            sigma_d = Standard deviation of daily clinical demand
            sigma_LT = Standard deviation of supplier lead time in days
            LT = Mean vendor lead time in days

    Inputs:
        service_level (float): Target cycle service level (e.g. 0.95 for 95% protection).
        std_lt (float): Standard deviation of replenishment lead time.
        std_demand (float): Standard deviation of daily units consumed/sold.
        lt (int): Average lead time in calendar days.

    Returns:
        int: Buffer stock units required to prevent stockouts during replenishment lead time.

    Assumptions / Edge Cases:
        - Uses Python standard library statistics.NormalDist(0, 1).inv_cdf() for exact z score.
        - Clamps minimum effective lead time to 1 day to prevent zero multiplication.
        - Assumes clinical demand and vendor delivery lead times follow independent normal distributions.
    """
    effective_lt = max(int(round(lt)), 1)
    # Combined variance under stochastic demand & lead time
    combined_std = math.sqrt((float(std_demand) ** 2) + (float(std_lt) ** 2))
    
    # Calculate z factor from target service level
    try:
        dist = statistics.NormalDist(mu=0.0, sigma=1.0)
        z = dist.inv_cdf(min(max(service_level, 0.50), 0.999))
    except Exception:
        z = 1.64485  # Fallback for 95% cycle service level
        
    ss_value = z * combined_std * math.sqrt(effective_lt)
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
    # Function for assigning tiers
    def assign_tier(cum_pct: float) -> str:
        if cum_pct <= 80.0:
            return "A"
        elif cum_pct <= 95.0:
            return "B"
        else:
            return "C"

    if not products_list:
        return []

    # Calculate value for each SKU
    for p in products_list:
        p['value'] = float(p['demand']) * float(p['price'])

    # Sort SKUs descending by value
    skus_sorted = sorted(products_list, key=lambda item: item['value'], reverse=True)

    # Calculate cumulative percentage and assign tiers
    total_value = sum(item['value'] for item in skus_sorted)
    running_total = 0.0
    for item in skus_sorted:
        if total_value > 0:
            running_total += item['value']
            item['cum_pct'] = (running_total / total_value) * 100.0
            item['tier'] = assign_tier(item['cum_pct'])
        else:
            item['cum_pct'] = 0.0
            item['tier'] = "C"

    return skus_sorted


# =============================================================================
# JSON FUNCTIONS
# =============================================================================

## Getting raw product data
def get_products_raw(product_id=None):
    if product_id == '' or product_id is None:
        sql = """
        SELECT 
            p.product_id AS id,
            p.product_name AS name,
            p.product_price AS price,   
            p.stock_quantity AS starting_inv,
            p.product_holding_cost AS hc
        FROM product p
        """
        products = db.query_all(sql)
        db.close_db()
        formatted_products = []
        for p in products:
            formatted_products.append({
                'id': int(p['id']),
                'name': str(p['name']),
                'price': float(p['price']),
                'year_starting_inventory': int(p['starting_inv']),
                'holding_cost': float(p['hc'])
            })
        return formatted_products
    else:
        sql = """
        SELECT 
            p.product_id AS id,
            p.product_name AS name,
            p.product_price AS price,   
            p.stock_quantity AS starting_inv,
            p.product_holding_cost AS hc
        FROM product p
        WHERE p.product_id = %s
        """
        p = db.query_one(sql, (product_id,))
        db.close_db()
        if not p:
            return None
        return {
            'id': int(p['id']),
            'name': str(p['name']),
            'price': float(p['price']),
            'year_starting_inventory': int(p['starting_inv']),
            'holding_cost': float(p['hc'])
        }


## Getting relevant product data
def get_products(product_id=None):
    r_product = get_products_raw(product_id)
    if not r_product:
        return None if product_id is not None else []

    # Normalize to a list so the loop works for both all-products and single-product requests
    products_to_process = [r_product] if product_id is not None else r_product
    output_product = []

    # Past 1 full calendar year, excluding the current year
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
    abc_lookup = {int(item['id']): item['tier'] for item in abc_data}

    # Past 5 full calendar years, excluding the current year
    eoq_sql = """
    WITH yearly_sales AS (
        SELECT 
            product_id, 
            YEAR(sold_date) AS sales_year,
            SUM(sold_qty) AS yearly_qty
        FROM sale
        WHERE sold_date >= MAKEDATE(YEAR(CURDATE()) - 5, 1)
          AND sold_date < MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY 
            product_id, 
            YEAR(sold_date)
    ),
    avg_yearly_sales AS (
        SELECT 
            product_id, 
            SUM(yearly_qty) / 5.0 AS avg_annual_sold_qty
        FROM yearly_sales
        GROUP BY product_id
    ),
    current_setup AS (
        SELECT 
            product_id, 
            supplier_unit, 
            supplier_price,
            ROW_NUMBER() OVER (
                PARTITION BY product_id 
                ORDER BY effective_date DESC
            ) AS rn
        FROM product_supplier
    )
    SELECT 
        COALESCE(ays.avg_annual_sold_qty, 0) AS annual_demand, 
        COALESCE(cs.supplier_price, 0) AS setup_cost, 
        COALESCE(cs.supplier_unit, 1) AS box_conversion
    FROM product p 
    LEFT JOIN avg_yearly_sales ays ON p.product_id = ays.product_id 
    LEFT JOIN current_setup cs ON p.product_id = cs.product_id AND cs.rn = 1
    WHERE p.product_id = %s;
    """

    # Past 5 full calendar years, excluding the current year
    ss_sql = """
    WITH filtered_po AS (
        SELECT
            po.order_id,
            po.order_date
        FROM purchase_order po
        JOIN purchase_order_item poi
            ON po.order_id = poi.order_id
        WHERE po.order_status = 'Received'
          AND poi.product_id = %s
          AND po.order_date >= MAKEDATE(YEAR(CURDATE()) - 5, 1)
          AND po.order_date < MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY po.order_id, po.order_date
    ),
    lead_time_metrics AS (
        SELECT
            AVG(DATEDIFF(iu_agg.receipt_date, fpo.order_date)) AS avg_lt,
            STD(DATEDIFF(iu_agg.receipt_date, fpo.order_date)) AS std_lt
        FROM filtered_po fpo
        JOIN (
            SELECT
                order_id,
                MAX(update_date) AS receipt_date
            FROM inventory_update
            GROUP BY order_id
        ) iu_agg
            ON fpo.order_id = iu_agg.order_id
        WHERE iu_agg.receipt_date >= fpo.order_date
    ),
    demand_metrics AS (
        SELECT
            STD(s.sold_qty) AS std_d
        FROM sale s
        WHERE s.product_id = %s
          AND s.sold_date >= MAKEDATE(YEAR(CURDATE()) - 5, 1)
          AND s.sold_date < MAKEDATE(YEAR(CURDATE()), 1)
    )
    SELECT
        %s AS id,
        lt.avg_lt,
        lt.std_lt,
        dm.std_d
    FROM lead_time_metrics lt
    CROSS JOIN demand_metrics dm;
    """

    # Past 5 full calendar years, excluding the current year
    rop_sql = """
    WITH daily_sales AS (
        SELECT
            product_id,
            DATE(sold_date) AS sale_day,
            SUM(sold_qty) AS daily_qty
        FROM sale
        WHERE sold_date >= MAKEDATE(YEAR(CURDATE()) - 5, 1)
          AND sold_date < MAKEDATE(YEAR(CURDATE()), 1)
        GROUP BY product_id, DATE(sold_date)
    )
    SELECT
        product_id,
        AVG(daily_qty) AS avg_daily_demand
    FROM daily_sales
    WHERE product_id = %s
    GROUP BY product_id;
    """
    
    for p in products_to_process:
        p_id = p['id']
        data_eoq = db.query_one(eoq_sql, (p_id,))
        data_ss = db.query_one(ss_sql, (p_id, p_id, p_id))
        data_rop = db.query_one(rop_sql, (p_id,))

        if data_eoq:
            annual_demand = float(data_eoq['annual_demand'] or 0)
            setup_cost = float(data_eoq['setup_cost'] or 0)
            box_conversion = max(int(data_eoq['box_conversion'] or 1), 1)
            eoq = calculate_eoq(annual_demand, p['holding_cost'], setup_cost, box_conversion)
        else:
            eoq = 0

        if data_ss:
            service_level = 0.95
            std_lt = float(data_ss['std_lt'] or 0)
            std_d = float(data_ss['std_d'] or 0)
            lt = int(round(float(data_ss['avg_lt'] or 0)))
            ss = calculate_ss(service_level, std_lt, std_d, lt)
        else:
            lt = 0
            ss = 0

        if data_rop and data_rop['avg_daily_demand'] is not None:
            daily_demand = float(data_rop['avg_daily_demand'])
            if daily_demand > 0 and eoq > 0:
                t = eoq / daily_demand
                effective_lt = lt % t
                rop = calculate_rop(daily_demand, effective_lt, ss)
            else:
                rop = ss
        else:
            rop = ss

        p_class = abc_lookup.get(p_id, "C")

        output_product.append({ 
            'id': int(p['id']),
            'name': str(p['name']),
            'price': float(p['price']),
            'holding_cost': float(p['holding_cost']),
            'eoq': int(eoq),
            'ss': int(ss),
            'rop': int(rop),
            'class': str(p_class)
        })

    db.close_db()
    return output_product[0] if product_id is not None else output_product


## Creating a product
def insert_product(name: str = '', price: float = 0.0, holding_cost: float = 0.0, starting_inventory: int = 0):
    sql = """
    INSERT INTO product (product_name, product_price, product_holding_cost, stock_quantity)
    VALUES (%s, %s, %s, %s)
    """
    product_id = db.execute(sql, (name, price, holding_cost, starting_inventory))
    db.close_db()
    return product_id


## Editing product
def update_product(name: str, price: float, holding_cost: float, starting_inventory: int, product_id: int):
    sql = """
    UPDATE product
    SET product_name = %s, product_price = %s, product_holding_cost = %s, stock_quantity = %s
    WHERE product_id = %s
    """
    rows_affected = db.execute(sql, (name, price, holding_cost, starting_inventory, product_id))
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
    