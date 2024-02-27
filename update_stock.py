from shopify_api import get_all_product_handles
from utils import update_inventory_for_all_products
from logger import logger, settings

def update_stock():

    # Get all product handles on Shopify
    all_shopify_handles = get_all_product_handles()

    # Update inventory for all products
    update_inventory_for_all_products(all_shopify_handles)

    logger.info("#### FINISH ####", extra={'to_console': settings["CONSOLE"]})

if __name__ == '__main__':
    update_stock()