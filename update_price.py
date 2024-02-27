from sinesy_api import get_full_catalog, organize_catalog_by_item_code
from shopify_api import get_all_product_handles, categorize_itemcodes_in_shopify, update_shopify_prices
from utils import get_sinesy_prices
from logger import logger, settings

def update_price():

    try:
        # Get catalog from Sinesy
        catalog_sinesy = get_full_catalog(start=0)

        # Organize the catalog by itemCode
        organized_catalog = organize_catalog_by_item_code(catalog_sinesy)

        # Returns all the product handles in Shopify
        shopify_handles = get_all_product_handles()

        # Returns products in catalog that are present in Shopify
        present_itemcodes, _ = categorize_itemcodes_in_shopify(shopify_handles, organized_catalog)

        if len(present_itemcodes) > 0: # if there are more than 0 product in shopify
            
            # organize shopify catalog by price (Vendita and Retail)
            catalog_prices = get_sinesy_prices(organized_catalog, present_itemcodes)

            update_shopify_prices(catalog_prices)

    except Exception as e:
        logger.info(f"An error occurred: {e}", extra={'to_console': True})

    logger.info("#### FINISH ####", extra={'to_console': settings["CONSOLE"]})

if __name__ == '__main__':
    update_price()