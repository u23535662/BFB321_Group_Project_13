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
# ===== Importing external files =====

# Creating custom file path
file_path = input("Enter file path for Excell file:") or r"C:\Users\User\OneDrive\UP\Y4\S2\BFB321\Code\BFB321_Group_Project_13\Backend\Data.xlsx"

try:
    # Importing file
    df = pd.read_excel(file_path, engine="openpyxl", usecols=[0,1])
    # Cleaning data: Removing spaces before and after data
    df.columns = df.columns.str.strip()
    df['Inventory_Order_Date'] = pd.to_datetime(df['Inventory_Order_Date'])
    df['Inventory_Update_Date'] = pd.to_datetime(df['Inventory_Update_Date'])

    print("Excel file imported successfully!")
    print(df.head())

except FileNotFoundError:
    print(f"Error: The file at '{file_path}' could not be found. Check the path.")
except Exception as e:
    print(f"An error occurred during import: {e}")

# ===== Calculating Lead time =====
df['lead_time_days'] = (df['Inventory_Update_Date'] - df['Inventory_Order_Date']).dt.total_seconds()/ (24 * 3600)
avg_lead_time = df['lead_time_days'].mean()
std_lead_time = df['lead_time_days'].std()
Z = stats.norm.ppf(0.95)

avg_daily_demand = 120.0
std_daily_demand = 15.0 

variance = (avg_lead_time * (std_daily_demand ** 2)) + ((avg_daily_demand ** 2) * (std_lead_time ** 2))
safety_stock = Z * sy.sqrt(variance)

reorder_point = (avg_daily_demand * avg_lead_time) + safety_stock

print(f"Dynamic Reorder Point: {round(reorder_point)} units")

# ===== Plotting lead time data =====
plt.figure(1)
plt.hist(df['lead_time_days'])
plt.title("Lead times histogram")
plt.xlabel("Lead times")
plt.ylabel("Frequency")

plt.figure(2)
sorted_df = df.sort_values(by="Inventory_Update_Date")
plt.plot(sorted_df['Inventory_Update_Date'], sorted_df['lead_time_days'])
plt.plot(sorted_df['Inventory_Update_Date'], 20)
plt.show()