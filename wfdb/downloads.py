import numpy as np
import re
import os
import sys
import requests
import multiprocessing
from .records import Record, BaseRecord, rdheader
        
# Read a header file from physiobank
def streamheader(recordname, pbdir):

    # Full url of header location
    url = 'http://physionet.org/physiobank/database/'+os.path.join(pbdir, recordname+'.hea')
    r = requests.get(url)
    
    # Raise HTTPError if invalid url
    r.raise_for_status()
    
    # Get each line as a string
    filelines = r.content.decode('ascii').splitlines()
    
    # Separate content into header and comment lines
    headerlines = []
    commentlines = []
    
    for line in filelines:
        line = line.strip()
        # Comment line
        if line.startswith('#'):
            commentlines.append(line)
        # Non-empty non-comment line = header line.
        elif line:  
            # Look for a comment in the line
            ci = line.find('#')
            if ci > 0:
                headerlines.append(line[:ci])
                # comment on same line as header line
                commentlines.append(line[ci:])
            else:
                headerlines.append(line)
    
    return (headerlines, commentlines) 

# Read certain bytes from a dat file from physiobank
def streamdat(filename, pbdir, fmt, bytecount, startbyte, datatypes):
    
    # Full url of dat file
    url = 'http://physionet.org/physiobank/database/'+os.path.join(pbdir, filename)

    # Specify the byte range
    endbyte = startbyte + bytecount-1 
    headers = {"Range": "bytes="+str(startbyte)+"-"+str(endbyte), 'Accept-Encoding': '*/*'} 
    
    # Get the content
    r = requests.get(url, headers=headers, stream=True)
    
    # Raise HTTPError if invalid url
    r.raise_for_status()
    
    sigbytes = r.content

    # Convert to numpy array
    sigbytes = np.fromstring(sigbytes, dtype = np.dtype(datatypes[fmt]))

    # For special formats that were read as unsigned 1 byte blocks to be further processed,
    # convert dtype from uint8 to uint64
    if fmt == ['212', '310', '311']:
        sigbytes = sigbytes.astype('uint')

    return sigbytes

# Read an entire annotation file from physiobank
def streamannotation(filename, pbdir):

    # Full url of annotation file
    url = 'http://physionet.org/physiobank/database/'+os.path.join(pbdir, filename)

    # Get the content
    r = requests.get(url)
    # Raise HTTPError if invalid url
    r.raise_for_status()
    
    annbytes = r.content

    # Convert to numpy array
    annbytes = np.fromstring(annbytes, dtype = np.dtype('<u1'))

    return annbytes


# Download all the WFDB files from a physiobank database
# http://freecode.com/projects/pysync/
# http://stackoverflow.com/questions/20441270/fastest-way-to-download-thousand-files-using-python
def dldatabase(pbdb, dldir): 

    # Full url physiobank database
    dburl = 'http://physionet.org/physiobank/database/'+pbdb

    # Check if the database is valid
    r = requests.get(dburl)
    r.raise_for_status()

    # Check for a RECORDS file
    recordsurl = 'http://physionet.org/physiobank/database/'+os.path.join(pbdb, 'RECORDS')

    # Check if the file is present
    r = requests.get(dburl)
    if r.status_code == 404:
        sys.exit('This database has no WFDB files to download')

    # Get each line as a string
    records = r.content.decode('ascii').splitlines()

    # Make the local download dir if it doesn't exist
    if not os.path.isdir(dldir):  
        os.makedirs(dldir)
        print("Created local directory: ", dldir)

    # All files to download (relative to the database's home directory)
    allfiles = []
    
    for rec in records:
        # Check out whether each record is in MIT or EDF format
        if rec.endswith('.edf'):
            allfiles.append(rec)
        else:
            # If MIT format, have to figure out all associated files
            mitrecords.append(rec+'.hea')
            
            dirname, baserecname = os.path.split(rec)

            record = records.rdheader(baserecname, pbdir = 'dirname')




    allfiles = [os.path.join('http://physionet.org/physiobank/database/', pbdb, file) for file in allfiles]




    return









