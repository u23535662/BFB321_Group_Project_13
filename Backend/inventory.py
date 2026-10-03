# This code has everything to do with the inventory side of the project
# Ideas: EOQ, inventory forecasting, inventory warnings, trends graphs, ABC classification
# Methods of importing data: Excell, CSV

# ===== Imporing packages =====
import sympy as sy
import matplotlib.pyplot as plt
import pandas as pd
import scipy.stats as stats
import pathlib
from datetime import date
from fitter import Fitter
import sys

from file_import import import_file

# ===== Importing external files =====
# Creating custom file path
script_dir = pathlib.Path(__file__).parent
default = script_dir / "Data.xlsx"
file_path = input("Enter file path for Excell file:") or default

try:
    # Importing Inventory Sheet
    df_inventory = pd.read_excel(file_path, engine="openpyxl", usecols=[0,1,2,3], sheet_name="Inventory")
    # Cleaning data: Removing spaces before and after data
    df_inventory.columns = df_inventory.columns.str.strip()
    # Convering columns back to correct data type
    df_inventory['Inventory_Order_Date'] = pd.to_datetime(df_inventory['O_Date'].astype(str) + ' ' + df_inventory['O_Time'].astype(str))
    df_inventory['Inventory_Update_Date'] = pd.to_datetime(df_inventory['U_Date'].astype(str) + ' ' + df_inventory['U_Time'].astype(str))
    # Importing Sales Sheet
    df_sales = pd.read_excel(file_path, engine="openpyxl", usecols=[0,1,2], sheet_name="Sales")
    # Cleaning data: Removing spaces before and after data
    df_sales.columns = df_sales.columns.str.strip()
    # Converting columns back to correct data type
    df_sales['Date'] = pd.to_datetime(df_sales['Date'])
    df_sales['Amount'] = pd.to_numeric(df_sales['Amount'])
    df_sales['Unit_Price'] = pd.to_numeric(df_sales['Price'])
    print("Excel file imported successfully!")
        
except FileNotFoundError:
    print(f"Error: The file at '{file_path}' could not be found. Check the path.")
    sys.exit()
except Exception as e:
    print(f"An error occurred during import: {e}")
    sys.exit()

# ===== Calculating Lead time =====
df_inventory['lead_time_days'] = (df_inventory['Inventory_Update_Date'] - df_inventory['Inventory_Order_Date']).dt.total_seconds()/ (24 * 3600)
avg_lead_time = df_inventory['lead_time_days'].mean()
std_lead_time = df_inventory['lead_time_days'].std()
Z = stats.norm.ppf(0.95)


avg_daily_demand = 120.0
std_daily_demand = 15.0 

variance = (avg_lead_time * (std_daily_demand ** 2)) + ((avg_daily_demand ** 2) * (std_lead_time ** 2))
safety_stock = Z * sy.sqrt(variance)

reorder_point = (avg_daily_demand * avg_lead_time) + safety_stock

print(f"Dynamic Reorder Point: {round(reorder_point)} units")

# %%
# ===== Plotting lead time data =====
plt.figure(1)
plt.hist(df_inventory['lead_time_days'])
plt.title("Lead times histogram")
plt.xlabel("Lead times")
plt.ylabel("Frequency")

plt.figure(2)
sorted_df = df_inventory.sort_values(by="Inventory_Update_Date")
plt.plot(sorted_df['Inventory_Update_Date'], sorted_df['lead_time_days'])

f = Fitter(df_inventory['lead_time_days'], distributions=['norm', 'uniform', 'expon'])
f.fit()
print(f.summary)

# Group by date and sum the amounts
daily_sales = df_sales.groupby(df_sales['Date'].dt.date)['Amount'].sum()

# Extract as lists
lu_dates = daily_sales.index.tolist()
lu_amount = daily_sales.values.tolist()

plt.figure(3)
plt.plot(lu_dates,lu_amount)
plt.title("Daily demand")
plt.xlabel("Date")
plt.ylabel("Amount")

plt.figure(4)
plt.hist(lu_amount)
plt.show()