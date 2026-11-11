"""
=============================================================================
Course: BFB321 - Supply Chain Web Application
Module: new_code/models.py
Description:
    Business logic, inventory simulation, and statistical computations for
    the Supply Chain Overview dashboard.
    
    Principles adhered to (as taught in lecture slides):
    1. Separation of Concerns: app.py handles routing; models.py executes SQL
       and applies business domain logic (Lecture Slide Class 5, Slide 6).
    2. EOQ & Inventory Formulas:
       - EOQ (Economic Order Quantity): Q = sqrt((2 * D * S) / H)
       - ROP (Reorder Point): ROP = (d * L_eff) + SS
       - SS (Safety Stock): SS = z * sqrt(sigma_d^2 + sigma_LT^2) * sqrt(LT)
       - Total Cost: TC = (K * D / Q) + (Q * h / 2)
    3. Multi-tier Stock Status:
       Calculated dynamically based on real data: Out of Stock (Red),
       Safety Stock level (Yellow-Orange Warning), Low Stock (Orange),
       and Healthy Stock (Green) (Lecture Slide Class 5, Slide 42).
=============================================================================
"""

import sys
import os
import math
import numpy as np
import scipy.stats as stats
import pandas as pd

# Ensure root directory is on the path so we can import root db.py safely
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import db


# =============================================================================
# 1. CORE SUPPLY CHAIN FORMULAS (From Lecture Materials)
# =============================================================================

def calculate_eoq(annual_demand: int, holding_cost: float, setup_cost: float) -> int:
    """
    Calculates the Economic Order Quantity (EOQ).
    Formula: Q = sqrt((2 * D * S) / H)
    
    Parameters:
        annual_demand: Total annual units required (D)
        holding_cost:  Holding cost per unit per year (H)
        setup_cost:    Ordering / setup cost per batch (S)
    """
    if holding_cost <= 0 or annual_demand <= 0 or setup_cost <= 0:
        return 0
    eoq_value = math.sqrt((2 * annual_demand * setup_cost) / holding_cost)
    return int(round(eoq_value, 0))


def calculate_rop(daily_demand: int, effective_LT: int, safety_stock: int) -> int:
    """
    Calculates the Reorder Point (ROP).
    Formula: ROP = (daily_demand * effective_LT) + safety_stock
    """
    return int(round((daily_demand * effective_LT) + safety_stock, 0))


def calculate_ss(service_level: float, std_LT: float, std_demand: float, LT: int) -> int:
    """
    Calculates the required Safety Stock (SS) under stochastic demand & lead time.
    Formula: SS = z * sqrt(std_demand^2 + std_LT^2) * sqrt(LT)
    
    Parameters:
        service_level: Desired cycle service level (e.g. 0.95 = 95%)
        std_LT:        Standard deviation of lead time
        std_demand:    Standard deviation of demand
        LT:            Average lead time in days
    """
    effective_lt = max(LT, 1)
    combined_std = math.sqrt((std_demand ** 2) + (std_LT ** 2))
    z = stats.norm.ppf(service_level)
    return int(round(z * combined_std * math.sqrt(effective_lt), 0))


def calculate_tc(annual_demand: int, setup_cost: float, order_qty: int, holding_cost: float) -> float:
    """
    Calculates Annual Total Inventory Cost (TC).
    Formula: TC = (S * D / Q) + (Q * H / 2)
    """
    if order_qty <= 0:
        return 0.0
    ordering_cost_component = (setup_cost * annual_demand) / order_qty
    holding_cost_component = (order_qty * holding_cost) / 2.0
    return round(ordering_cost_component + holding_cost_component, 2)


# =============================================================================
# 2. INVENTORY SIMULATION (Real-Time EOQ Sawtooth Simulation)
# =============================================================================

