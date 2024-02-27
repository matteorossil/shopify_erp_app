from shopify_api import *
from sinesy_api import *
from logger import logger, settings

TOT_PROC = 0

def update_inventory_for_all_products(all_shopify_handles):
    global TOT_PROC
    TOT_PROC = 0
    logger.info("Updating inventory for all products on Shopify", extra={'to_console': settings["CONSOLE"]})
    for handle in sorted(all_shopify_handles):
        TOT_PROC += 1
        update_inventory_for_product(handle)
    
    time.sleep(PAUSE)
    logger.info("Completed\n" + "-"*50, extra={'to_console': settings["CONSOLE"]})

    return None

def update_inventory_for_product(handle):
    # Fetch stock data from Sinesy
    stock_data = fetch_stock_from_sinesy(handle)

    # Fetch product variants from Shopify
    product_data = get_product_by_handle(handle)
    
    logger.info(f"\n    {TOT_PROC:<4}{handle:5}", extra={'to_console': settings["CONSOLE"]})

    # Update inventory for each variant
    for variant in product_data['variants']:
        size = variant['option1']
        if size in stock_data:
            new_quantity = stock_data[size]
            old_quantity = variant['inventory_quantity']
            if new_quantity != old_quantity:
                response = update_shopify_stock(LOCATION_ID, variant['inventory_item_id'], new_quantity)
                logger.info(f"        {size:4}  |  updated  |  new:old  {new_quantity:2}:{old_quantity:<2}  |  Status Code: {response.status_code}", extra={'to_console': settings["CONSOLE"]})
            else:
                logger.info(f"        {size:4}  |  -------  |  new:old  {new_quantity:2}:{old_quantity:<2}  |", extra={'to_console': settings["CONSOLE"]})
    
    if not stock_data: logger.info(f"        Not in Sinesy", extra={'to_console': settings["CONSOLE"]})

    return None

def get_sinesy_prices(catalog, itemcodes):
    
    # Initialize a new dictionary to store the filtered information
    prices_dict = {}
    
    # Iterate over the list of item codes
    for code in itemcodes:
        # Check if the item code exists in the original dictionary
        if code in catalog:
            # Extract 'Prezzo' and 'Prezzo Retail' and add them to the new dictionary
            prices_dict[code] = {
                'Prezzo': catalog[code].get('Prezzo'),
                'Prezzo Retail': catalog[code].get('Prezzo Retail')
            }
    
    return prices_dict
