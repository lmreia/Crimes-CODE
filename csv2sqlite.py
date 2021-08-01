import pandas as pd
import glob
import os
import sqlite3
from datetime import datetime

# Create a SQL connection to our SQLite database
conn = sqlite3.connect("CODE_Data/code_data.sqlite")

# carregando todos os dados
path = 'CODE_Data/'  # use your path
all_files = glob.glob(os.path.join(path + "/*.csv.gz"))

dateparse = lambda x: datetime.strptime(x, '%Y-%m-%d %H:%M')
data = pd.concat((pd.read_csv(f,
                              compression='gzip',
                              on_bad_lines='warn',
                              usecols=["city_name", "offense_code", "offense_type", "offense_group", "offense_against",
                                       "date_single", "longitude", "latitude", "location_type", "location_category"],
                              parse_dates=["date_single"],
                              date_parser=dateparse)
                  for f in all_files))

data.to_sql("code_data", conn, if_exists='replace', index=False)

# Be sure to close the connection
conn.close()
