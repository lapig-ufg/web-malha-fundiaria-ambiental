import rasterio
import numpy as np
import sys
import os

def explore_tif(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    print(f"--- Exploring: {file_path} ---")
    
    with rasterio.open(file_path) as src:
        # Print Metadata
        print(f"Driver: {src.driver}")
        print(f"Width: {src.width}, Height: {src.height}")
        print(f"Number of Bands: {src.count}")
        print(f"Coordinate Reference System (CRS): {src.crs}")
        print(f"Transform (Affine):\n{src.transform}")
        print(f"Bounds: {src.bounds}")
        print(f"NoData Value: {src.nodata}")
        
        # Read the first band (usually where land cover data is)
        band1 = src.read(1)
        
        # Calculate Unique Values (Classes)
        unique_values = np.unique(band1)
        print(f"\nUnique Values (Classes) in Band 1:")
        print(unique_values)
        
        # Print value counts for better insight
        values, counts = np.unique(band1, return_counts=True)
        print("\nClass Distribution:")
        for v, c in zip(values, counts):
            print(f"Value {v}: {c} pixels")

if __name__ == "__main__":
    # Default file for testing if none provided
    default_file = "../../data/mapbiomas/brazil_coverage_2023_reclassificado.tif"
    
    path = sys.argv[1] if len(sys.argv) > 1 else default_file
    
    # Adjust path if relative to tools/tif-explorer
    if not os.path.isabs(path) and not os.path.exists(path):
        # Try relative to the script's parent (tools) or root
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(script_dir))
        potential_path = os.path.join(root_dir, "data", "mapbiomas", os.path.basename(path))
        if os.path.exists(potential_path):
            path = potential_path
        else:
            # Try exactly what was provided relative to root
            path = os.path.join(root_dir, path.replace("../../", ""))

    explore_tif(path)
