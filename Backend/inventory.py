# This code has everything to do with the inventory side of the project
# Ideas: EOQ, inventory forecasting, inventory warnings, trends graphs, ABC classification
# Methods of importing data: Excell, CSV
# %%
# ===== Imporing packages =====
import sympy as sy
import matplotlib.pyplot as plt
import pandas as pd
import scipy.stats as stats
import pathlib
from datetime import date
from fitter import Fitter
import math
import sys

CURRENT_INVENTORY_POSITION_UNITS = None
SERVICE_LEVEL = 0.95
ORDER_COVERAGE_DAYS = 30


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
    df_inventory['lead_time_days'] = (df_inventory['Inventory_Update_Date'] - df_inventory['Inventory_Order_Date']).dt.total_seconds() / 86400
    # Importing Sales Sheet
    df_sales = pd.read_excel(file_path, engine="openpyxl", usecols=[0,1,2], sheet_name="Sales")
    # Cleaning data: Removing spaces before and after data
    df_sales.columns = df_sales.columns.str.strip()
    # Converting columns back to correct data type
    df_sales['Date'] = pd.to_datetime(df_sales['Date'])
    df_sales['Amount'] = pd.to_numeric(df_sales['Amount'])
    df_sales['Unit_Price'] = pd.to_numeric(df_sales['Price'])
    df_sales = df_sales.dropna(subset=['Date', 'Amount'])
    print("Excel file imported successfully!")
        
except FileNotFoundError:
    print(f"Error: The file at '{file_path}' could not be found. Check the path.")
    sys.exit()
except Exception as e:
    print(f"An error occurred during import: {e}")
    sys.exit()
# %%


# %%
# ===== Forecasting and plotting lead time data =====
df_inventory = df_inventory.sort_values(by='Inventory_Order_Date')
valid_lead_times = df_inventory.loc[df_inventory['lead_time_days'] >= 0, 'lead_time_days']
invalid_count = len(df_inventory) - len(valid_lead_times)
valid_inventory = df_inventory.loc[df_inventory['lead_time_days'] >= 0]

if valid_lead_times.empty:
    print("No valid non-negative lead times are available for a forecast.")
    sys.exit()

monthly_means = valid_inventory.groupby(
    valid_inventory['Inventory_Order_Date'].dt.to_period('M')
)['lead_time_days'].mean()
monthly_dates = monthly_means.index.to_timestamp()
trend = stats.linregress(range(len(monthly_means)), monthly_means.to_numpy())
trend_values = trend.intercept + trend.slope * range(len(monthly_means))
trend_direction = 'decreasing' if trend.slope < 0 else 'increasing'

forecast_start = (
    df_inventory['Inventory_Order_Date'].max().to_period('M').to_timestamp()
    + pd.offsets.MonthBegin(1)
)
forecast_dates = pd.date_range(start=forecast_start, periods=12, freq='MS')
forecast_mean = valid_lead_times.mean()
df_forecast = pd.DataFrame({
    'Forecast_Date': forecast_dates,
    'Forecast_Lead_Time_Days': forecast_mean,
})

if invalid_count:
    print(f"Excluded {invalid_count} record(s) with update times before order times.")
print(f"12-month average lead-time forecast: {forecast_mean:.2f} days")
print(
    f"Monthly trend: {trend_direction} by {abs(trend.slope):.2f} days/month "
    f"(R-squared: {trend.rvalue ** 2:.2f}, p-value: {trend.pvalue:.4g})."
)
if trend.pvalue < 0.05:
    print("The linear trend is statistically significant at the 5% level.")
else:
    print("No statistically significant linear trend was detected at the 5% level.")
print(df_forecast.to_string(index=False))

# ===== Demand forecast and replenishment policy =====
daily_demand = (
    df_sales.groupby(df_sales['Date'].dt.normalize())['Amount']
    .sum()
    .asfreq('D', fill_value=0)
)
average_daily_demand = daily_demand.mean()
daily_demand_std = daily_demand.std()
lead_time_std = valid_lead_times.std()
if pd.isna(daily_demand_std):
    daily_demand_std = 0
if pd.isna(lead_time_std):
    lead_time_std = 0

mean_lead_time = valid_lead_times.mean()
lead_time_demand = average_daily_demand * mean_lead_time
lead_time_demand_std = math.sqrt(
    mean_lead_time * daily_demand_std ** 2
    + average_daily_demand ** 2 * lead_time_std ** 2
)
safety_stock_units = stats.norm.ppf(SERVICE_LEVEL) * lead_time_demand_std
reorder_point_units = math.ceil(lead_time_demand + safety_stock_units)
order_quantity_at_trigger = math.ceil(average_daily_demand * ORDER_COVERAGE_DAYS)
target_stock_units = reorder_point_units + order_quantity_at_trigger

