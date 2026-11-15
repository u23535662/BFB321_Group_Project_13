"""
This file is for all the functions that will be used in the app.py file
"""

import numpy as np
import scipy.stats as stats
import pandas as pd
import db
import datetime 

# ===========================================================================================================================
# OVERVIEW PAGE CODE
# ===========================================================================================================================
def overview():

    # =======================================================================================================================
    # General product data for product scroll
    ## Query for data extraction
    unique_product = '''
    SELECT 
        p.product_id AS id, 
        p.product_name AS name,
        p.stock_quantity AS start,
        p.product_price AS price,
        p.product_holding_cost AS hc,
        ROUND(ps.supplier_price/ps.supplier_unit,2) AS sc
    FROM product p
    JOIN product_supplier ps
		ON p.product_id=ps.product_id
	ORDER BY p.product_id
    '''
    ## Importing data from database
    products_db = db.query_all(unique_product)

    ## Creating an empty list in which all product specific data will be stored
    products_list = []
   
    ## Looping through all products
    for p in products_db:

        p_id = str(p['id'])
        p_name = p['name']
        p_price = float(p['price'])
        p_start = int(p['start'])
        p_hc = float(p['hc'])
        p_sc = float(p['sc'])

        ### Getting historical demand
        df_demand = select_product(p_id)

        ### Getting standard deviation for lead time per product
        std_lt = db.query_all(
            """
            SELECT STD(CAST(iu.update_date AS DATE)-po.order_date) AS stdLT
            FROM purchase_order po
            JOIN purchase_order_item poi
                ON po.order_id = poi.order_id
            JOIN inventory_update iu
                ON po.order_id=iu.order_id
            WHERE poi.product_id = %s
            """,
            p_id
        )
        std_lt = float(std_lt[0]['stdLT'])

        ### Getting standard deviation for demand per product
        std_d = db.query_all(
            """
            SELECT STD(s.sold_qty) AS stdD
            FROM sale s
            WHERE s.product_id = %s
            """,
            p_id
        )
        std_d = float(std_d[0]['stdD'])

        ### Getting the average lead time per product
        avg_lt = db.query_all(
            """
            SELECT AVG(CAST(iu.update_date AS DATE)-po.order_date) AS avgLT
            FROM purchase_order po
            JOIN purchase_order_item poi
                ON po.order_id = poi.order_id
            JOIN inventory_update iu
                ON po.order_id=iu.order_id
            WHERE poi.product_id = %s
            """,
            p_id
        )
        avg_lt = int(round(avg_lt[0]['avgLT']))

        ### Supply chain metrics
        annual_demand = int(df_demand['demand'].sum())
        avg_daily_demand = int(round(df_demand['demand'].mean(),0))
        ss = calculate_ss(0.95, std_lt, std_d, avg_lt)
        eoq = calculate_eoq(annual_demand, p_hc, p_sc)
        ct = eoq/max(avg_daily_demand, 1)
        effective_lt = int(np.mod(avg_lt, ct))
        rop = calculate_rop(avg_daily_demand, effective_lt, ss)

        ### Getting open order per product
        open_order = db.query_all(
            """
            SELECT po.order_date AS open
            FROM purchase_order po
            JOIN purchase_order_item poi 
                ON po.order_id = poi.order_id
            LEFT JOIN inventory_update iu 
                ON po.order_id = iu.order_id
            WHERE poi.product_id = 1
                AND iu.order_id IS NULL
                AND po.order_status = 'Pending'
            """
        )
        open_order = str(open_order[0]['open']) if open_order and open_order[0]['open'] is not None else ''


        ### Simulation
        df_sim = simulation_eoq(p_start, open_order, df_demand['date'], df_demand['demand'], rop, eoq, effective_lt)
        sim_inventory = df_sim['inventory'].to_list()

        ### Determining the reserved inventory (inventory that will be used in a job)
        reserved_inv = db.query_all(
            """
            SELECT SUM(jc.qty_of_product_used) AS used
            FROM job_instance ji
            JOIN job_consumables jc
                ON ji.job_id=jc.job_id
            WHERE jc.product_id = %s
                AND ji.status = 'Scheduled'
            """,
            p_id
        )
        reserved_inv = int(reserved_inv[0]['used']) if reserved_inv and reserved_inv[0]['used'] is not None else 0


        available_inventory = db.query_all(
            """
            WITH yearly_sales AS (
                SELECT product_id, COALESCE(SUM(sold_qty), 0) AS total_sold
                FROM sale
                WHERE sold_date >= STR_TO_DATE(CONCAT(YEAR(CURDATE())-1, '-01-01'), '%%Y-%%m-%%d')
                GROUP BY product_id
            ),
            yearly_updates AS (
                SELECT iui.product_id, COALESCE(SUM(iui.update_amount), 0) AS total_updated
                FROM inventory_update_item iui
                JOIN inventory_update iu ON iui.update_id = iu.update_id
                WHERE iu.update_date >= STR_TO_DATE(CONCAT(YEAR(CURDATE())-1, '-01-01'), '%%Y-%%m-%%d')
                GROUP BY iui.product_id
            ),
            yearly_consumables AS (
                SELECT jc.product_id, COALESCE(SUM(jc.qty_of_product_used), 0) AS total_used
                FROM job_consumables jc
                JOIN job_instance ji ON jc.job_id = ji.job_id
                WHERE ji.operation_date >= STR_TO_DATE(CONCAT(YEAR(CURDATE())-1, '-01-01'), '%%Y-%%m-%%d')
                AND ji.status != 'Cancelled'
                GROUP BY jc.product_id
            )
            SELECT 
                GREATEST(p.stock_quantity + COALESCE(yu.total_updated, 0) - COALESCE(ys.total_sold, 0) - COALESCE(yc.total_used, 0),0) AS stock
            FROM product p
            LEFT JOIN yearly_sales ys ON p.product_id = ys.product_id
            LEFT JOIN yearly_updates yu ON p.product_id = yu.product_id
            LEFT JOIN yearly_consumables yc ON p.product_id = yc.product_id
            WHERE p.product_id = %s;
            """,
            p_id
        )
        available_inventory = int(available_inventory[0]['stock'])


    # =======================================================================================================================

    # =======================================================================================================================
    # Data for to-do section
    to_do = '''
    SELECT p.stock_quantity AS availableStock
    FROM product p
    '''






    return {
        'product_data': df_products

    }







