# This code has everything to do with the inventory side of the project
# Ideas: EOQ, inventory forecasting, inventory warnings, trends graphs, ABC classification
# Methods of importing data: Excell, CSV
# %%
# ===== Imporing packages =====
import matplotlib.pyplot as plt
import pandas as pd
import pathlib
import math
import sys
import numpy as np
import scipy.stats as stats

print("Packages imported")
# %%
# ===== Importing external files =====
file_path = r'..\Data\Data.xlsx'

try:
    # Importing Inventory Sheet
    df_inventory = pd.read_excel(file_path, engine="openpyxl", usecols=[0,1,2,3], sheet_name="Inventory")
    
    # Cleaning data: Removing spaces before and after data
    df_inventory.columns = df_inventory.columns.str.strip()
    
    # Convering columns back to correct data type
    df_inventory['Inventory_Order_Date'] = pd.to_datetime(df_inventory['O_Date'].astype(str) + ' ' + df_inventory['O_Time'].astype(str),format='mixed')
    df_inventory['Inventory_Update_Date'] = pd.to_datetime(df_inventory['U_Date'].astype(str) + ' ' + df_inventory['U_Time'].astype(str),format='mixed')
    df_inventory['lead_time_days'] = abs((df_inventory['Inventory_Update_Date'] - df_inventory['Inventory_Order_Date']).dt.total_seconds())/86400
    # Importing Sales Sheet
    df_sales = pd.read_excel(file_path, engine="openpyxl", usecols=[0,1,2], sheet_name="Sales")
    
    # Cleaning data: Removing spaces before and after data
    df_sales.columns = df_sales.columns.str.strip()
    
    # Converting columns back to correct data type
    df_sales['Date'] = pd.to_datetime(df_sales['Date'])
    df_sales['Amount'] = pd.to_numeric(df_sales['Amount'])
    df_sales['Price'] = pd.to_numeric(df_sales['Price'])

    # Removing rows that contain NA data
    df_sales = df_sales.dropna(subset=['Date', 'Amount'])

    # Output if the file was imported sucessfully
    print("Excel file imported successfully!")
        
except FileNotFoundError:

    # Output if the file was not found
    print(f"Error: The file at '{file_path}' could not be found. Check the path.")
    sys.exit()
except Exception as e:

    # Output should another error ocurs
    print(f"An error occurred during import: {e}")
    sys.exit()
# %%
# ===== Creating Data =====
np.random.seed(42)
data_date = pd.date_range(start="2026-01-01", end="2026-12-31", freq="D")
data_demand = np.random.normal(loc=30, scale=6, size=len(data_date))
data_LT = np.random.poisson(lam=8, size=len(data_date))

# Inject artificial demand shifts for demonstration
data_demand[40:80] = np.random.normal(loc= 60, scale=6, size=40)  # High demand period
data_demand[150:200] = np.random.poisson(lam=15, size=50)  # Low demand period

df_sales = pd.DataFrame({"Date": data_date, "Demand": data_demand})
df_inventory = pd.DataFrame({"Date": data_date, "Lead_Time": data_LT})

print("Data generated")

# %%
# ===== Calculating values =====

''' 
calculate_eoq takes in the annual demand, holding cost and setup cost to then calculate the economic order quantity using the 
standard formula: Q = sqrt(2*K*D/h) that is outputted as an integer
'''
def calculate_eoq(annual_demand: int, holding_cost: float, setup_cost: float):
    return int(round(math.sqrt((2*annual_demand*setup_cost)/holding_cost),0))

'''
calculate_rop takes in the daily demand, effective lead time and safety stock to then calculate the re-order point using the 
fomula: ROP = d*Leff + SS that is outputted as an integer
'''
def calculate_rop(daily_demand: int, effective_LT: int, safety_stock: int):
    return int(round((daily_demand*effective_LT)+safety_stock,0))

