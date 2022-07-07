import globus_sdk
import pickle
import numpy as np
from astropy.io import fits
from astroquery.sdss import SDSS
from astropy import wcs
from astropy import coordinates as coords
import time
import sys
import glob
import os
import tarfile
import os.path
from pathlib import Path
import json

#region functions
def getProperties():
    # Properties are retrieved from the properties.json file and are assigned to the corresponding variables
    with open(os.path.join(sys.path[0], "properties.json"), 'r') as f:
        data = json.load(f)

    return (data['directories-and-filepaths']['download-directory'],
    data['globus-credentials']['client-id'],
    data['globus-credentials']['transfer-rt'],
    data['globus-credentials']['source-end-point'],
    data['globus-credentials']['destination-end-point'],
    data['general-properties']['images-per-tar'])

def createDirectoriesandFiles():
    # Creates the directories that will be used to store the data
    # Also creates the export log text file
    #
    # Create current data directory for each filter
    path = '{}downloadedData/currentData/'.format(downloadLocation)
    for fil in filters:
        os.makedirs('{}{}'.format(path, fil), exist_ok = True)
    # Create tarfiles directory
    path = '{}downloadedData/tarFiles'.format(downloadLocation)
    os.makedirs('{}'.format(path), exist_ok = True)

def deleteDownloadedData():
    for filter in filters:
        files = glob.glob('{}downloadedData/currentData/{}/*'.format(downloadLocation, filter))
        for f in files:
            os.remove(f)

def make_tarfile(run_no):
    source_dir = '{}downloadedData/currentData'.format(downloadLocation)
    output_filename = '{}downloadedData/tarFiles/{}.tar'.format(downloadLocation, run_no)

    with tarfile.open(output_filename, "w") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

#endregion

#region constants
filters = ['u', 'g', 'r', 'i', 'z']
downloadLocation, CLIENT_ID, transfer_rt, source_endpoint_id, destination_endpoint_id, filesPerTar = getProperties()

#endregion

createDirectoriesandFiles()

# Initialise client connection and authorizer using the refresh token

client = globus_sdk.NativeAppAuthClient(CLIENT_ID)

authorizer = globus_sdk.RefreshTokenAuthorizer(
    transfer_rt, client
)

tc = globus_sdk.TransferClient(authorizer=authorizer)

# Loads the dictionary that contains the names of the survey images to be downloaded and puts the keys into a list

with open("{}SDSSDictionary.pickle".format(downloadLocation), 'rb') as handle:
	SDSS_dictionary = pickle.load(handle)

# Convert dictionary to list and split up into sublists of equal size
key_list = list(SDSS_dictionary)
chunks = [key_list[x:x+filesPerTar] for x in range(0, len(key_list), filesPerTar)]

# Define filter names and start time for the execution
start_time = time.time()

for index, chunk in enumerate(chunks):
    print("Downloading job: " + str(index + 1) + " / " + str(len(chunks)))
    tdata = globus_sdk.TransferData(tc, source_endpoint_id,
                                        destination_endpoint_id,
                                        label="Download Job {}".format(index),
                                        sync_level="checksum")

    for surveyImage in chunk:
        filename_params = np.array(surveyImage.split(" "))
        for fil in filters:
            tdata.add_item("/dr17/eboss/photoObj/frames/{}/{}/{}/frame-{}-{}-{}-{}.fits.bz2".format(filename_params[1], 
                                                                                                    filename_params[0], 
                                                                                                    filename_params[2], 
                                                                                                    fil, 
                                                                                                    filename_params[0].zfill(6), 
                                                                                                    filename_params[2], 
                                                                                                    filename_params[3].zfill(4)),
            "{}downloadedData/currentData/{}/{}.fits.bz2".format(downloadLocation, fil, surveyImage))
    
    # Trigger the download

    transfer_result = tc.submit_transfer(tdata)
    task_id = transfer_result["task_id"]
    while not tc.task_wait(task_id, timeout=60):
        print("Another minute went by without {0} terminating".format(task_id))

    # Once downloaded tar the files and then delete the original files

    print('Tarring File')

    make_tarfile(str(index))
    deleteDownloadedData()

    print('Done!')

    # Write to the text file to update how the download is progressing

    with open('{}exportLog.txt'.format(downloadLocation), 'a') as f:
        f.write('Loop Number {} Saved'.format(str(index)))
        f.write('\n')
    
print('Program finished!')