def downloadsamp(pbrecname, targetdir):
    """Check a specified local directory for all necessary files required to read a Physiobank
       record, and download any missing files into the same directory. Returns a list of files
       downloaded, or exits with error if an invalid Physiobank record is specified.

    Usage: dledfiles = dlrecordfiles(pbrecname, targetdir)

    Input arguments:
    - pbrecname (required): The name of the MIT format Physiobank record to be read, prepended
      with the Physiobank subdirectory the file is contained in (without any file extensions).
      eg. pbrecname=prcp/12726 to download files http://physionet.org/physiobank/database/prcp/12726.hea
      and 12727.dat
    - targetdir (required): The local directory to check for files required to read the record,
      in which missing files are also downloaded.

    Output arguments:
    - dledfiles:  The list of files downloaded from PhysioBank.

    """

    physioneturl = "http://physionet.org/physiobank/database/"
    pbdir, baserecname = os.path.split(pbrecname)
    displaydlmsg=1
    dledfiles = [] 
    
    if not os.path.isdir(targetdir):  # Make the target dir if it doesn't exist
        os.makedirs(targetdir)
        print("Created local directory: ", targetdir)
    
    # For any missing file, check if the input physiobank record name is
    # valid, ie whether the file exists on physionet. Download if valid, exit
    # if invalid.
    dledfiles, displaydlmsg = dlifmissing(physioneturl+pbdir+"/"+baserecname+".hea", os.path.join(targetdir, 
        baserecname+".hea"), dledfiles, displaydlmsg, targetdir)
        
    fields = rdheader(os.path.join(targetdir, baserecname))

    # Need to check validity of link if ANY file is missing.
    if fields["nseg"] == 1:  # Single segment. Check for all the required dat files
        for f in set(fields["filename"]):
            # Missing dat file
            dledfiles, displaydlmsg = dlifmissing(physioneturl+pbdir+"/"+f, os.path.join(targetdir, f), 
                dledfiles, displaydlmsg, targetdir)
    else:  # Multi segment. Check for all segment headers and their dat files
        for segment in fields["filename"]:
            if segment != '~':
                # Check the segment header
                dledfiles, displaydlmsg = dlifmissing(physioneturl+pbdir+"/"+segment+".hea", 
                    os.path.join(targetdir, segment+".hea"), dledfiles, displaydlmsg, targetdir)    
                segfields = rdheader(os.path.join(targetdir, segment))
                for f in set(segfields["filename"]):
                    if f != '~':
                        # Check the segment's dat file
                        dledfiles, displaydlmsg = dlifmissing(physioneturl+pbdir+"/"+f, 
                            os.path.join(targetdir, f), dledfiles, displaydlmsg, targetdir)
                            
    if dledfiles:
        print('Downloaded all missing files for record.')
    return dledfiles  # downloaded files


# Download a file if it is missing. Also error check 0 byte files.  
def dlifmissing(url, filename, dledfiles, displaydlmsg, targetdir):
    fileexists = os.path.isfile(filename)  
    if fileexists:
        # Likely interrupted download
        if os.path.getsize(filename)==0:
            try:
                input = raw_input
            except NameError:
                pass
            userresponse=input("Warning: File "+filename+" is 0 bytes.\n"
                "Likely interrupted download. Remove file and redownload? [y/n]: ")
            # override input for python 2 compatibility
            while userresponse not in ['y','n']:
                userresponse=input("Remove file and redownload? [y/n]: ")
            if userresponse=='y':
                os.remove(filename)
                dledfiles.append(dlorexit(url, filename, displaydlmsg, targetdir))
                displaydlmsg=0
            else:
                print("Skipping download.")
        # File is already present.
        else:
            print("File "+filename+" is already present.")
    else:
        dledfiles.append(dlorexit(url, filename, displaydlmsg, targetdir))
        displaydlmsg=0
    
    # If a file gets downloaded, displaydlmsg is set to 0. No need to print the message more than once. 
    return dledfiles, displaydlmsg
                 
    
# Download the file from the specified 'url' as the 'filename', or exit with warning.
def dlorexit(url, filename, displaydlmsg=0, targetdir=[]):
    if displaydlmsg: # We want this message to be called once for all files downloaded.
        print('Downloading missing file(s) into directory: {}'.format(targetdir))
    try:
        r = requests.get(url)
        with open(filename, "wb") as writefile:
            writefile.write(r.content)
        return filename
    except requests.HTTPError:
        sys.exit("Attempted to download invalid target file: " + url)


# Download files required to read a wfdb annotation.
def dlannfiles():
    return dledfiles


# Download all the records in a physiobank database.
def dlPBdatabase(database, targetdir):
    return dledfiles



