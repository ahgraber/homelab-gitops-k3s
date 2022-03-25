#%%
import os
import numpy as np
import pandas as pd

#%%
columns=[
    'Type',
    'MPG',
    'Date',
    'Time',
    'Vehicle',
    'Odometer',
    'Filled Up',
    'Cost/Gallon',
    'Gallons',
    'Total Cost',
    'Octane',
    'Gas Brand',
    'Location',
    'Tags',
    'Payment Type',
    'Tire Pressure',
    'Notes',
    'Services',
    ]
# %%
df = pd.read_csv(os.path.join("~/Desktop", "fuelly", "fuelups.csv"))
df.columns = [col.strip() for col in df.columns]
df.columns

# %%
new = pd.DataFrame(columns=columns)

# %%
new['Type'] = 'Gas'
new['MPG'] = df['mpg']
new['Date'] = df['fuelup_date']
new['Time'] = '8:49 AM' # '08:18:00'
new['Vehicle'] = 'Golf R'
new['Odometer'] = df['odometer'].astype(int)
new['Filled Up'] = df['partial_fuelup']
new['Cost/Gallon'] = df['price']
new['Gallons'] = df['gallons']
new['Total Cost'] = (new['Cost/Gallon'] * new['Gallons']).round(2)
new['Octane'] = 'Premium [Octane: 91]'
new['Gas Brand'] = 'Citgo'
new['Location'] = np.NaN
new['Tags'] = np.NaN
new['Payment Type'] = 'American Express'
new['Tire Pressure'] = 0
new['Notes'] = np.NaN
new['Services'] = np.NaN


new.head()

# %%
new['Type'] = 'Gas'
new.loc[new['Filled Up']==0, ['Filled Up']] = 'Full'
new.loc[new['Filled Up']==1, ['Filled Up']] = 'Partial'
new.loc[new['MPG']==0, ['Filled Up']] = 'Partial'
new['Cost/Gallon'] = "$" + new['Cost/Gallon'].astype(str)
new['Total Cost'] = "$" + new['Total Cost'].astype(str)

new.head()

#%%
new = new.sort_values(by=["Date","Odometer"], ascending=True)
new.head()

#%%
# TODO: some intelligent checking to ensure date + odometer only increase

#%%
new.to_csv(
    os.path.join("~/Desktop", "fuelly_cleaned.csv"),
    index=False
)

# %%
# Note:  Hammond expects at least one "services" record
