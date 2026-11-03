import os
from flask import (Flask, flash, redirect, render_template, request, url_for)
import db
import models
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY","dev-only-change-me")

db.init_app(app)

@app.route('/')
def index():
    # This runs inside an active request/application context
    product = "1"
    df_products = pd.DataFrame(models.select_product(product))
    std_lt = float(db.query_all("SELECT std(i.inventory_update_date - i.inventory_order_date) AS std_d FROM Inventory_Order i WHERE i.product_id = %s", product))
    std_demand = float(db.query_all("SELECT std(s.sold_quantity) AS std_s FROM Sale s WHERE s.product_id = %s", product))
    avg_Lt = float(db.query_all("SELECT avg(i.inventory_update_date - i.inventory_order_date) AS avg_d FROM Inventory_Order i WHERE i.product_id = %s", product))
    ss = models.calculate_ss(0.95,std_lt, std_demand, avg_Lt)
    eoq = models.calculate_eoq(int(df_products['Demand'].sum()), 20, 300)
    ct = eoq/df_products['Demand'].mean().round(0)
    effective_Lt = np.mod(avg_Lt, ct)
    rop = models.calculate_rop(int(round(df_products['Demand'].mean(),0)), effective_Lt, ss)
    df_result = models.simulation_eoq(200, 0, df_products['Date'], df_products['Demand'], rop, eoq, effective_Lt)

    plt.figure(1, figsize=(12, 6))
    plt.plot(df_result['Date'], df_result['Inventory'], color="#13BA75")
    plt.axhline(y=rop, color="#1818B8", linestyle='--', label=f'Reorder Point (ROP = {rop})')
    plt.axhline(y=ss, color='red', linestyle='--', label=f'Safety Stock (SS = {ss})')
    plt.axhline(y=0, color="#000000", linestyle='-')


    plt.title(f'Inventory simulation for {product}', fontsize=14, fontweight='bold', color= "#000000")
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Inventory', fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, linestyle=':', alpha=0.6, color= "#363636")

    plt.tight_layout()
    plt.savefig('static/simulation_plot.png')
    plt.close() # Free up memory

    # 4. Return HTML displaying the image
    html_page = f"""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Inventory Simulation</title>
      </head>
      <body style="font-family: Arial, sans-serif; text-align: center; background-color: #f9f9f9; margin: 30px;">
        <h1 style="color: #333;">Inventory Simulation for Product 1</h1>
        
        <!-- Displaying the plot image -->
        <div style="background: white; padding: 20px; display: inline-block; box-shadow: 0px 0px 10px rgba(0,0,0,0.1); border-radius: 8px;">
          <img src="/static/simulation_plot.png" alt="Inventory Simulation Plot" style="max-width: 100%; height: auto;">
        </div>

        <p style="margin-top: 20px; color: #666;">ROP: {rop} | EOQ: {eoq}</p>
      </body>
    </html>
    """
    return html_page

if __name__ == '__main__':
    app.run(debug=True)