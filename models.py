"""
This file is for all the functions that will be used in the app.py file
"""

import numpy as np
import scipy.stats as stats
import pandas as pd
import db

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

"""
simulation_eoq is used to generate a dataframe with column 1 being the date and column 2 being the inventory. This function 
takes in the re-order point value, economic order quantity, starting inventory, projected demand on a projected date and 
simulates how the inventory system will respond. 
"""

def simulation_eoq(
        starting_inventory: int = 0,
        initial_replenish: int = 0, 
        df_date: pd.DataFrame = None, 
        df_demand: pd.DataFrame = None, 
        rop: int = 0, 
        eoq: int = 0, 
        effective_LT: int = 0):
    
    # combining the date and demand dataframe into one dataframe
    df_sim = pd.concat([df_date.reset_index(drop=True), df_demand.reset_index(drop=True)], axis=1)

    # rename columns to ensure consistency
    df_sim.columns = ['Date', 'Demand']

    # adding the required columns 
    df_sim['Inventory'] = 0
    df_sim['Replenish'] = 0

    # defining the initial inventory
    df_sim.loc[0,'Inventory'] = starting_inventory - int(df_sim.loc[0, 'Demand']) + initial_replenish

    # Looping through all data entries
    for i in range(1, len(df_sim)):

        # Calculating the inventory. The max is to ensure inventory does not go negative
        df_sim.loc[i, 'Inventory'] = max(int(df_sim.loc[i-1, 'Inventory']) + int(df_sim.loc[i, 'Replenish']) - int(df_sim.loc[i, 'Demand']), 0)

        # check if inventory is below or at the re-order point and if no order was placed
        if (int(df_sim.loc[i, 'Inventory']) <= rop) and\
           (df_sim.loc[i:min(i+effective_LT, len(df_sim)-1), 'Replenish'].sum() == 0) and\
           (i+effective_LT < len(df_sim)):

            # assigning the replenish in the future to the economic order quantity
            df_sim.loc[i+effective_LT, 'Replenish'] = eoq


    df_out = df_sim[['Date', 'Inventory']].copy()
    return df_out


def select_product(search: str = ""):
    sql = """
        SELECT s.products_sold_date, s.sold_quantity
        FROM Sale s
        WHERE s.product_id = %s
        ORDER BY s.products_sold_date
    """
    # Extract the date and amount columns for a specific product
    df_products = pd.DataFrame(db.query_all(sql, search))

    # rename the columns to understandable names
    df_products.columns = ['Date', 'Demand']

    # ensure correct data type
    df_products['Date'] = pd.to_datetime(df_products['Date'])
    df_products['Demand'] = pd.to_numeric(df_products['Demand'])

    # determine the daily demand
    df_daily = df_products.groupby('Date')['Demand'].sum()

    # extract the year from the data
    year = df_daily.index.year[0]

    # generate the full year
    full_year = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31', freq='D')

    # combine the daily demand and the full year
    df_products = (df_daily
                   .reindex(full_year, fill_value=0)
                   .reset_index()
                   .rename(columns={'index':'Date'}))
    return df_products


def select_LT(search:str = ""):
    sql = """
        SELECT i.inventory_order_date, i.inventory_update_date
        FROM Inventory_Order i
        WHERE i.product_id = %s
        ORDER BY i.inventory_order_date
    """
    df_LT = pd.DataFrame(db.query_all(sql, search))
    df_LT.columns = ['Date', 'end_d']
    
    df_LT['Date'] = pd.to_datetime(df_LT['Date'])
    df_LT['end_d'] = pd.to_datetime(df_LT['end_d'])

    df_LT['LT'] = df_LT['end_d'] - df_LT['Date']
    df_LT.drop('end_d')

