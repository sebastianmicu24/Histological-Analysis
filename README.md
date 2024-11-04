# Description
Jython code to separate different part of histological tissues for a quantifiable analysis

# What does this Macro do?
1) Separates the tissue from the background
2) Separates the vessels from the tissue
3) Using particle analysis selects all nuclei
4) Using Voronoi Tesselation creates an estimate of the hepatocytic Cytoplasm

# On what tissues does this work?
Has been tried only on hepatic tissues coloured with Hematoxylin & Eosin.

# Functions to be implemented
1) Cleaning border cells to not include background
2) Removing nuclear selection from cellular selection to get the cytoplasm
3) Analyzing colour histogram for each cell
4) Exporting all data in a custom table
