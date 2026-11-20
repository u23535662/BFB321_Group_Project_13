import db
import math
import statistics

# =============================================================================
# SUPPLY CHAIN FORMULAS
# =============================================================================

## Economic Order Quantity
def calculate_eoq(annual_demand: int, holding_cost: float, setup_cost: float, conversion:int) -> int:
    """
    Calculates the Economic Order Quantity (EOQ) using the classical Wilson lot-size formula.
    
    Formula:
        Q = sqrt((2 * D * S) / H)
        where:
            D = Annual demand in physical units
            S = Fixed setup / ordering cost per procurement batch
            H = Annual inventory holding cost per unit per year

    Inputs:
        annual_demand (int): Total expected or historical units consumed per year (D).
        holding_cost (float): Holding / carrying cost per unit per annum (H).
        setup_cost (float): Order placement, logistics, and processing cost per order (S).
        conversion (int): Amount of units are in an ordered box

    Returns:
        int: The cost-minimizing order batch quantity (Q), rounded to nearest box quantity.

    Assumptions / Edge Cases:
        - If holding_cost <= 0, annual_demand <= 0, or setup_cost <= 0, returns 0 to
          prevent ZeroDivisionError and domain errors under negative square roots.
        - Demand rate is assumed deterministic and uniform across the planning horizon.
    """
    if holding_cost <= 0 or annual_demand <= 0 or setup_cost <= 0:
        return 0
    raw_eoq = math.sqrt((2.0 * float(annual_demand) * float(setup_cost)) / float(holding_cost))
    box_eoq = math.ceil(raw_eoq/conversion)*conversion
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
def calculate_rop(daily_demand: float, effective_lt: int, safety_stock: int) -> int:
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
        effective_lt (int): Lead time modulo cycle time (L_eff).
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
def calculate_abc_classification(products_list: list) -> dict:
    """
    Computes Pareto ABC Inventory Classification based on annual consumption value.
    
    Formula:
        Annual Consumption Value = Annual Demand * Unit Price
        where Annual Demand = (Historical Sold Units / 3.0 years)
        Cumulative Value % = (Cumulative Consumption Value / Total Consumption Value) * 100
        
        Pareto Classification Thresholds:
            - Class A (High Priority / Strict Control):
                Top ~70% of total annual consumption value. Typically represents ~20-25%
                of SKU count. Demands tight monitoring, accurate records, and frequent reviews.
            - Class B (Moderate Priority / Normal Control):
                Next ~20% of total consumption value (cumulative ~70% to 90%).
                Managed via standard automated EOQ/ROP replenishment rules.
            - Class C (Low Priority / Simplified Control):
                Final ~10% of total consumption value (cumulative > 90%).
                Higher safety buffers and bulk packaging to minimize administrative overhead.

    Inputs:
        products_list (list): List of product dictionary objects, each containing:
            - 'product_id' (int): Primary product identifier
            - 'name' (str): Product description / brand
            - 'price' (float): Clinical unit selling price
            - 'sold_qty' (int): Cumulative historical 3-year consumption

    Returns:
        dict: Detailed classification dictionary containing:
            - 'class_a': list of products assigned to Class A
            - 'class_b': list of products assigned to Class B
            - 'class_c': list of products assigned to Class C
            - 'counts': dict mapping 'A', 'B', 'C' to SKU counts
            - 'percentages': dict mapping 'A', 'B', 'C' to financial value percentage shares
            - 'total_annual_value': float representing total annual consumption value
            - 'total_annual_value_formatted': str formatted in South African Rand (ZAR)

    Assumptions / Edge Cases:
        - If products_list is empty or total_annual_value <= 0, returns empty structures
          with 0 counts to prevent ZeroDivisionError.
        - Each product object in products_list is updated in place with 'abc_class',
          'abc_badge_class', 'abc_annual_val', and 'abc_annual_val_formatted'.
    """
    if not products_list:
        return {
            "class_a": [], "class_b": [], "class_c": [],
            "counts": {"A": 0, "B": 0, "C": 0},
            "percentages": {"A": 0.0, "B": 0.0, "C": 0.0},
            "total_annual_value": 0.0,
            "total_annual_value_formatted": "R 0.00"
        }

    # Sort products in descending order by annual consumption value: (sold_qty / 3.0) * price
    sorted_prods = sorted(
        products_list,
        key=lambda p: (float(p.get("sold_qty", 0)) / 3.0) * float(p.get("price", 0.0)),
        reverse=True
    )

    total_annual_val = sum((float(p.get("sold_qty", 0)) / 3.0) * float(p.get("price", 0.0)) for p in sorted_prods)
    if total_annual_val <= 0:
        total_annual_val = 1.0

    class_a, class_b, class_c = [], [], []
    val_a, val_b, val_c = 0.0, 0.0, 0.0
    cum_val = 0.0

    for i, p in enumerate(sorted_prods):
        ann_val = (float(p.get("sold_qty", 0)) / 3.0) * float(p.get("price", 0.0))
        cum_val += ann_val
        cum_pct = (cum_val / total_annual_val) * 100.0

        # Classify based on Pareto cumulative cutoff (A: ~70%, B: ~90%, C: >90%)
        # Enforcing at least top 2 items in A and bottom 2 in C
        if (cum_pct <= 70.0 and i < 4) or i < 2:
            cls = "A"
            badge = "badge-abc-a"
            class_a.append(p)
            val_a += ann_val
        elif cum_pct <= 90.0 or i < 7:
            cls = "B"
            badge = "badge-abc-b"
            class_b.append(p)
            val_b += ann_val
        else:
            cls = "C"
            badge = "badge-abc-c"
            class_c.append(p)
            val_c += ann_val

        p["abc_class"] = cls
        p["abc_badge_class"] = badge
        p["abc_annual_val"] = ann_val
        p["abc_annual_val_formatted"] = f"R {ann_val:,.2f}"

    pct_a = round((val_a / total_annual_val) * 100.0, 1)
    pct_b = round((val_b / total_annual_val) * 100.0, 1)
    pct_c = round((val_c / total_annual_val) * 100.0, 1)

    return {
        "class_a": class_a,
        "class_b": class_b,
        "class_c": class_c,
        "counts": {"A": len(class_a), "B": len(class_b), "C": len(class_c)},
        "percentages": {"A": pct_a, "B": pct_b, "C": pct_c},
        "total_annual_value": total_annual_val,
        "total_annual_value_formatted": f"R {total_annual_val:,.2f}"
    }
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
        p = db.query_one(sql, product_id)
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

    eoq_sql = """
    WITH yearly_sales AS (
        SELECT 
            product_id, 
            YEAR(sold_date) AS sales_year,
            SUM(sold_qty) AS yearly_qty
        FROM sale
        WHERE sold_date >= MAKEDATE(YEAR(CURDATE()) - 5, 1)
        GROUP BY 
            product_id, 
            YEAR(sold_date)
    ),
    avg_yearly_sales AS (
        SELECT 
            product_id, 
            AVG(yearly_qty) AS avg_annual_sold_qty
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
    ss_sql = """
    
    """
    for p in products_to_process:
        p_id = p['id']
        data_eoq = db.query_one(eoq_sql, (p_id,))

        if data_eoq:
            annual_demand = int(round(float(data_eoq['annual_demand'] or 0)))
            setup_cost = float(data_eoq['setup_cost'] or 0)
            box_conversion = max(int(data_eoq['box_conversion'] or 1), 1)
            eoq = calculate_eoq(annual_demand, p['holding_cost'], setup_cost, box_conversion)
        else:
            eoq = 0

        output_product.append({ 
            'id': int(p['id']),
            'name': str(p['name']),
            'price': float(p['price']),
            'holding_cost': float(p['holding_cost']),
            'eoq': int(eoq)
        })

    return output_product[0] if product_id is not None else output_product

## Creating a product
def insert_product(name:str = '', price:str = '', holding_cost:str ='', starting_inventory: str = ''):
    sql = """
    INSERT INTO product (product_name, product_price, product_holding_cost, stock_quantity)
    VALUES (%s, %s, %s, %s)
    """
    id = db.execute(sql, (name, price, holding_cost, starting_inventory))
    db.close_db
    return id

## Editing product
def update_product(name:str, price:float, holding_cost:float, starting_inventory:int, product_id: str):
    sql = """
    UPDATE product
    SET product_name = %s, product_price= %s, product_holding_cost= %s, stock_quantity=%s
    WHERE product_id = %s
    """
    id = db.execute(sql, (name, price, holding_cost, starting_inventory, product_id))
    db.close_db()
    return id

## Deleting product
def delete_product(product_id: str):
    sql = """
    DELETE FROM product WHERE product_id=%s
    """
    id = db.execute(sql, product_id)
    db.close_db()
    return id