"""
calculate_eoq takes in the annual demand, holding cost and setup cost to then calculate the economic order quantity using the 
standard formula: Q = sqrt(2*K*D/h) that is outputted as an integer
"""

def calculate_eoq(annual_demand: int, holding_cost: float, setup_cost: float):
    return int(round(np.sqrt((2*annual_demand*setup_cost)/holding_cost),0))

"""
calculate_rop takes in the daily demand, effective lead time and safety stock to then calculate the re-order point using the 
fomula: ROP = d*Leff + SS that is outputted as an integer
"""

def calculate_rop(daily_demand: int, effective_LT: int, safety_stock: int):
    return int(round((daily_demand*effective_LT)+safety_stock,0))

"""
calculate_ss takes in the service level, standard deviation for the lead time, standard deviation for the demand and lead time 
to then calculate the needed safety stock by first getting the z-value for the inputted service level and then the combined 
standard deviation. The formula used for calculating the safety stock is: SS = z*std*sqrt(L). It is assumed that the demand 
follows a normal distibution. The output is converted to an integer.
"""

def calculate_ss(service_level: float, std_LT: float, std_demand: float, LT: int):
    STD = np.sqrt(std_demand**2 + std_LT**2)
    z = stats.norm.ppf(service_level)
    return int(round(z*STD*np.sqrt(LT),0))

"""
calculate_tc takes in the annual demand, setup cost, order quantity and holding cost to calculate the annual total cost. The 
formula used is: TC = K*D/Q + Q*h/2
"""

def calculate_tc(annual_demand: int, setup_cost: float, order_qty: int, holding_cost: float):
    return (setup_cost*annual_demand/order_qty) + (order_qty*holding_cost/2)

# ===========================================================================================================================
# SIMULATION FUNCTION
# ===========================================================================================================================

"""
simulation_eoq is used to generate a dataframe with column 1 being the date and column 2 being the inventory. This function 
takes in the re-order point value, economic order quantity, starting inventory, projected demand on a projected date and 
simulates how the inventory system will respond. 
"""

