import csv
import progressbar
import pickle
import pandas as pd
import sys
from pathlib import Path
import json
import os

#region functions
def getProperties():
    # Properties are retrieved from the properties.json file and are assigned to the corresponding variables
    with open(os.path.join(sys.path[0], "properties.json"), 'r') as f:
        data = json.load(f)

    return (data['directories-and-filepaths']['csv-filepath'], data['directories-and-filepaths']['download-directory'])
#endregion

#region constants
dataCSVLocation, pickleLocation = getProperties()
#endregion

# Main data csv is loaded

print('Loading csv file...')

main_data = pd.read_csv(dataCSVLocation)

# Converts the objId column to string so that precision is not lost

main_data['objId'] = main_data['objId'].astype('object')

print('Done!')
print('Starting dictionary conversion...')

SDSS_dictionary = {}
radec_dictionary = {}

bar = progressbar.ProgressBar(max_value = len(main_data))

# Loops through each of the galaxies in the df
# If the galaxy has a run-rerun-camcol-field combination that has already been seen then this object will be added to the value for the specific key
# If not then a new key will be created in the dictionary

for index, row in main_data.iterrows():
    # Adds the ra and dec to a dictionary with keys of the object id so that later on quick reference can be achieved
    radec_dictionary[row['objId']] = '{} {}'.format(row['ra'], row['dec'])
    # Adds the objId to the dictionary entry for each survey image.
    if "{} {} {} {}".format(row['run'], row['rerun'], row['camcol'], row['field']) in SDSS_dictionary:
        # If the plate has already been added to the dictionary
        # Add the ra and dec to the dictionary
        SDSS_dictionary["{} {} {} {}".format(row['run'], row['rerun'], row['camcol'], row['field']) ].append(row['objId'])
    else:
        # If the plate has not yet been added to the dictionary
        SDSS_dictionary["{} {} {} {}".format(row['run'], row['rerun'], row['camcol'], row['field']) ] = [row['objId']]

    bar.update(index)

# Save dictionary to a pickle file

print('Done!')
print('Saving pickle file...')

with open('{}radecDictionary.pickle'.format(pickleLocation), 'wb') as handle:
    pickle.dump(radec_dictionary, handle, protocol=pickle.HIGHEST_PROTOCOL)


with open('{}SDSSDictionary.pickle'.format(pickleLocation), 'wb') as handle:
    pickle.dump(SDSS_dictionary, handle, protocol=pickle.HIGHEST_PROTOCOL)

print('Done!')