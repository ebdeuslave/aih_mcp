import os
from datetime import datetime
import csv

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    }
 
def createProductsFile(data:dict) -> dict:
    """
    Create a csv file for the supplier and write the products data in it
    Args:
        data: the data to write in the csv file contains the supplier name and the products data
    Returns:
        None
    """
    try:
        if not os.path.exists("products"):
            os.makedirs("products")
        
        for supplier, product_data in data.items():
            product_data = dict(sorted(product_data.items(), key=lambda x: x[0])) # Sort by product name
            filename = f"products/{supplier}_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"
            with open(filename, "w") as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Quantity", "Price"])
                for product_name, product_data in product_data.items():
                    writer.writerow([product_name, product_data["quantity"], product_data["price"]])
    
        return {
            "hasError": False,
            "content": "CSV files created successfully"
        }
    
    except Exception as e:
        return {
            "hasError": True,
            "content": str(e)       
    }
