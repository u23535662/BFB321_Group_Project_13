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
# ===== Creating a function for sectioning the demand based on a selector =====
def segment_demand(selection: str, df_demand: pd.DataFrame):
    
    # Copies data frame to prevent mutation of the origional
    df = df_demand[['Date', 'Amount']].copy()

    # Groups data by selection
    if selection == 'Daily':
        df.set_index('Date', inplace=True)

        # Sums the amount columns for same day
        df = df.resample('D')['Amount'].agg(['sum', 'std']).reset_index()

        # Renames the columns to make more sence
        df = df.rename(columns={'Date':'Day', 'sum':'Demand', 'std':'STD Demand'})
        return df
    elif selection == 'Weekly':
        df.set_index('Date', inplace=True)

        # Sums the amount columns for same week
        df = df.resample('W')['Amount'].agg(['sum', 'std']).reset_index()
        # Converts the date column to only display the day the week started on
        df['Date'] = df['Date'].dt.weekday

        # Renames the columns to make more sence
        df = df.rename(columns={'Date':'Week starting on', 'sum':'Demand', 'std':'STD Demand'})
        return df
    elif selection == 'Monthly':
        df.set_index('Date', inplace=True)

        # Sums the amount columns for same month
        df = df.resample('ME')['Amount'].agg(['sum', 'std']).reset_index()

        # Converts the date column to only display the month
        df['Date'] = df['Date'].dt.month

        # Renames the columns to make more sence
        df = df.rename(columns={'Date':'Month', 'sum':'Demand', 'std':'STD Demand'})
        return df
    elif selection == 'Yearly':
        df.set_index('Date', inplace=True)

        # Sums the amount columns for same year
        df = df.resample('YE')['Amount'].agg(['sum', 'std']).reset_index()

        # Converts the date column to only display the year
        df['Date'] = df['Date'].dt.year

        # Renames the columns to make more sence
        df = df.rename(columns={'Date':'Year', 'sum':'Demand', 'std':'STD Demand'})
        return df
    else:
        return "Selection should be: 'Daily', 'Weekly', 'Monthly' or 'Yearly'"

print("Segment_demand function created")

# %%
# ===== Creating a function to claculate EOQ =====
def calculate_eoq(annual_demand: int, setup_cost: float, holding_cost: float):
    # Uses the EOQ fomula and rounds up the final value 
    return np.ceil(np.sqrt((2*annual_demand*setup_cost)/holding_cost))


# ===== Creating a function to calculate ROP =====
def calculate_ROP(demand, effective_leadtime, safetystock):
    return demand*effective_leadtime + safetystock

print("EOQ and ROP functions created")



# %%
# ===== Creating a function for sectioning the lead time based on a selector =====
def segment_LT(selection: str, df_leadTime: pd.DataFrame):

    # Copies data frame to prevent mutation of the origional
    df = df_inventory[['Inventory_Order_Date', 'lead_time_days']].copy()

    # Groups data by selection
    if selection == 'Daily':
        df.set_index('Inventory_Order_Date', inplace=True)

        # Sums the amount columns for same day
        df = df.resample('D')['lead_time_days'].agg(['mean', 'std']).reset_index()

        # Renames the columns to make more sence
        df = df.rename(columns={'Inventory_Order_Date':'Day', 'mean':'Lead Time', 'std':'STD Lead Time'})
        return df
    elif selection == 'Weekly':
        df.set_index('Inventory_Order_Date', inplace=True)

        # Sums the amount columns for same week
        df = df.resample('W')['lead_time_days'].agg(['mean', 'std']).reset_index()
        # Converts the date column to only display the day the week started on
        df['Inventory_Order_Date'] = df['Inventory_Order_Date'].dt.weekday

        # Renames the columns to make more sence
        df = df.rename(columns={'Inventory_Order_Date':'Week starting on', 'mean':'Lead Time', 'std':'STD Lead Time'})
        return df
    elif selection == 'Monthly':
        df.set_index('Inventory_Order_Date', inplace=True)

        # Sums the amount columns for same month
        df = df.resample('ME')['lead_time_days'].agg(['mean', 'std']).reset_index()

        # Converts the date column to only display the month
        df['Inventory_Order_Date'] = df['Inventory_Order_Date'].dt.month

        # Renames the columns to make more sence
        df = df.rename(columns={'Inventory_Order_Date':'Month', 'mean':'Lead Time', 'std':'STD Lead Time'})
        return df
    elif selection == 'Yearly':
        df.set_index('Inventory_Order_Date', inplace=True)

        # Sums the amount columns for same year
        df = df.resample('YE')['lead_time_days'].agg(['mean', 'std']).reset_index()

        # Converts the date column to only display the year
        df['Inventory_Order_Date'] = df['Inventory_Order_Date'].dt.year

        # Renames the columns to make more sence
        df = df.rename(columns={'Inventory_Order_Date':'Year', 'mean':'Lead Time', 'std':'STD Lead Time'})
        return df
    else:
        return "Selection should be: 'Daily', 'Weekly', 'Monthly' or 'Yearly'"