'''
calculate_ss takes in the service level, standard deviation for the lead time, standard deviation for the demand and lead time 
to then calculate the needed safety stock by first getting the z-value for the inputted service level and then the combined 
standard deviation. The formula used for calculating the safety stock is: SS = z*std*sqrt(L). It is assumed that the demand 
follows a normal distibution. The output is converted to an integer.
'''
def calculate_ss(service_level:float, std_LT: float, std_demand: float, LT: int):
    STD = math.sqrt(std_demand**2 + std_LT**2)
    z = stats.norm.ppf(service_level)
    return int(round(z*STD*math.sqrt(LT),0))

'''
calculate_tc takes in the annual demand, setup cost, order quantity and holding cost to calculate the annual total cost. The 
formula used is: TC = K*D/Q + Q*h/2
'''
def calculate_tc(annual_demand: int, setup_cost: float, order_qty: int, holding_cost: float):
    return (setup_cost*annual_demand/order_qty) + (order_qty*holding_cost/2)

holding_cost = 68.08 # R/u/y
setup_cost = 8595 # R/u
service_level = 0.95
annual_demand = df_sales['Demand'].sum().round(0) # u/y
average_daily_demand = df_sales['Demand'].mean().round(0) # u/d
std_demand = df_sales['Demand'].std()
average_LT = df_inventory['Lead_Time'].mean().round(0) # days
std_LT = df_inventory['Lead_Time'].std()

Q = calculate_eoq(annual_demand, holding_cost, setup_cost) # u
cycle_time = Q/average_daily_demand # days
effective_LT = np.mod(average_LT, cycle_time) # days
SS = calculate_ss(service_level, std_LT, std_demand, average_LT) # u
ROP = calculate_rop(average_daily_demand, effective_LT, SS) # u
TC = calculate_tc(annual_demand, setup_cost, Q, holding_cost) # R

print(f"""Input values:
Holding cost: R{holding_cost}
Setup cost: R{setup_cost}
Service level: {service_level*100}%
Annual demand: {annual_demand} units
Daily demand: {average_daily_demand} units
Standard deviation for demand: {std_demand:.4f}
Lead time: {average_LT} days
Standard deviation for lead time: {std_LT:.4f}

Economic order quantity: {Q} units
Cycle time: {cycle_time:.2f} days
Effective lead time: {effective_LT:.2f} days
Safety stock: {SS} units
Re-order point: {ROP} units
Annual cost: R{TC:.2f}""")

# ===== Simulation =====
starting_inventory = 400 # units
df_sim = df_sales[['Date', 'Demand']].copy()
df_sim['Replenish'] = 0
df_sim.loc[0,'Inventory'] = starting_inventory - df_sim.loc[0,'Demand'] + df_sim.loc[0, 'Replenish']
for i in range(1, len(df_sim)):

    df_sim.loc[i,'Inventory'] = max(df_sim.loc[i-1, 'Inventory'] + df_sim.loc[i, 'Replenish'] - df_sim.loc[i,'Demand'], 0)

    if (df_sim.loc[i, 'Inventory'] <= ROP) and \
       (df_sim.loc[i:min(i+int(round(effective_LT,0)), len(df_sim)-1), 'Replenish'].sum()==0) and \
       (i + int(round(effective_LT,0)) < len(df_sim)-1):
        df_sim.loc[i+int(round(effective_LT,0)), 'Replenish'] = Q

# %%
plt.figure(1, figsize=(12, 6))
plt.plot(df_sim['Date'], df_sim['Inventory'])
plt.axhline(y=ROP, color='crimson', linestyle='--', label=f'Reorder Point (ROP = {ROP})')
plt.axhline(y=SS, color='gray', linestyle='--', label=f'Safety Stock (SS = {SS})')
plt.axhline(y=0, color='black', linestyle='-')

plt.title('Inventory Simulation Over Time', fontsize=14, fontweight='bold')
plt.xlabel('Date', fontsize=12)
plt.ylabel('Inventory Units', fontsize=12)
plt.legend(loc='upper right')
plt.grid(True, linestyle=':', alpha=0.6)
plt.show()

# %%