def simulation_eoq(
    starting_inventory: int = 200,
    initial_replenish: int = 0,
    df_date: pd.Series = None,
    df_demand: pd.Series = None,
    rop: int = 0,
    eoq: int = 0,
    effective_LT: int = 0
) -> pd.DataFrame:
    """
    Simulates daily inventory trajectory over time using the EOQ model.
    When inventory drops below or equal to ROP, a replenishment order of size EOQ
    is triggered and arrives after effective_LT days.
    """
    df_sim = pd.concat([df_date.reset_index(drop=True), df_demand.reset_index(drop=True)], axis=1)
    df_sim.columns = ['Date', 'Demand']
    df_sim['Inventory'] = 0
    df_sim['Replenish'] = 0

    # Initial inventory at day 0
    df_sim.loc[0, 'Inventory'] = max(
        starting_inventory - int(df_sim.loc[0, 'Demand']) + initial_replenish,
        0
    )

    lead_time = max(int(round(effective_LT)), 1)
    n_days = len(df_sim)

    for i in range(1, n_days):
        # Daily balance: prior inventory + today's delivery - today's sales
        df_sim.loc[i, 'Inventory'] = max(
            int(df_sim.loc[i - 1, 'Inventory']) + int(df_sim.loc[i, 'Replenish']) - int(df_sim.loc[i, 'Demand']),
            0
        )

        # Trigger order if at or below ROP and no order is currently in transit
        window_end = min(i + lead_time, n_days - 1)
        orders_in_transit = df_sim.loc[i:window_end, 'Replenish'].sum()

        if (int(df_sim.loc[i, 'Inventory']) <= rop) and (orders_in_transit == 0) and (i + lead_time < n_days):
            df_sim.loc[i + lead_time, 'Replenish'] = eoq

    return df_sim[['Date', 'Inventory']].copy()


# =============================================================================
# 3. DATABASE QUERIES & RESAMPLING
# =============================================================================

def select_product(product_id: str = "1") -> pd.DataFrame:
    """
    Retrieves sales for a product from the database, resamples daily across the
    calendar year 2026, and imputes zero demand for dates without recorded sales.
    """
    sql = """
        SELECT s.products_sold_date, s.sold_quantity
        FROM Sale s
        WHERE s.product_id = %s
        ORDER BY s.products_sold_date
    """
    rows = db.query_all(sql, product_id)
    if not rows:
        # Fallback empty year if product has no recorded sales
        full_year = pd.date_range(start='2026-01-01', end='2026-12-31', freq='D')
        return pd.DataFrame({'Date': full_year, 'Demand': [0] * len(full_year)})

    df_products = pd.DataFrame(rows)
    df_products.columns = ['Date', 'Demand']
    df_products['Date'] = pd.to_datetime(df_products['Date'])
    df_products['Demand'] = pd.to_numeric(df_products['Demand'])

    df_daily = df_products.groupby('Date')['Demand'].sum()
    year = df_daily.index.year[0] if len(df_daily) > 0 else 2026
    full_year = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31', freq='D')

    df_products = (
        df_daily.reindex(full_year, fill_value=0)
        .reset_index()
        .rename(columns={'index': 'Date'})
    )
    return df_products


def determine_stock_status(available_stock: int, safety_stock: int, rop: int) -> dict:
    """
    Calculates visual stock status indicators per user and lecture specifications:
      - 🔴 Red: Out of Stock (0 units)
      - ⚠️ Warning Icon / Yellow-Orange: Safety Stock level (0 < stock <= SS)
      - 🟧 Orange: Low Stock (SS < stock <= ROP)
      - 🟢 Green: OK / Healthy Stock (stock > ROP)
    """
    if available_stock <= 0:
        return {
            'status': 'Out of Stock',
            'code': 'out_of_stock',
            'color': '#ef4444',          # Red
            'badge_class': 'badge-danger',
            'icon': 'fa-solid fa-circle-xmark',
            'symbol': '🔴',
            'description': 'Stock is depleted. Urgent purchase order required.'
        }
    elif available_stock <= safety_stock:
        return {
            'status': 'Safety Stock Level',
            'code': 'safety_stock',
            'color': '#eab308',          # Yellow-Orange
            'badge_class': 'badge-warning',
            'icon': 'fa-solid fa-triangle-exclamation',
            'symbol': '⚠️',
            'description': 'Operating within safety buffer. Stockout risk imminent.'
        }
    elif available_stock <= rop:
        return {
            'status': 'Low Stock',
            'code': 'low_stock',
            'color': '#f97316',          # Orange
            'badge_class': 'badge-orange',
            'icon': 'fa-solid fa-square',
            'symbol': '🟧',
            'description': 'Stock reached Reorder Point. Place replenishment order.'
        }
    else:
        return {
            'status': 'Healthy Stock',
            'code': 'healthy',
            'color': '#10b981',          # Green
            'badge_class': 'badge-success',
            'icon': 'fa-solid fa-circle-check',
            'symbol': '🟢',
            'description': 'Adequate inventory covering anticipated cycle demand.'
        }


