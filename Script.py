##################### PRELIMINARY STEPS ###################################

# Close all open images
from ij import WindowManager
for imp in WindowManager.getImageTitles():
    WindowManager.getImage(imp).close()

# Clear ROI if it was opened
from ij.plugin.frame import RoiManager
rm = RoiManager.getInstance()
if rm is not None:
    rm.reset()

from ij import IJ, ImagePlus
from ij.process import ImageProcessor
from ij.plugin.frame import RoiManager
from ij.io import OpenDialog
from ij.gui import Roi, ShapeRoi

RM = RoiManager()        # we create an instance of the RoiManager class
rm = RM.getRoiManager()  # "activate" the RoiManager otherwise it can behave strangely

##################### CREATING FUNCTIONS ###################################


# Creating the function that takes a binary mask and adds it to the ROI with custom name and colour
# If invertTrue is = 0 it selects the white part, if it is = 1 it selects the black part
# Optional fillHolesTrue = 1 adds the holes inside the selection
# Make sure the number variable is unique for each selection
def binaryToSelection(number, colour, name, image, fillHolesTrue, invertTrue):
    
    if invertTrue:
        IJ.run(image, "Invert LUT", "")
    if fillHolesTrue:
        IJ.run(image, "Fill Holes", "")
    IJ.run(image, "Create Selection", "")
    rm.addRoi(image.getRoi())
    rm.select(number)
    rm.runCommand("Set Fill Color", colour)
    rm.runCommand("Rename", name)
    rm.runCommand(image, "Deselect")



# Function to perform particle selection and add it to ROI Manager
def particleSelection(minSize, maxSize, image, name, fill, color, invertTrue):
    if invertTrue:
        IJ.run(image, "Invert LUT", "")
    
    # Store the current number of ROIs before running Analyze Particles
    initial_roi_count = rm.getCount()

    # Run Analyze Particles
    IJ.run(image, "Analyze Particles...", "size=" + str(minSize) + "-" + str(maxSize) + " pixel show=[Overlay] clear")

    overlay = image.getOverlay()

    if overlay is not None and overlay.size() > 0:
        combined_roi = ShapeRoi(overlay.get(0))
        for i in range(1, overlay.size()):
            roi = overlay.get(i)
            combined_roi.or(ShapeRoi(roi))
        
        # Remove ROIs added by Analyze Particles
        for i in range(rm.getCount() - 1, initial_roi_count - 1, -1):
            rm.select(i)
            rm.runCommand("Delete")
        
        # Add the combined ROI
        rm.addRoi(combined_roi)
        rm.select(rm.getCount() - 1)
        rm.runCommand("Rename", name)
        rm.runCommand("Set Fill Color", color)

        if fill.lower() == "true":
            rm.runCommand("Fill")

# New function to create a binary image from an ROI
def create_binary_image_from_roi(imp, roi, name):
    # Create a new blank image
    ip = imp.getProcessor().createProcessor(imp.getWidth(), imp.getHeight())
    ip.setColor(255)  # Set color to white
    ip.fill()  # Fill the image with white
    
    # Draw the ROI in black
    ip.setColor(0)
    ip.fill(roi)
    
    # Create a new ImagePlus with the binary image
    binary_imp = ImagePlus(name, ip)
    binary_imp.show()
    return binary_imp

# New function to perform binary operations
def perform_binary_operations(image):
    IJ.run(image, "Convert to Mask", "");
    IJ.run(image, "Invert LUT", "")
    IJ.run(image, "Dilate", "")
    IJ.run(image, "Fill Holes", "")
    IJ.run(image, "Erode", "")

################ START OF THE CODE ######################


# Open a dialog to select the image file
od = OpenDialog("Select the image file", None)
file_path = od.getPath()

if file_path is None:
    print("No file selected. Exiting script.")
    import sys
    sys.exit()

# Open the specified image
imp = IJ.openImage(file_path)

if imp is None:
    print("Failed to open image: {}".format(file_path))
    print("Please check if the file exists and is accessible.")
    import sys
    sys.exit()

imp.setTitle("Copy_1")
imp.show()

# Create a duplicate of the original image
duplicate = imp.duplicate()
duplicate.setTitle("Copy_2")
duplicate.show()

# Process the duplicate image
ImagePlus.setDefault16bitRange(16)
duplicate.setDisplayRange(60, 215)
duplicate.updateAndDraw()
IJ.run(duplicate, "Despeckle", "")
IJ.run(duplicate, "8-bit", "")
IJ.setAutoThreshold(duplicate, "Default no-reset")
IJ.setRawThreshold(duplicate, 220, 255, None)
IJ.run(duplicate, "Convert to Mask", "")

############## SEPARATING STRUCTURES #################


# Saving the part of the image without tissue as a blue backgroung (it contains the vessels as well)
binaryToSelection(
    0,                # number - ROI index (0 for the first ROI)
    "white",           # colour - Fill color for the ROI
    "All background", # name - Name for the ROI
    duplicate,        # image - The image to process
    False,            # fillHolesTrue - Whether to fill holes (False in this case)
    False             # invertTrue - Whether to invert the selection (True in this case)
)

#Select the tissue with all the vessels inside

binaryToSelection(
    1,                # number - ROI index (0 for the first ROI)
    "white",         # colour - Fill color for the ROI
    "Tissue",         # name - Name for the ROI
    duplicate,        # image - The image to process
    1,                # fillHolesTrue - Whether to fill holes (False in this case)
    1                 # invertTrue - Whether to invert the selection (True in this case)
)
rm.select(1)

# Use the new particleSelection function
particleSelection(100000, "Infinity", duplicate, "Combined Particles", "false", "magenta", False)

#Separate vessels from the rest of the tissue
rm.setSelectedIndexes([0,2])
rm.runCommand(duplicate,"AND")
rm.addRoi(duplicate.getRoi())
rm.select(3)
rm.runCommand("Set Fill Color", "red")
rm.runCommand("Rename", "Vessels")

particleSelection(1000, 100000, duplicate, "Cleaned Vessels", "false", "brown", False)

# Create binary image for Cleaned Vessels ROI
rm.select(rm.getCount() - 1)  # Select the last ROI (Cleaned Vessels)
cleaned_vessels_roi = rm.getRoi(4)
binary_cleaned_vessels = create_binary_image_from_roi(imp, cleaned_vessels_roi, "Binary_Cleaned_Vessels")

# Perform binary operations on the Cleaned Vessels binary image
perform_binary_operations(binary_cleaned_vessels)

# Convert the processed binary image back to ROI
IJ.run(binary_cleaned_vessels, "Create Selection", "")
processed_roi = binary_cleaned_vessels.getRoi()

# Add the processed ROI to the ROI Manager
rm.addRoi(processed_roi)
rm.select(rm.getCount() - 1)
rm.runCommand("Set Fill Color", "yellow")
rm.runCommand("Rename", "Processed Cleaned Vessels")

# Close the binary image
binary_cleaned_vessels.close()

print("Script completed successfully. Processed Cleaned Vessels ROI added to ROI Manager.")
