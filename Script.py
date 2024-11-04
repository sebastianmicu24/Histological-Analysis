##################### IMPORTS ###################################

import sys
import os
from ij import IJ, ImagePlus, WindowManager
from ij.process import ImageProcessor
from ij.plugin.frame import RoiManager
from ij.io import OpenDialog
from ij.gui import Roi, ShapeRoi

##################### FUNCTION DEFINITIONS ###################################

# Functions from tissueSelection.py
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

def particleSelection(minSize, maxSize, image, name, fill, color, invertTrue):
    if invertTrue:
        IJ.run(image, "Invert LUT", "")
    
    initial_roi_count = rm.getCount()
    IJ.run(image, "Analyze Particles...", "size={0}-{1} pixel show=[Overlay] clear".format(minSize, maxSize))

    overlay = image.getOverlay()
    if overlay is not None and overlay.size() > 0:
        combined_roi = ShapeRoi(overlay.get(0))
        for i in range(1, overlay.size()):
            combined_roi.or(ShapeRoi(overlay.get(i)))
        
        for i in range(rm.getCount() - 1, initial_roi_count - 1, -1):
            rm.select(i)
            rm.runCommand("Delete")
        
        rm.addRoi(combined_roi)
        rm.select(rm.getCount() - 1)
        rm.runCommand("Rename", name)
        rm.runCommand("Set Fill Color", color)

        if fill.lower() == "true":
            rm.runCommand("Fill")

def create_binary_image_from_roi(imp, roi, name):
    ip = imp.getProcessor().createProcessor(imp.getWidth(), imp.getHeight())
    ip.setColor(0)
    ip.fill()
    
    ip.setColor("#ffffff")
    ip.fill(roi)
    
    binary_imp = ImagePlus(name, ip)
    
    IJ.run(binary_imp, "8-bit", "")
    ip.setColor(255)
    
    IJ.setThreshold(binary_imp, 2, 255)
    IJ.run(binary_imp, "Convert to Mask", "")
    
    binary_imp.show()
    return binary_imp

def binary_fill_holes(image):
    IJ.run(image, "8-bit", "")
    IJ.run(image, "Dilate", "")
    IJ.run(image, "Dilate", "")
    IJ.run(image, "Dilate", "")
    IJ.run(image, "Fill Holes", "")
    IJ.run(image, "Erode", "")
    IJ.run(image, "Erode", "")
    IJ.run(image, "Erode", "")

# Functions from nucleiSelection.py
def particleSelection_nuclei(minSize, maxSize, image, name, fill, color, invertTrue):
    if invertTrue:
        IJ.run(image, "Invert LUT", "")
    
    initial_roi_count = rm.getCount()
    IJ.run(image, "Analyze Particles...", "size={0}-{1} pixel show=[Overlay] add".format(minSize, maxSize))

    final_roi_count = rm.getCount()
    
    for i in range(initial_roi_count, final_roi_count):
        rm.select(i)
        rm.runCommand("Set Fill Color", color)
        rm.runCommand("Rename", "{0}_{1}".format(name, i-initial_roi_count+1))

        if fill.lower() == "true":
            rm.runCommand("Fill")
    
    rm.runCommand("Show All")
    return initial_roi_count, final_roi_count

def create_background_points(image, spacing=10):
    width = image.getWidth()
    height = image.getHeight()
    background_points = []
    
    for x in range(0, width, spacing):
        background_points.append((x, 0))
        background_points.append((x, height - 1))
    
    for y in range(spacing, height - spacing, spacing):
        background_points.append((0, y))
        background_points.append((width - 1, y))
    
    return background_points

def create_voronoi_cells(image, initial_count, final_count):
    points_imp = IJ.createImage("Points", "8-bit black", image.getWidth(), image.getHeight(), 1)
    points_imp.show()
    
    ip = points_imp.getProcessor()
    ip.setColor(255)
    
    for i in range(initial_count, final_count):
        rm.select(i)
        roi = rm.getRoi(i)
        bounds = roi.getBounds()
        x = bounds.x + bounds.width/2
        y = bounds.y + bounds.height/2
        ip.drawDot(int(x), int(y))
    
    background_points = create_background_points(image)
    for x, y in background_points:
        ip.drawDot(x, y)
    
    points_imp.updateAndDraw()
    
    IJ.setAutoThreshold(points_imp, "Default dark")
    IJ.run(points_imp, "Convert to Mask", "")
    
    IJ.run(points_imp, "Voronoi", "")
    
    IJ.setRawThreshold(points_imp, 1, 255, None)
    IJ.run(points_imp, "Convert to Mask", "")
    
    counter = 0
    for i in range(initial_count, final_count):
        rm.select(i)
        nucleus_roi = rm.getRoi(i)
        bounds = nucleus_roi.getBounds()
        x = bounds.x + bounds.width/2
        y = bounds.y + bounds.height/2
        
        IJ.doWand(int(x), int(y))
        
        cell_roi = points_imp.getRoi()
        
        if cell_roi is not None:
            rm.addRoi(cell_roi)
            rm.select(rm.getCount()-1)
            rm.runCommand("Set Fill Color", "magenta")
            rm.runCommand("Rename", "Cell_{0}".format(i-initial_count+1))

##################### MAIN SCRIPT ###################################