print("Segment_LT function created")
# %%
# ===== Input values for EOQ calculation =====
working_days = 300 # Number of days the company is active in a year
working_weeks = 51 # Number of weeks the company is active in a year

holding_cost = 500 # R/u/y Cost of holding the product
setup_cost = 400 # R/u Cost to buy the product

service_level = 0.95
z = stats.norm.ppf(service_level)
selection = 'Daily'

# ===== Testing =====
dates = pd.date_range(start='2026-01-01', end='2026-12-31', freq='D')
df = pd.DataFrame({'Date':dates})

df['Demand'] = segment_demand(selection, df_sales)['Demand'].values[0:len(df['Date'])]
df['Demand STD'] = segment_demand(selection, df_sales)['STD Demand'].values[0:len(df['Date'])]
df['Demand STD'] = df['Demand STD'].fillna(0)
df['Lead Time STD'] = segment_LT(selection, df_inventory)['STD Lead Time'].values[0:len(df['Date'])]
df['Lead Time STD'] = df['Lead Time STD'].fillna(0)
df['STD'] = np.sqrt((df['Lead Time STD']**2) + (df['Demand STD']**2))
df = df.drop(columns=['Demand STD', 'Lead Time STD'])
df['EOQ'] = calculate_eoq(df['Demand']*working_days, setup_cost, holding_cost)
df['Cycle Time(t*)'] = round(df['EOQ']/df['Demand'],0)
df['Cycle Time(t*)'] = df['Cycle Time(t*)'].fillna(0)
df['Lead Time'] = segment_LT(selection, df_inventory)['Lead Time'].values[0:len(df['Date'])].round(0)
df['Safety Stock'] = round(z*df['STD']*np.sqrt(df['Lead Time']), 0)
df['Effective lead time'] = np.mod(df['Lead Time'], df['Cycle Time(t*)'])
df['Effective lead time'] = df['Effective lead time'].fillna(0)
df['ROP'] = round(calculate_ROP(df['Demand'], df['Effective lead time'], df['Safety Stock']))


df['replenish'] = 0
df.loc[0, 'Inventory'] = 20 - df.loc[0, 'Demand'] + df.loc[0, 'replenish']

for i in range(1, len(df['Date'])):
    # 1. Calculate today's inventory first (runs for every iteration)
    df.loc[i, 'Inventory'] = df.loc[max(0, i-1), 'Inventory'] - df.loc[i, 'Demand'] + df.loc[i, 'replenish']
    
    el_t = int(df.loc[i, 'Effective lead time'])
    
    # 2. Check conditions cleanly using the already-calculated inventory
    if (df.loc[i, 'Inventory'] <= df.loc[i, 'ROP']) and \
       (sum(df.loc[max(0, i - el_t):i, 'replenish']) == 0) and \
       (i + el_t <= len(df['Date']) - 1):
        
        # Trigger replenishment arriving in the future
        df.loc[i + el_t, 'replenish'] = df.loc[i, 'EOQ']
print(df)
# %%
D = segment_demand('Yearly', df_sales).loc[0,'Demand']
D_STD = segment_demand('Yearly', df_sales).loc[0,'STD Demand']
LT = segment_LT('Yearly', df_inventory).loc[0,'Lead Time']
LT_STD = segment_LT('Yearly', df_inventory).loc[0,'STD Lead Time']
Q = calculate_eoq(D, setup_cost, holding_cost)
CT = Q/D
Leff = np.mod(LT, CT)
STD = np.sqrt((D_STD**2) + (LT_STD**2))
SS = z*STD*np.sqrt(LT)
ROP = calculate_ROP(D/working_days, Leff, SS)