def simulation_eoq(
        starting_inventory: int = 0,
        open_order_date: str = '', 
        df_date: pd.DataFrame = None, 
        df_demand: pd.DataFrame = None, 
        rop: int = 0, 
        eoq: int = 0, 
        effective_LT: int = 0):
    
    # combining the date and demand dataframe into one dataframe
    df_sim = pd.concat([df_date.reset_index(drop=True), df_demand.reset_index(drop=True)], axis=1)

    # rename columns to ensure consistency
    df_sim.columns = ['date', 'demand']

    # adding the required columns 
    df_sim['inventory'] = 0
    df_sim['replenish'] = 0

    # adding the open order to replenish
    if open_order_date != '':
        ## geting current year
        current_year = datetime.date.today().year
        ## converting the open order date to datetime data type
        open_order = datetime.datetime.strptime(open_order_date, '%Y-%m-%d').date()
        ## calculating the amount of days elapsed for previous year
        open_order_replenish_days = int(round(datetime.date(current_year,1,1) - open_order,0))
        ## calculating how many days until the order arrives based on lead time
        days_into_year = max(effective_LT - open_order_replenish_days,0)
        ## setting the replenishment value to correct date
        df_sim.loc[days_into_year, 'replenish'] = eoq

    # defining the initial inventory
    df_sim.loc[0,'inventory'] = starting_inventory - int(df_sim.loc[0, 'demand']) + int(df_sim.loc[0, 'replenish'])

    # Looping through all data entries
    for i in range(1, len(df_sim)):

        ## Calculating the inventory. The max is to ensure inventory does not go negative
        df_sim.loc[i, 'inventory'] = max(int(df_sim.loc[i-1, 'inventory']) + int(df_sim.loc[i, 'replenish']) - int(df_sim.loc[i, 'demand']), 0)

        ## check if inventory is below or at the re-order point and if no order was placed
        if (int(df_sim.loc[i, 'inventory']) <= rop) and\
           (df_sim.loc[i:min(i+effective_LT, len(df_sim)-1), 'replenish'].sum() == 0) and\
           (i+effective_LT < len(df_sim)):

            ### assigning the replenish in the future to the economic order quantity
            df_sim.loc[i+effective_LT, 'replenish'] = eoq

    # creating the output file by dropping the columns that is not needed
    df_out = df_sim[['date', 'inventory']].copy()
    return df_out

# ===========================================================================================================================
# PRODUCT SELECTION FOR SIMULATION
# ===========================================================================================================================

def select_product(search: str = ""):
    sql = """
    SELECT 
        CAST(s.sold_date AS DATE) AS date, 
        SUM(s.sold_qty) AS demand
    FROM sale s
    WHERE s.product_id = %s
      AND s.sold_date >= STR_TO_DATE(CONCAT(YEAR(CURDATE()) - 5, '-01-01'), '%%Y-%%m-%%d')
      AND s.sold_date < STR_TO_DATE(CONCAT(YEAR(CURDATE()), '-01-01'), '%%Y-%%m-%%d')
    GROUP BY CAST(s.sold_date AS DATE)
    ORDER BY date ASC
    """

    # Pass query parameters as a tuple and safely handle return data types
    raw_data = db.query_all(sql, (search,))
    
    if raw_data and isinstance(raw_data[0], (tuple, list)):
        df_products = pd.DataFrame(raw_data, columns=["date", "demand"])
    else:
        df_products = pd.DataFrame(raw_data)

    # Setup the full current calendar year backbone
    current_year = datetime.date.today().year
    full_year = pd.date_range(
        start=f"{current_year}-01-01", end=f"{current_year}-12-31", freq="D"
    )
    df_final = pd.DataFrame({"Date": full_year})

    # If database returned nothing, return the full calendar year initialised to 0
    if df_products.empty:
        df_final["demand"] = 0.0
        return df_final

    # Clean and map historical data types
    df_products["date"] = pd.to_datetime(df_products["date"])
    df_products["demand"] = pd.to_numeric(df_products["demand"])

    # Assign month and day explicitly before grouping to avoid column mapping issues
    df_products["month"] = df_products["date"].dt.month
    df_products["day"] = df_products["date"].dt.day

    # Group by Month and Day to calculate historical daily averages
    daily_avg = df_products.groupby(
        ["month", "day"], 
        as_index=False
    )["demand"].mean()
    
    # Round up the demand values
    daily_avg["demand"] = np.ceil(daily_avg["demand"])

    # Create mapping keys on our current year timeline
    df_final["month"] = df_final["Date"].dt.month
    df_final["day"] = df_final["Date"].dt.day

    # Merge historical averages onto the complete calendar year
    df_final = pd.merge(df_final, daily_avg, on=["month", "day"], how="left")

    # Fill completely empty calendar slots with 0 and clean up keys
    df_final["demand"] = df_final["demand"].fillna(0)
    df_final = df_final[["Date", "demand"]]

    return df_final

# ===========================================================================================================================
# PRODUCT STATUS INDICATOR
# ===========================================================================================================================
def determine_stock_status(available_stock: int, safety_stock: int, rop:int):
    if available_stock <= 0:
        return {
            'status': 'Out of Stock',
            'description': 'Out of Stock. Urgent purchase order is needed'
        }
    elif available_stock <= safety_stock:
        return {
            'status': 'Safety Stock Level',
            'description': 'Operating within safety buffer. Stockout risk imminent.'
        }
    elif available_stock <= rop:
        return{
            'status': 'Low Stock',
            'description': 'Srock reached Reorder Point. Place order'
        }
    else:
        return{
            'status': 'Healthy Stock',
            'description': 'Adequate inventory'
        }