def main():
    # Close all open images
    for imp in WindowManager.getImageTitles():
        WindowManager.getImage(imp).close()

    # Clear ROI Manager if it was opened
    global rm
    rm = RoiManager.getInstance()
    if rm is not None:
        rm.reset()

    # Initialize ROI Manager
    RM = RoiManager()
    rm = RM.getRoiManager()

    # Open a dialog to select the image file
    od = OpenDialog("Select the image file", None)
    file_path = od.getPath()

    if file_path is None:
        print("No file selected. Exiting script.")
        return

    # Open the specified image
    imp = IJ.openImage(file_path)

    if imp is None:
        print("Failed to open image: {0}".format(file_path))
        print("Please check if the file exists and is accessible.")
        return

    # Tissue Selection
    imp.setTitle("Copy_1")
    imp.show()

    duplicate = imp.duplicate()
    duplicate.setTitle("Copy_2")
    duplicate.show()

    ImagePlus.setDefault16bitRange(16)
    duplicate.setDisplayRange(60, 215)
    duplicate.updateAndDraw()
    IJ.run(duplicate, "Despeckle", "")
    IJ.run(duplicate, "8-bit", "")
    IJ.setAutoThreshold(duplicate, "Default no-reset")
    IJ.setRawThreshold(duplicate, 215, 255, None)
    IJ.run(duplicate, "Convert to Mask", "")

    binaryToSelection(0, "white", "All background", duplicate, False, False)
    binaryToSelection(1, "white", "Tissue", duplicate, True, True)
    rm.select(1)

    particleSelection(100000, "Infinity", duplicate, "Combined Particles", "false", "magenta", False)

    rm.setSelectedIndexes([0,2])
    rm.runCommand(duplicate, "AND")
    rm.addRoi(duplicate.getRoi())
    rm.select(3)
    rm.runCommand("Set Fill Color", "red")
    rm.runCommand("Rename", "Vessels")

    particleSelection(2000, 1000000, duplicate, "Cleaned Vessels", "false", "black", False)

    rm.select(rm.getCount() - 1)
    cleaned_vessels_roi = rm.getRoi(4)
    binary_cleaned_vessels = create_binary_image_from_roi(imp, cleaned_vessels_roi, "Binary_Cleaned_Vessels")

    binary_fill_holes(binary_cleaned_vessels)

    IJ.run(binary_cleaned_vessels, "Create Selection", "")
    processed_roi = binary_cleaned_vessels.getRoi()

    rm.addRoi(processed_roi)
    rm.select(rm.getCount() - 1)
    rm.runCommand("Set Fill Color", "yellow")
    rm.runCommand("Rename", "Processed Cleaned Vessels")

    binary_cleaned_vessels.close()

    rm.select(4)
    rm.runCommand(duplicate,"Delete")
    rm.select(3)
    rm.runCommand(duplicate,"Delete")
    rm.select(1)
    rm.runCommand(duplicate,"Delete")
    rm.select(0)
    rm.runCommand(duplicate,"Delete")

    rm.setSelectedIndexes([0,1])
    rm.runCommand(imp,"XOR")
    IJ.run(imp, "Make Inverse", "")
    new_roi = imp.getRoi()
    if new_roi is not None:
        rm.addRoi(new_roi)
    rm.select(2)
    IJ.setForegroundColor(255, 255, 255)
    rm.runCommand(imp,"Fill")

    duplicate.close()

    print("Tissue selection completed successfully.")

    # Deselect everything without closing any page
    rm.runCommand(imp, "Deselect")
    imp.killRoi()

    # Nuclei Selection
    if imp.getType() != ImagePlus.COLOR_RGB:
        print("Error: Image must be RGB color. Please select an RGB image.")
        print("Current image type: {0}".format(imp.getType()))
        return

    imp.setTitle("Original")

    try:
        print("Attempting to duplicate image...")
        duplicate = imp.duplicate()
        print("Image duplicated successfully.")
    except Exception as e:
        print("Error occurred while duplicating image:")
        print(str(e))
        return

    duplicate.setTitle("Deconvolved")
    duplicate.show()

    try:
        IJ.run(duplicate, "Colour Deconvolution", "vectors=[H&E]")

        nuclei_image = WindowManager.getImage("Deconvolved-(Colour_1)")
        if nuclei_image is None:
            print("Error: Color deconvolution failed. Could not get nuclei image.")
            return
            
        nuclei_image.setTitle("Nuclei")

        color2_imp = WindowManager.getImage("Deconvolved-(Colour_2)")
        if color2_imp is not None:
            color2_imp.close()
            
        color3_imp = WindowManager.getImage("Deconvolved-(Colour_3)")
        if color3_imp is not None:
            color3_imp.close()

        IJ.run(nuclei_image, "Despeckle", "")
        IJ.run(nuclei_image, "Gaussian Blur...", "sigma=2")
        
        kernel = "-1 -1 -1 -1 9 -1 -1 -1 -1"
        IJ.run(nuclei_image, "Convolve...", "text1=[" + kernel + "]")
        
        IJ.setRawThreshold(nuclei_image, 0, 237, None)
        IJ.run(nuclei_image, "Convert to Mask", "")
        
        IJ.run(nuclei_image, "Erode", "")
        IJ.run(nuclei_image, "Dilate", "")
        
        IJ.run(nuclei_image, "Watershed", "")
        
        IJ.run(nuclei_image, "Fill Holes", "")
        
        IJ.run(nuclei_image, "Open", "")

        initial_count, final_count = particleSelection_nuclei(50, 500, nuclei_image, "Nucleus", "false", "black", False)

        create_voronoi_cells(nuclei_image, initial_count, final_count)

        save_dir = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        roi_path = os.path.join(save_dir, base_name + "_ROIs.zip")
        rm.runCommand("Save", roi_path)

        print("Script completed successfully.")
        print("Nuclei and cell ROIs added to ROI Manager and saved to: " + roi_path)
        
    except Exception as e:
        print("An error occurred during processing:")
        print(str(e))

if __name__ == '__main__':
    main()
