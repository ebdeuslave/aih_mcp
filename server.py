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

available_stores = os.getenv("stores")

mcp = FastMCP("mcp_demo")

@mcp.tool()
def getOrders(store: str,from_date: str, to_date: str, from_time="00:00:00", payment:str="all", current_states:list=[2,3]) -> list|int|str:
    """
    Get the orders ids for a giving date
    Args:
        store: the given store name
        from_date: The starting date (format: YYYY-MM-DD)
        to_date: The ending date (format: YYYY-MM-DD) NOTE that the to_date is excluded
        from_time: The starting time (format: "HH:MM:SS")
        payment: payment mode (only cod and cmi, cod means cash on delivery, cmi means prepaid, all is the default means both)
        current_states: list contains ids of orders status
            list of status {ID:NAME} : { 2:"paiement accepte or received payment", 3: "preparation encours or not yet shipped"}
    Returns:
        The list of orders ids if successed else a status code number or message
    """
    
    available_payment = {
        "cod": "Paiement comptant à la livraison (Cash on delivery)",
        "cmi": "cmi"
    }

    if store not in available_stores:
        return f"Store {store} is not available"


    url = f"https://{store}.ma/api/orders?output_format=JSON&filter[invoice_date]=[{from_date} {from_time},{to_date}]"

    if payment != "all" and payment in available_payment:
        url += "&filter[payment]=[{payment}]"

    if current_states:
        url += f"&filter[current_state]={current_states}"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code != 200:
            return response.status_code
            
        return response.json()["orders"]
        
    
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
def getProductSupplier(id_product:int) -> str:
    """
     Get the product supplier
    Args:
        id_product: product id
    Returns:
        The supplier name if 200 else response content
    """
    
    url = f"https://parapharma.ma/api/products/{id_product}?output_format=JSON"

    with httpx.Client(http2=True) as client:
        response = client.get(url, auth=(API_KEY, ""))
        
        if response.status_code != 200:
            return response.content   
        
        return getSupplierName(response.json()["product"]["id_supplier"]) 


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
        DO NOT TRY TO USE ANY COMMAND THAT UPDATE/DELETE RECORDS BECAUSE YOU CANNOT, YOU ARE ALLOWED TO ONLY FETCH DATA
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
def saveProducts(store: str,from_date: str, to_date: str, from_time="00:00:00", payment:str="all", current_states:list=[2,3]) -> None:
    """
    Get orders details from store via API, and take products ids, names, quantities, and prices
    then fetch products from database by id_product and take id_supplier from each product
    then fetch it from pp_suppliers table (pp could be ps or other) and get the supplier name
    then create a folder called "products" inside it create csv file for each supplier, name it supplierName_todayDate(YYYY-MM-DD).csv and put their products, quantities and pricesb\n
    NOTE: do not double the product name in the file , instead , add its quantity to the same previous one
        it is better to give a feedback about this point, Ex : "i found another PRODUCT_NAME i will add its quantity to the previous one"
        
    Args:
        store: the given store name
        from_date: The starting date (format: YYYY-MM-DD)
        to_date: The ending date (format: YYYY-MM-DD) NOTE that the to_date is excluded
        from_time: The starting time (format: "HH:MM:SS")
        payment: payment mode (only cod and cmi, cod means cash on delivery, cmi means prepaid, all is the default means both)
        current_states: list contains ids of orders status
            list of status {ID:NAME} : { 2:"paiement accepte or received payment", 3: "preparation encours or not yet shipped"}
            
    Returns:
        None
    """ 
    
    getOrders(store, from_date, to_date, from_time, payment,current_states)
        

# resource

# prompt


if __name__ == "__main__":
    mcp.run()