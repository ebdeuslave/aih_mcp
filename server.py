from mcp.server.fastmcp import FastMCP
import httpx
import os
import webbrowser
import requests
import mysql.connector
from mysql.connector import Error
import sqlite3
import paramiko
from dotenv import load_dotenv


load_dotenv()
API_KEY = os.getenv("api_key")
SECURE_KEY = os.getenv("secure_key")
headers = {
   "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}

available_stores = ["parapharma", "coinpara", "allopara", "parabio"]

mcp = FastMCP("mcp_demo")

@mcp.tool()
def getOrders(store: str,from_date: str, to_date: str, from_time="00:00:00", payment:str="all", current_state:list=[]) -> list|int:
    """
    Get the orders ids for a giving date
    Args:
        store: the given store name
        from_date: The starting date (format: YYYY-MM-DD)
        to_date: The ending date (format: YYYY-MM-DD) NOTE that the to_date is excluded
        from_time: The starting time (format: "HH:MM:SS")
        payment: payment mode (only cod and cmi, cod means cash on delivery, cmi means prepaid, all is the default means both)
        current_state: order current status
        status
    Returns:
        The list of orders ids
    """
    
    available_payment = {
        "cod": "Paiement comptant à la livraison (Cash on delivery)",
        "cmi": "cmi"
    }

    if store not in available_stores:
        return f"Store {store} is not available"

    if store == "parabio":
        store = "www.parabio"

    url = f"https://{store}.ma/api/orders?filter[invoice_date]=[{from_date} {from_time},{to_date}]&output_format=JSON"

    if payment != "all" and payment in available_payment:
        url = f"https://{store}.ma/api/orders?filter[invoice_date]=[{from_date} {from_time},{to_date}]&filter[payment]=[{payment}]&output_format=JSON"
  

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code == 200:
            return response.json()["orders"]
        
        return response.status_code
    
    
@mcp.tool()
def getOrderDetails(store:str, id: int) -> dict|int:
    """
     Get the order details
    Args:
        store: the given store name
        id: order id
    Returns:
        dict contains all order's info including products names/ids, total paid, payment type and more if successed otherwise a status code number
    """
    
    if store not in available_stores:
        return f"Store {store} is not available"

    if store == "parabio":
        store = "www.parabio"

    url = f"https://{store}.ma/api/orders/{id}?output_format=JSON"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code == 200:
            return response.json()["order"]
        
        return response.status_code
    

@mcp.tool()
def getProductSupplier(id:int) -> str:
    """
     Get the product supplier
    Args:
        id: product id
    Returns:
        The supplier name
    """
    
    url = f"https://parapharma.ma/api/products/{id}?output_format=JSON"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code == 200:
            supplier_id = response.json()["product"]["id_supplier"]
            return getSupplierName(supplier_id)
        
        return response.status_code    
    

def getSupplierName(id) -> str:
    """
     Get the supplier name
    Args:
        id: supplier id
    Returns:
        The supplier name
    """
    with httpx.Client(http2=True, headers=headers) as client:
        url = f"https://parapharma.ma/api/suppliers/{id}?output_format=JSON"
        response = client.get(url, auth=(API_KEY, ""), headers=headers)
        if response.status_code == 200:
            return response.json()["supplier"]["name"]
        
    return f"Error => {response.content}"


@mcp.tool()
def getSuppliers() -> list:
    """Get all suppliers
    """
    suppliers = []
    with httpx.Client(http2=True, headers=headers) as client:
        url = "https://parapharma.ma/api/suppliers?output_format=JSON"
        response = client.get(url, auth=(API_KEY, ""), headers=headers)
        if response.status_code == 200:
            ids = response.json()["suppliers"]
            for id in ids:
                suppliers.append(id)
    
    return suppliers


@mcp.tool()
def downloadInvoice(store:str, order_id:int) -> str:
    """
    Download the invoice PDF and open it
    Args:
        store: store name
        id: order id
    Returns:
        message
    """
    # if not os.path.isdir("invoices"):
    #     os.mkdir("invoices")
    
    if store not in available_stores:
        return f"Store {store} is not available"

    if store == "parabio":
        store = "www.parabio"
        
    url = f"https://{store}.ma/generatePDF.php?id_order={order_id}&secure_key={SECURE_KEY}"
    
    webbrowser.open(url)
    
    # with httpx.Client(http2=True, headers=headers) as client:
        
        # response = client.get(url)
        # if response.status_code == 200 and response.headers.get("Content-Type") == "application/pdf":
            # pdf_file = Path(f"invoices/{order_id}.pdf")
            # pdf_file.write_bytes(response.content)
            # subprocess.Popen([os.path.abspath(pdf_file)], shell=True)
            # webbrowser.open(f"file:///{os.path.abspath(pdf_file)}")
            
            
    return f"Invoice {order_id} downloaded"
        

@mcp.tool()
def prestashopWebserviceAutorization(store:str) -> list:
    """
    Get prestashop api autorized enpoints of my api key
    Args:
        store: the store name
    Returns:
        a list of str
    """
    
    if store not in available_stores:
        return ["Error", f"Store {store} is not available"]

    if store == "parabio":
        store = "www.parabio"
    
    response = requests.get(f"https://{store}.ma/api/?output_format=JSON", auth=(API_KEY, ""))
    
    if not response.status_code == 200:
        return [response.status_code, response.content]
        
    return response.json()
    
    
@mcp.tool()
def connectionToDB(command:str) -> list|str:
    """
    Connection to mysql database and fetch data\n
    **IMPORTANT**:
        DO NOT USE ANY COMMAND THAT CHANGE RECORDS IN THE DATABASE USE FETCH REQUESTS ONLY
    Args:
        command: the command to run in mysql (IMPORTANT: DO NOT END COMMAND WITH ";" MYSQL CONNECTOR HANDLES THAT AUTOMATICALY)
    Returns:
        fetched data in list if successd else an error message
    """
    
    try:
        connection = mysql.connector.connect(
            host=os.getenv("server_host"),
            port=3306,
            database=os.getenv("db_name"),
            user=os.getenv("db_user"),
            password=os.getenv("db_password"),
        )

        if connection.is_connected():
            cursor = connection.cursor()
            
            cursor.execute(command)
            
            fetched_data = [ data for data in cursor.fetchall()]
                
            connection.close()
            
            return fetched_data

        
    except Error as e:
        return f"❌ Error while connecting to MySQL: {e}"


mcp.tool()
def saveOrdersData() -> None:
    """
    Get orders details from store via API then take products ids and names, quantities, and prices
    then fetch products from database by id_product and take id_supplier from each product
    then fetch it from pp_suppliers table and get the supplier name
    then create csv file for each supplier, name it supplierName_todayDate.csv and put their products, quantities and pricesb\n
    NOTE: do not double the product name in the file , instead , add its quantity to previous one

    """ 
        

# resource

# prompt


if __name__ == "__main__":
    mcp.run()