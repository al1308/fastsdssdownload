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
from pathlib import Path
import shutil
import json

#region functions

def getCroppedImage(Originalimage, radec):
    cropped_image = np.zeros((32,32))
    x_count = -1
    y_count = -1

    try:
        for i in range(int(radec[1] - cropped_image.shape[0] / 2), int(radec[1] + cropped_image.shape[0] / 2)):
            x_count += 1
            y_count = -1
            for j in range(int(radec[0] - cropped_image.shape[1] / 2), int(radec[0] + cropped_image.shape[1] / 2)):
                y_count += 1
                cropped_image[x_count, y_count] = Originalimage[i][j]
        return cropped_image
    except IndexError as error:
        return None
    
def processImages(filename):
    # Open the files first and store in array
    # Also store the wcs_converts and plate images
    hduls = []
    wcs_converts = []
    survey_images = []

    skipped_images = []

    for fil_index, band in enumerate(filters):
        hduls.append(fits.open('{}downloadedData/untarredFiles/Job{}/currentData/{}/{}.fits.bz2'.format(downloadLocation, str(job_number), band, filename)))
        wcs_converts.append(wcs.WCS(hduls[fil_index][0].header))
        survey_images.append(hduls[fil_index][0].data)

    # Loop though the different ra and dec pairs and if one of the filters doesn't work then don't add it to the array

    cropped_images = []

    for objId in SDSS_dictionary[filename]:
        # Creates an array for the file to be stored
        image = []
        # Converts the ra dec to sky coord
        pos = coords.SkyCoord(str(radecDictionary[objId]), unit='deg', frame='icrs')
        for band in filters:
            # Gets where the object is within the frame for the specified filter
            ux, uy = wcs.utils.skycoord_to_pixel(pos, wcs_converts[fil_index])
            # Get the cropped image (will return None if failed)  
            cropped = getCroppedImage(survey_images[fil_index], [ux, uy])
            if cropped is not None:
                image.append(cropped)
              
        # Check if the image is in the correct shape
        if np.array(image).shape == (5, 32, 32):
            cropped_images.append(image)
        else:
            # If the image does not have the correct size then the image will not be added to the array
            print('Added to skipped array')
            skipped_images.append(str(ra_dec_pair))

    cropped_images = np.array(cropped_images)

    # Add the skipped images to the text file 

    if len(skipped_images) > 0:
        f = open("{}downloadedData/imageLists/{}list.txt".format(downloadLocation, str(i)), "a")

        for skipped_image in skipped_images:
            f.write(skipped_image)
            f.write("\n")

        f.close()

    # If the shape of the resulting array is correct then it can be returned
    
    if len(cropped_images.shape) == 4:
        return np.transpose(cropped_images, (0,2,3,1))
    else:
        return None

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def getProperties():
    # Properties are retrieved from the properties.json file and are assigned to the corresponding variables
    with open(os.path.join(sys.path[0], "properties.json"), 'r') as f:
        data = json.load(f)

    return (data['directories-and-filepaths']['download-directory'])

def createDirectoriesandFiles():
    # Create a folder relating to the job so that the temp untarred files can be stored there
    os.makedirs('{}downloadedData/untarredFiles/Job{}'.format(downloadLocation, str(job_number)), exist_ok = True)
    os.makedirs('{}downloadedData/numpyFiles'.format(downloadLocation), exist_ok = True)
    os.makedirs('{}downloadedData/exportLogs'.format(downloadLocation), exist_ok = True)

#endregion

#region constants
downloadLocation = getProperties()
numberOfJobs = sys.argv[1]
job_number = sys.argv[2]
#endregion

# Gets the list of the files stored in the tarFiles directory
# This can be looped through and the files can be referenced from within the SDSS Dictionary

files = []

for f in os.listdir('{}downloadedData/tarFiles/'.format(downloadLocation)):
    if f.endswith(".tar"):
        files.append(f)

files = [x.split('.')[0] for x in files]

splitFiles = list(split(files, int(numberOfJobs)))

# Import the main dictionary and the radec dictionary for the objects

with open("{}SDSSDictionary.pickle".format(downloadLocation), 'rb') as handle:
	SDSS_dictionary = pickle.load(handle)

with open("{}radecDictionary.pickle".format(downloadLocation), 'rb') as handle:
	radecDictionary = pickle.load(handle)

# Create the required directories and files 

createDirectoriesandFiles()

# Creates the new list of the tar files to be processed in this script

filters = ['u', 'g', 'r', 'i', 'z']

start_time = time.time()

for fileName in splitFiles[int(job_number) - 1]:
    processed_images = []
    # untar the file in the specified directory for the job
    my_tar = tarfile.open('{}downloadedData/tarFiles/{}.tar'.format(downloadLocation, str(fileName)))
    my_tar.extractall('{}downloadedData/untarredFiles/Job{}'.format(downloadLocation, str(job_number)))
    my_tar.close()

    fitsFiles = list(map(lambda a : Path(Path(a).stem).stem, glob.glob('{}downloadedData/untarredFiles/Job{}/currentData/r/*'.format(downloadLocation, str(job_number)))))

    for index, fitsFile in enumerate(fitsFiles):    
        print('Analysing File {}'.format(str(index)))
        # Gets a list of the processed images from the file
        returned_images = processImages(fitsFile)
        # Loops through each returned image and adds it to the returned images
        if returned_images is not None:
            for retImage in returned_images:
                processed_images.append(retImage)
        
        print(np.array(processed_images).shape)

    # Save numpy file
    try:
        np.save('{}downloadedData/numpyFiles/{}.npy'.format(downloadLocation, fileName), np.array(processed_images), allow_pickle = False)
    except ValueError as error:
        print('Error occured when saving numpy file {}'.format(str(i)))

    # Remove the extracted data
    shutil.rmtree('{}downloadedData/untarredFiles/Job{}/currentData'.format(downloadLocation, job_number))

    # Update the status in the text file
    f = open("{}downloadedData/exportLogs/Job{}Log.txt".format(downloadLocation, job_number), "a")
    f.write("Status: {} / {}".format(str((index - ((job_number - 1) * default_tar_per_job))), str(tar_per_job)))
    f.write("\n")
    f.close()

    print('Analysing {} finished'.format(str(index)))