# =============================================================================
# 4. COMPREHENSIVE OVERVIEW DATA AGGREGATION
# =============================================================================

def get_overview_data(selected_id: str = None) -> dict:
    """
    Compiles all data needed for the Overview dashboard:
      - Product list with real-time stock indicators
      - Stacked bar chart data (State A: Total financial $, State B: Unit quantities)
      - Simulation line chart data (State A: All products, State B: Focused product
        overlapping Forecasted Simulation with Actual inventory progression)
      - Action button analytics (Analysis & Month-End summaries)
    """
    # 1. Fetch all products from MySQL
    products_db = db.query_all(
        "SELECT product_id, product_name, product_price FROM Product ORDER BY product_id"
    )

    # Distinct color palette for multi-product simulation rendering
    palette = [
        '#10b981',  # Emerald Green (Product 1)
        '#06b6d4',  # Vibrant Cyan (Product 2)
        '#f59e0b',  # Amber Gold (Product 3)
        '#8b5cf6',  # Violet Purple (Product 4)
        '#3b82f6',  # Royal Blue (Product 5)
    ]

    products_list = []
    simulation_datasets = []
    
    total_available_val = 0.0
    total_reserved_val = 0.0
    total_sold_val = 0.0

    total_available_qty = 0
    total_reserved_qty = 0
    total_sold_qty = 0

    shared_dates = None

    for idx, p in enumerate(products_db):
        p_id = str(p['product_id'])
        p_name = p['product_name']
        p_price = float(p['product_price'])
        color = palette[idx % len(palette)]

        # Demand time series
        df_p = select_product(p_id)
        if shared_dates is None:
            # Format dates as YYYY-MM-DD
            shared_dates = df_p['Date'].dt.strftime('%Y-%m-%d').tolist()

        # Lead time standard deviation
        std_lt_res = db.query_all(
            "SELECT std(i.inventory_update_date - i.inventory_order_date) AS std_d "
            "FROM Inventory_Order i WHERE i.product_id = %s",
            p_id
        )
        std_lt = float(std_lt_res[0]['std_d']) if std_lt_res and std_lt_res[0]['std_d'] is not None else 1.0

        # Demand standard deviation
        std_demand_res = db.query_all(
            "SELECT std(s.sold_quantity) AS std_s "
            "FROM Sale s WHERE s.product_id = %s",
            p_id
        )
        std_demand = float(std_demand_res[0]['std_s']) if std_demand_res and std_demand_res[0]['std_s'] is not None else 5.0

        # Average Lead Time
        avg_lt_res = db.query_all(
            "SELECT avg(i.inventory_update_date - i.inventory_order_date) AS avg_d "
            "FROM Inventory_Order i WHERE i.product_id = %s",
            p_id
        )
        avg_lt = float(avg_lt_res[0]['avg_d']) if avg_lt_res and avg_lt_res[0]['avg_d'] is not None else 2.0

        # Supply chain metrics
        total_demand = int(df_p['Demand'].sum())
        mean_demand = df_p['Demand'].mean()
        ss = calculate_ss(0.95, std_lt, std_demand, int(round(avg_lt)))
        eoq = calculate_eoq(total_demand, 20.0, 300.0)
        ct = eoq / max(round(mean_demand, 0), 1.0)
        effective_lt = int(np.mod(avg_lt, ct))
        rop = calculate_rop(int(round(mean_demand, 0)), effective_lt, ss)

        # Simulation
        df_sim = simulation_eoq(200, 0, df_p['Date'], df_p['Demand'], rop, eoq, effective_lt)
        sim_inventory_curve = df_sim['Inventory'].tolist()

        # Reserved quantity from Job_Product junction table
        job_res = db.query_all(
            "SELECT SUM(qty_of_products_used_in_job) AS reserved "
            "FROM Job_Product WHERE product_id = %s",
            p_id
        )
        reserved_qty = int(job_res[0]['reserved']) if job_res and job_res[0]['reserved'] is not None else 0

        # Current available stock from latest simulated state
        available_qty = int(df_sim['Inventory'].iloc[-1])
        sold_qty = total_demand

        # Status determination
        status_info = determine_stock_status(available_qty, ss, rop)

        # Financial valuations ($)
        available_val = available_qty * p_price
        reserved_val = reserved_qty * p_price
        sold_val = sold_qty * p_price
        total_val = available_val + reserved_val + sold_val

        # Accumulate totals
        total_available_val += available_val
        total_reserved_val += reserved_val
        total_sold_val += sold_val

        total_available_qty += available_qty
        total_reserved_qty += reserved_qty
        total_sold_qty += sold_qty

        # Actual recorded progression (order receipts minus sales)
        actual_inventory_curve = []
        running_actual = 200  # starting baseline
        
        # Query orders with replenishment dates
        orders = db.query_all(
            "SELECT inventory_update_date FROM Inventory_Order "
            "WHERE product_id = %s AND inventory_update_date IS NOT NULL "
            "ORDER BY inventory_update_date",
            p_id
        )
        order_dates = {str(o['inventory_update_date']) for o in orders}

        sales_by_date = {
            r['products_sold_date'].strftime('%Y-%m-%d'): int(r['sold_quantity'])
            for r in db.query_all(
                "SELECT products_sold_date, sold_quantity FROM Sale WHERE product_id = %s",
                p_id
            )
        }

        for d_str in shared_dates:
            # Order receipt
            if d_str in order_dates:
                running_actual += eoq  # replenishment batch received
            # Sales deduction
            if d_str in sales_by_date:
                running_actual -= sales_by_date[d_str]
            actual_inventory_curve.append(max(running_actual, 0))

        prod_record = {
            'product_id': p_id,
            'name': p_name,
            'price': p_price,
            'price_formatted': f"${p_price:,.2f}",
            'color': color,
            'available_qty': available_qty,
            'reserved_qty': reserved_qty,
            'sold_qty': sold_qty,
            'available_val': available_val,
            'reserved_val': reserved_val,
            'sold_val': sold_val,
            'total_val': total_val,
            'ss': ss,
            'rop': rop,
            'eoq': eoq,
            'status': status_info['status'],
            'status_code': status_info['code'],
            'badge_class': status_info['badge_class'],
            'icon': status_info['icon'],
            'symbol': status_info['symbol'],
            'color_hex': status_info['color'],
            'description': status_info['description'],
            'sim_curve': sim_inventory_curve,
            'actual_curve': actual_inventory_curve,
        }
        products_list.append(prod_record)

        simulation_datasets.append({
            'label': p_name,
            'productId': p_id,
            'borderColor': color,
            'backgroundColor': color,
            'data': sim_inventory_curve,
            'tension': 0.1,
            'fill': False,
        })

    # Portfolio metrics
    portfolio_summary = {
        'total_available_val': total_available_val,
        'total_reserved_val': total_reserved_val,
        'total_sold_val': total_sold_val,
        'grand_total_val': total_available_val + total_reserved_val + total_sold_val,
        'total_available_qty': total_available_qty,
        'total_reserved_qty': total_reserved_qty,
        'total_sold_qty': total_sold_qty,
        'total_items_count': len(products_list),
        'total_available_val_formatted': f"${total_available_val:,.2f}",
        'total_reserved_val_formatted': f"${total_reserved_val:,.2f}",
        'total_sold_val_formatted': f"${total_sold_val:,.2f}",
        'grand_total_val_formatted': f"${(total_available_val + total_reserved_val + total_sold_val):,.2f}",
    }

    # Selected product resolution
    selected_prod = None
    if selected_id:
        for p in products_list:
            if str(p['product_id']) == str(selected_id):
                selected_prod = p
                break

    return {
        'products': products_list,
        'portfolio': portfolio_summary,
        'shared_dates': shared_dates,
        'simulation_datasets': simulation_datasets,
        'selected_product': selected_prod,
        'selected_id': str(selected_id) if selected_id else None
    }