df_2 = pd.DataFrame({'Date':dates})

df_2['Demand'] = segment_demand(selection, df_sales)['Demand'].values[0:len(df['Date'])]

df_2['replenish'] = 0
df_2.loc[0, 'Inventory'] = 20 - df_2.loc[0, 'Demand'] + df_2.loc[0, 'replenish']

for i in range(1, len(df_2['Date'])):
    # 1. Calculate today's inventory first (runs for every iteration)
    df_2.loc[i, 'Inventory'] = df_2.loc[max(0, i-1), 'Inventory'] - df_2.loc[i, 'Demand'] + df_2.loc[i, 'replenish']
    
    el_t = int(Leff)
    
    # 2. Check conditions cleanly using the already-calculated inventory
    if (df.loc[i, 'Inventory'] <= ROP) and \
       (sum(df_2.loc[max(0, i - el_t):i, 'replenish']) == 0) and \
       (i + el_t <= len(df_2['Date']) - 1):
        
        # Trigger replenishment arriving in the future
        df_2.loc[i + el_t, 'replenish'] = Q
# %%
plt.figure(1)
plt.plot(df_2['Date'], df_2['Demand'])

plt.figure(2)
plt.plot(df_2['Date'], df_2['Inventory'])
plt.plot(df['Date'], df['Inventory'])
plt.show()
# %%
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# # ---------------------------------------------------------
# # 1. SAMPLE DATA SETUP (Replace this with your actual dataframe: df)
# # ---------------------------------------------------------
# np.random.seed(42)
# date_rng = pd.date_range(start="2026-01-01", end="2026-01-10", freq="h")
# demand_val = np.random.poisson(lam=50, size=len(date_rng))

# # Inject artificial demand shifts for demonstration
# demand_val[40:80] = np.random.poisson(lam=120, size=40)  # High demand period
# demand_val[150:200] = np.random.poisson(
#     lam=15, size=50
# )  # Low demand period

# df = pd.DataFrame({"Date": date_rng, "Demand": demand_val})

# # ---------------------------------------------------------
# # 2. FEATURE ENGINEERING (Behavioral Attributes)
# # ---------------------------------------------------------
# # Ensure datetime format and sort
# df["Date"] = pd.to_datetime(df["Date"])

df = df_sales[['Date', 'Amount']].copy()
df = df.sort_values("Date").reset_index(drop=True)
df["Date"] = pd.to_datetime(df["Date"])
df = df.set_index("Date")
# Use rolling window statistics to capture demand behavior (e.g., 6-hour window)
window_size = "30D"
df["Rolling_Mean"] = (
    df["Amount"].rolling(window=window_size, min_periods=1).mean().round(0)
)
df["Rolling_Std"] = (
    df["Amount"].rolling(window=window_size, min_periods=1).std().fillna(0)
)

# ---------------------------------------------------------
# 3. CLUSTERING DEMAND BEHAVIORS
# ---------------------------------------------------------
# Scale features for clustering
features = df[["Rolling_Mean", "Rolling_Std"]]
scaler = StandardScaler()
scaled_features = scaler.fit_transform(features)

# Define number of behavioral states (e.g., 3: Low, Medium, High)
n_clusters = 3
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
df["Behavior_Cluster"] = kmeans.fit_predict(scaled_features)

# ---------------------------------------------------------
# 4. GROUP CONSECUTIVE TIMESTAMPS INTO DATE RANGES
# ---------------------------------------------------------
# Identify changes in cluster state to create distinct blocks
df["Cluster_Change"] = (
    df["Behavior_Cluster"] != df["Behavior_Cluster"].shift()
).cumsum()

# Aggregate into date ranges
date_ranges = (
    df.groupby("Cluster_Change")
    .agg(
        Start_Date=("Date", "min"),
        End_Date=("Date", "max"),
        Behavior_Cluster=("Behavior_Cluster", "first"),
        Average_Demand=("Amount", "mean"),
    )
    .reset_index(drop=True)
)

print(date_ranges.head(10))
# %%
plt.figure(3)
plt.plot(df['Date'], df['Amount'])
for i in range(0, len(date_ranges['Start_Date'])):
    plt.axvline(date_ranges.loc[i, 'Start_Date'], color = 'red')
plt.show()
# %%
