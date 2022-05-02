import pandas as pd
import numpy as np
from olist.utils import haversine_distance
from olist.data import Olist


class Order:
    '''
    DataFrames containing all orders as index,
    and various properties of these orders as columns
    '''
    def __init__(self):
        # Assign an attribute ".data" to all new instances of Order
        self.data = Olist().get_data()

    def get_wait_time(self, is_delivered=True):
        """
        Returns a DataFrame with:
        [order_id, wait_time, expected_wait_time, delay_vs_expected, order_status]
        and filters out non-delivered orders unless specified
        """
        orders = self.data['orders'].copy()
        orders = orders.query('order_status == "delivered"')
        for x in ['order_purchase_timestamp','order_approved_at','order_delivered_customer_date','order_estimated_delivery_date']:
            orders[x] = pd.to_datetime(orders[x])
        orders['wait_time'] = ((orders['order_delivered_customer_date']-orders['order_purchase_timestamp'])/np.timedelta64(1,'D'))
        orders['expected_wait_time'] = ((orders['order_estimated_delivery_date']-orders['order_purchase_timestamp'])/np.timedelta64(1,'D'))
        orders['delay_vs_expected'] = ((orders['order_delivered_customer_date']-orders['order_estimated_delivery_date'])/np.timedelta64(1,'D'))
        orders = orders[['order_id','wait_time','expected_wait_time','delay_vs_expected','order_status']]
        return orders

    def get_review_score(self):
        """
        Returns a DataFrame with:
        order_id, dim_is_five_star, dim_is_one_star, review_score
        """
        reviews = self.data['order_reviews'].copy()
        for index,row in reviews.iterrows():
            if row['review_score'] == 5:
                reviews.loc[index,'dim_is_five_star'] = 1
            else:
                reviews.loc[index,'dim_is_five_star'] = 0
        for index,row in reviews.iterrows():
            if row['review_score'] == 1:
                reviews.loc[index,'dim_is_one_star'] = 1
            else:
                reviews.loc[index,'dim_is_one_star'] = 0
        reviews = reviews[['order_id', 'dim_is_five_star', 'dim_is_one_star', 'review_score']]
        return reviews

    def get_number_products(self):
        """
        Returns a DataFrame with:
        order_id, number_of_products
        """
        items = self.data['order_items'].copy()
        items = items.groupby('order_id').count()
        items['order_id'] = items.index
        items = items.set_index(np.arange(0,len(items['order_id'])))
        items = items.rename(columns={'product_id': 'number_of_products'})
        return items[['order_id','number_of_products']]

    def get_number_sellers(self):
        """
        Returns a DataFrame with:
        order_id, number_of_sellers
        """
        numseller = self.data['order_items'].copy()
        numseller = numseller.groupby('order_id').nunique()
        numseller['order_id'] = numseller.index
        numseller = numseller.set_index(np.arange(0,len(numseller['order_id'])))
        numseller = numseller.rename(columns={'seller_id': 'number_of_sellers'})
        return numseller[['order_id','number_of_sellers']]


    def get_price_and_freight(self):
        """
        Returns a DataFrame with:
        order_id, price, freight_value
        """
        price = self.data['order_items'].copy()
        price = price.groupby('order_id').agg('sum')
        price['order_id'] = price.index
        price = price.set_index(np.arange(0,len(price['order_id'])))
        return price[['order_id','price','freight_value']]


    # Optional
    def get_distance_seller_customer(self):
        """
        Returns a DataFrame with:
        order_id, distance_seller_customer
        """
        # import data
        data = self.data
        orders = data['orders']
        order_items = data['order_items']
        sellers = data['sellers']
        customers = data['customers']

        # Since one zip code can map to multiple (lat, lng), take the first one
        geo = data['geolocation']
        geo = geo.groupby('geolocation_zip_code_prefix',
                          as_index=False).first()

        # Merge geo_location for sellers
        sellers_mask_columns = [
            'seller_id', 'seller_zip_code_prefix', 'geolocation_lat', 'geolocation_lng'
        ]

        sellers_geo = sellers.merge(
            geo,
            how='left',
            left_on='seller_zip_code_prefix',
            right_on='geolocation_zip_code_prefix')[sellers_mask_columns]

        # Merge geo_location for customers
        customers_mask_columns = ['customer_id', 'customer_zip_code_prefix', 'geolocation_lat', 'geolocation_lng']

        customers_geo = customers.merge(
            geo,
            how='left',
            left_on='customer_zip_code_prefix',
            right_on='geolocation_zip_code_prefix')[customers_mask_columns]

        # Match customers with sellers in one table
        customers_sellers = customers.merge(orders, on='customer_id')\
            .merge(order_items, on='order_id')\
            .merge(sellers, on='seller_id')\
            [['order_id', 'customer_id','customer_zip_code_prefix', 'seller_id', 'seller_zip_code_prefix']]

        # Add the geoloc
        matching_geo = customers_sellers.merge(sellers_geo,
                                            on='seller_id')\
            .merge(customers_geo,
                   on='customer_id',
                   suffixes=('_seller',
                             '_customer'))
        # Remove na()
        matching_geo = matching_geo.dropna()

        matching_geo.loc[:, 'distance_seller_customer'] =\
            matching_geo.apply(lambda row:
                               haversine_distance(row['geolocation_lng_seller'],
                                                  row['geolocation_lat_seller'],
                                                  row['geolocation_lng_customer'],
                                                  row['geolocation_lat_customer']),
                               axis=1)
        # Since an order can have multiple sellers,
        # return the average of the distance per order
        order_distance =\
            matching_geo.groupby('order_id',
                                 as_index=False).agg({'distance_seller_customer':
                                                      'mean'})

        return order_distance


    def get_training_data(self,
                          is_delivered=True,
                          with_distance_seller_customer=False):
        """
        Returns a clean DataFrame (without NaN), with the all following columns:
        ['order_id', 'wait_time', 'expected_wait_time', 'delay_vs_expected',
        'order_status', 'dim_is_five_star', 'dim_is_one_star', 'review_score',
        'number_of_products', 'number_of_sellers', 'price', 'freight_value',
        'distance_seller_customer']
        """

        result = self.get_wait_time().merge(self.get_review_score(),on = 'order_id', how = 'inner')
        result = result.merge(self.get_number_products(), on = 'order_id', how = 'inner')
        result = result.merge(self.get_number_sellers(),on = 'order_id', how = 'inner')
        result = result.merge(self.get_price_and_freight(), on = 'order_id', how = 'inner')
        if with_distance_seller_customer:
            result = result.merge(
                self.get_distance_seller_customer(), on='order_id')

        return result.dropna()
