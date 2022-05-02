import os
import pandas as pd


class Olist:
    def get_data(self):
        """
        This function returns a Python dict.
        Its keys should be 'sellers', 'orders', 'order_items' etc...
        Its values should be pandas.DataFrames loaded from csv files
        """
        abs_dirname = os.path.dirname(os.path.dirname(__file__))
        csv_path = os.path.join(abs_dirname,"data","csv")
        file_names = [os.listdir(csv_path)[x] for x in range(len(os.listdir(csv_path))) if '.csv' in os.listdir(csv_path)[x]]
        key_names = [x.replace('olist_','').replace('_dataset','').replace('.csv', '') for x in file_names]
        data = {}
        for (key,file) in zip(key_names,file_names):
            data[key] = pd.read_csv(os.path.join(csv_path, file))

        return data

    def ping(self):
        """
        You call ping I print pong.
        """
        print("pong")

