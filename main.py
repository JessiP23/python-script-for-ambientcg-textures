import os
import shutil
import subprocess
from pathlib import Path

def download_and_extract_texture_images(
    output_dir="texture_images_only",
    temp_dir="temp_textures",
    sizes=["2k", "4k"],
    keep_types=["diff", "col", "albedo", "preview"]
):
    """
    Download all textures and extract only the main image files
    """
    
    print("🚀 Starting texture image extraction...")
    print(f"📁 Output directory: {output_dir}")
    print(f"📏 Sizes: {sizes}")
    print(f"🖼️ Keeping file types: {keep_types}")
    
    # Step 1: Download all textures to temp directory
    print("\n📥 Step 1: Downloading all textures...")
    
    cmd = [
        "polydown", "textures",
        "-f", temp_dir,
        "-s"] + sizes + ["-o"]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Download complete!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")
        return
    
    # Step 2: Extract only the main texture images
    print("\n🔍 Step 2: Extracting main texture images...")
    
    os.makedirs(output_dir, exist_ok=True)
    
    temp_path = Path(temp_dir)
    output_path = Path(output_dir)
    
    copied_count = 0
    skipped_count = 0
    
    # Walk through all downloaded files
    for file_path in temp_path.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.png', '.jpeg']:
            filename = file_path.name.lower()
            
            # Check if this is a main texture image
            is_main_texture = False
            for keep_type in keep_types:
                if keep_type in filename:
                    is_main_texture = True
                    break
            
            # Also keep preview images (they usually don't have specific keywords)
            if not is_main_texture and not any(skip_word in filename for skip_word in 
                ['normal', 'rough', 'disp', 'displacement', 'ao', 'ambient', 'spec', 'specular', 'bump', 'height']):
                is_main_texture = True
            
            if is_main_texture:
                # Create a unique filename to avoid conflicts
                texture_name = file_path.parent.name
                new_filename = f"{texture_name}_{file_path.name}"
                new_path = output_path / new_filename
                
                # Copy the file
                shutil.copy2(file_path, new_path)
                copied_count += 1
                
                if copied_count % 50 == 0:
                    print(f"📋 Copied {copied_count} images...")
            else:
                skipped_count += 1
    
    # Step 3: Clean up temp directory
    print(f"\n🧹 Step 3: Cleaning up temporary files...")
    shutil.rmtree(temp_dir)
    
    # Final summary
    print(f"\n🎉 Extraction Complete!")
    print(f"✅ Copied {copied_count} main texture images")
    print(f"⏭️ Skipped {skipped_count} technical files (normal, roughness, etc.)")
    print(f"📁 Images saved to: {os.path.abspath(output_dir)}")

def download_category_images(category, output_dir="texture_images", sizes=["2k", "4k"]):
    """Download images from a specific category only"""
    
    print(f"📥 Downloading category: {category}")
    
    cmd = [
        "polydown", "textures",
        "-c", category,
        "-f", f"temp_{category}",
        "-s"] + sizes + ["-o"]
    
    try:
        subprocess.run(cmd, check=True)
        
        # Extract images from this category
        category_output = os.path.join(output_dir, category)
        os.makedirs(category_output, exist_ok=True)
        
        temp_path = Path(f"temp_{category}")
        output_path = Path(category_output)
        
        copied = 0
        for file_path in temp_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.jpg', '.png', '.jpeg']:
                filename = file_path.name.lower()
                
                # Skip technical maps
                if not any(skip_word in filename for skip_word in 
                    ['normal', 'rough', 'disp', 'displacement', 'ao', 'ambient', 'spec', 'specular', 'bump', 'height']):
                    
                    new_path = output_path / file_path.name
                    shutil.copy2(file_path, new_path)
                    copied += 1
        
        # Clean up
        shutil.rmtree(f"temp_{category}")
        
        print(f"✅ {category}: {copied} images")
        return copied
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to download {category}: {e}")
        return 0

def download_all_categories_separately():
    """Download each category into separate folders"""
    
    categories = [
        'outdoor', 'man made', 'floor', 'wall', 'natural', 'terrain', 'dirty', 'rock', 
        'brick', 'plaster-concrete', 'concrete', 'indoor', 'wood', 'sand', 'clean', 
        'road', 'cobblestone', 'plaster', 'roofing', 'metal', 'aerial', 'bark', 
        'asphalt', 'raw wood', 'fabric', 'sandstone', 'gravel', 'snow', 'tiles', 
        'leather', 'cotton', 'denim', 'food', 'carpet'
    ]
    
    base_dir = "texture_dataset_by_category"
    total_images = 0
    
    print(f"📁 Downloading {len(categories)} categories...")
    
    for i, category in enumerate(categories, 1):
        print(f"\n[{i}/{len(categories)}] Processing: {category}")
        count = download_category_images(category, base_dir)
        total_images += count
    
    print(f"\n🎉 All categories downloaded!")
    print(f"📊 Total images: {total_images}")
    print(f"📁 Saved to: {os.path.abspath(base_dir)}")

def main():
    print("Choose your download method:")
    print("1. Download ALL textures (mixed) - Fast, good for ML training")
    print("2. Download ALL textures (extract only main images) - Clean dataset")
    print("3. Download by categories (organized folders)")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        # Simple download all
        print("📥 Downloading all textures...")
        cmd = ["polydown", "textures", "-f", "all_textures", "-s", "2k", "4k", "-o"]
        subprocess.run(cmd, check=True)
        print("✅ Done! Check 'all_textures' folder")
        
    elif choice == "2":
        # Download and extract only main images
        download_and_extract_texture_images()
        
    elif choice == "3":
        # Download by categories
        download_all_categories_separately()
        
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()