sales_monthly = daily_demand.resample('MS').sum()
demand_forecast_start = (
    daily_demand.index.max().to_period('M').to_timestamp()
    + pd.offsets.MonthBegin(1)
)
demand_forecast_dates = pd.date_range(
    start=demand_forecast_start, periods=12, freq='MS'
)
forecast_monthly_units = pd.Series(
    [average_daily_demand * forecast_date.days_in_month for forecast_date in demand_forecast_dates],
    index=demand_forecast_dates,
    name='Forecast_Units',
)

print(f"Average daily demand: {average_daily_demand:.2f} units")
print(f"Average replenishment lead time: {mean_lead_time:.2f} days")
print(f"Estimated safety stock ({SERVICE_LEVEL:.0%} service level): {math.ceil(safety_stock_units)} units")
print(f"Reorder point: {reorder_point_units} units")
print(f"Order quantity at reorder point ({ORDER_COVERAGE_DAYS} days of demand): {order_quantity_at_trigger} units")
print(f"Order-up-to level: {target_stock_units} units")
print("12-month sales-demand forecast:")
print(forecast_monthly_units.rename_axis('Forecast_Month').to_frame().to_string())

if CURRENT_INVENTORY_POSITION_UNITS is None:
    print(
        "Set CURRENT_INVENTORY_POSITION_UNITS to on-hand + on-order - backorders "
        "to calculate the next order date and immediate order quantity."
    )
else:
    current_inventory_position = float(CURRENT_INVENTORY_POSITION_UNITS)
    forecast_origin = daily_demand.index.max() + pd.Timedelta(days=1)
    if current_inventory_position <= reorder_point_units:
        recommended_order_date = forecast_origin
        recommended_order_quantity = math.ceil(
            max(0, target_stock_units - current_inventory_position)
        )
        print(
            f"Reorder now ({recommended_order_date.date()}): "
            f"order {recommended_order_quantity} units."
        )
    else:
        days_until_reorder = math.ceil(
            (current_inventory_position - reorder_point_units) / average_daily_demand
        )
        recommended_order_date = forecast_origin + pd.Timedelta(days=days_until_reorder)
        print(
            f"Estimated reorder date: {recommended_order_date.date()}; "
            f"order {order_quantity_at_trigger} units at the reorder point."
        )

plt.figure(3, figsize=(12, 6))
plt.bar(
    sales_monthly.index, sales_monthly.values, width=20,
    label='Observed monthly sales', color='tab:blue',
)
plt.bar(
    forecast_monthly_units.index, forecast_monthly_units.values, width=20,
    label='12-month demand forecast', color='tab:orange',
)
plt.axvline(demand_forecast_start, color='black', linestyle=':', label='Forecast starts')
plt.title("Monthly Sales and 12-Month Demand Forecast")
plt.xlabel("Month")
plt.ylabel("Units")
plt.legend()
plt.grid(True, axis='y', alpha=0.3)

plt.figure(4, figsize=(10, 5))
policy_labels = [
    'Lead-time demand',
    'Safety stock',
    'Reorder point',
    f'{ORDER_COVERAGE_DAYS}-day order quantity',
    'Order-up-to level',
]
policy_values = [
    lead_time_demand,
    safety_stock_units,
    reorder_point_units,
    order_quantity_at_trigger,
    target_stock_units,
]
plt.barh(policy_labels, policy_values, color=[
    'tab:blue', 'tab:green', 'tab:red', 'tab:orange', 'tab:purple',
])
if CURRENT_INVENTORY_POSITION_UNITS is not None:
    plt.axvline(
        current_inventory_position, color='black', linestyle='--',
        label='Current inventory position',
    )
    plt.legend()
plt.title("Replenishment Policy (Units)")
plt.xlabel("Units")
plt.grid(True, axis='x', alpha=0.3)

plt.figure(1)
plt.scatter(
    df_inventory['Inventory_Order_Date'], df_inventory['lead_time_days'],
    label='Observed lead time',
)
plt.plot(
    df_forecast['Forecast_Date'], df_forecast['Forecast_Lead_Time_Days'],
    marker='o', linestyle='--', color='tab:red', label='12-month average forecast',
)
plt.title("Lead Time and 12-Month Forecast")
plt.xlabel("Order date")
plt.ylabel("Lead time (days)")
plt.legend()
plt.grid(True, alpha=0.3)

plt.figure(2)
plt.plot(monthly_dates, monthly_means, marker='o', label='Monthly average lead time')
plt.plot(monthly_dates, trend_values, linestyle='--', color='tab:orange', label='Linear trend')
plt.title("Monthly Lead-Time Trend")
plt.xlabel("Order month")
plt.ylabel("Average lead time (days)")
plt.legend()
plt.grid(True, alpha=0.3)

plt.show()
# %%
