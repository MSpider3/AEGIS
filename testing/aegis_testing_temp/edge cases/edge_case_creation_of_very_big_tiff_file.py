# you this file to craeet the dge case tiff file, the file size will be around 4 to 5 GB
import numpy as np
import tifffile

# Set your dimensions (e.g., 40,000 x 30,000 pixels, 3 channels = ~3.6 GB)
# Increase width/height to easily cross the 4GB threshold
width = 50000
height = 30000
channels = 3  # RGB

print("Generating dummy image arrays in memory...")
# Create dummy data (zeros use less memory during allocation)
# uint8 = 1 byte per pixel per channel
data = np.zeros((height, width, channels), dtype=np.uint8)

print("Writing BigTIFF file to disk...")
# bigtiff=True forces the 64-bit offset required for files > 4GB
tifffile.imwrite(
    'edge_case_test.tif', 
    data, 
    bigtiff=True, 
    compression=None
)

print("Large TIFF file created successfully!")
