"""
Create a focused sample EXCLUDING category 90 (miscellaneous/catch-all)
Focus on specific, well-defined traffic sign categories
"""
import json
import os
import shutil
from pathlib import Path
import random
from collections import Counter, defaultdict

def create_focused_sample_no_cat90(
    input_json, 
    input_images_dir, 
    output_dir, 
    top_n_categories=15,
    images_per_category=150,
    seed=42
):
    """
    Create a sample focusing on specific categories, EXCLUDING category 90
    
    Args:
        input_json: Path to the original COCO JSON file
        input_images_dir: Directory containing the original images
        output_dir: Directory to save the sampled dataset
        top_n_categories: Number of top categories to focus on (excluding cat 90)
        images_per_category: Target number of images per category
        seed: Random seed for reproducibility
    """
    random.seed(seed)
    
    print("=" * 70)
    print("CREATING FOCUSED SAMPLE (EXCLUDING CATEGORY 90)")
    print("=" * 70)
    
    # Load original data
    print("\nLoading dataset...")
    with open(input_json, 'r') as f:
        data = json.load(f)
    
    print(f"Total images: {len(data['images'])}")
    print(f"Total annotations: {len(data['annotations'])}")
    
    # Get category counts EXCLUDING category 90
    category_counts = Counter(
        ann['category_id'] for ann in data['annotations'] 
        if ann['category_id'] != 90
    )
    
    cat_90_count = sum(1 for ann in data['annotations'] if ann['category_id'] == 90)
    print(f"\nExcluding category 90: {cat_90_count:,} annotations removed")
    print(f"Remaining annotations: {sum(category_counts.values()):,}")
    
    # Get top categories (excluding cat 90)
    top_categories = [cat_id for cat_id, _ in category_counts.most_common(top_n_categories)]
    
    print(f"\n=== Top {top_n_categories} Categories (Excluding Cat 90) ===")
    for i, cat_id in enumerate(top_categories, 1):
        count = category_counts[cat_id]
        print(f"{i:2d}. Category {cat_id:3d}: {count:6d} annotations")
    
    # Group images by which top categories they contain (excluding cat 90)
    image_categories = defaultdict(set)
    for ann in data['annotations']:
        if ann['category_id'] in top_categories:
            image_categories[ann['image_id']].add(ann['category_id'])
    
    # Filter to only images that have at least one top category
    eligible_images = [
        img for img in data['images'] 
        if img['id'] in image_categories and len(image_categories[img['id']]) > 0
    ]
    
    print(f"\nImages containing top categories: {len(eligible_images)}")
    
    # Sample images trying to balance categories
    category_image_map = defaultdict(list)
    for img in eligible_images:
        for cat_id in image_categories[img['id']]:
            category_image_map[cat_id].append(img)
    
    # Sample images per category
    sampled_image_ids = set()
    for cat_id in top_categories:
        available_images = category_image_map[cat_id]
        sample_size = min(images_per_category, len(available_images))
        sampled = random.sample(available_images, sample_size)
        for img in sampled:
            sampled_image_ids.add(img['id'])
    
    sampled_images = [img for img in data['images'] if img['id'] in sampled_image_ids]
    
    print(f"\n=== Sampling Strategy ===")
    print(f"Target images per category: {images_per_category}")
    print(f"Total unique images sampled: {len(sampled_images)}")
    
    # Filter annotations - EXCLUDE category 90
    sampled_annotations = [
        ann for ann in data['annotations'] 
        if ann['image_id'] in sampled_image_ids and ann['category_id'] != 90
    ]
    
    # Count annotations per category in sample
    sampled_category_counts = Counter(ann['category_id'] for ann in sampled_annotations)
    
    print(f"Total annotations (excluding cat 90): {len(sampled_annotations)}")
    print(f"\n=== Sampled Category Distribution ===")
    for cat_id in top_categories:
        count = sampled_category_counts[cat_id]
        images_with_cat = len([img for img in sampled_images if cat_id in image_categories[img['id']]])
        print(f"Category {cat_id:3d}: {count:5d} annotations in {images_with_cat:4d} images")
    
    # Other categories present (excluding cat 90)
    other_categories = sum(
        count for cat_id, count in sampled_category_counts.items() 
        if cat_id not in top_categories and cat_id != 90
    )
    print(f"\nOther specific categories: {other_categories} annotations")
    
    # Report how many category 90 annotations were in these images
    cat_90_in_sample = sum(
        1 for ann in data['annotations']
        if ann['image_id'] in sampled_image_ids and ann['category_id'] == 90
    )
    print(f"Category 90 annotations removed: {cat_90_in_sample}")
    
    # Create new dataset
    sampled_data = {
        'images': sampled_images,
        'annotations': sampled_annotations,
        'categories': data['categories'],
        'info': data.get('info', {}),
        'licenses': data.get('licenses', [])
    }
    
    # Create output directories
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    images_output = output_path / 'images'
    images_output.mkdir(exist_ok=True)
    
    # Save JSON
    json_output = output_path / 'annotations.json'
    with open(json_output, 'w') as f:
        json.dump(sampled_data, f, indent=2)
    
    print(f"\n=== Saving Dataset ===")
    print(f"Annotations saved to: {json_output}")
    
    # Copy images
    print(f"\nCopying {len(sampled_images)} images...")
    copied = 0
    missing = 0
    
    for img in sampled_images:
        src = Path(input_images_dir) / img['file_name']
        dst = images_output / img['file_name']
        
        if src.exists():
            shutil.copy2(src, dst)
            copied += 1
            if copied % 100 == 0:
                print(f"  Copied {copied}/{len(sampled_images)} images...")
        else:
            missing += 1
    
    print(f"\n=== Summary ===")
    print(f"✓ Copied: {copied} images")
    if missing > 0:
        print(f"✗ Missing: {missing} images")
    print(f"✓ Total annotations (excluding cat 90): {len(sampled_annotations)}")
    print(f"✓ Annotations per image: {len(sampled_annotations) / len(sampled_images):.2f}")
    print(f"✓ Number of categories: {len(sampled_category_counts)}")
    print(f"✓ Output directory: {output_path}")
    
    # Save category info
    category_info_file = output_path / 'category_info.txt'
    with open(category_info_file, 'w') as f:
        f.write("Focused Sample - Specific Traffic Sign Categories\n")
        f.write("(Category 90 excluded - it's a miscellaneous catch-all)\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Top {top_n_categories} Categories:\n\n")
        for i, cat_id in enumerate(top_categories, 1):
            count = sampled_category_counts[cat_id]
            images_with_cat = len([img for img in sampled_images 
                                  if cat_id in image_categories[img['id']]])
            f.write(f"{i:2d}. Category {cat_id:3d}: {count:5d} annotations in {images_with_cat:4d} images\n")
        f.write(f"\nTotal unique images: {len(sampled_images)}\n")
        f.write(f"Total annotations: {len(sampled_annotations)}\n")
        f.write(f"Category 90 annotations removed: {cat_90_in_sample}\n")
        f.write(f"\nThis sample focuses on specific, well-defined traffic sign types.\n")
    
    print(f"✓ Category info saved to: {category_info_file}")
    
    return sampled_data, top_categories


if __name__ == "__main__":
    # Paths
    project_dataset = Path("/Users/alejandromarchini/Documents/MSAAI/521/project_dataset")
    train_json = project_dataset / "train.json"
    train_images = project_dataset / "mtsd_fully_annotated_train_images" / "images"
    
    # Output directory
    output_dir = Path("/Users/alejandromarchini/Documents/MSAAI/521/AAI-521-Group3/clean_sample")
    
    print("\nCreating a clean sample with specific traffic sign categories...")
    print("Category 90 (miscellaneous/catch-all) will be EXCLUDED\n")
    
    # Create focused sample excluding category 90
    # Taking top 15 categories (excluding cat 90) with ~150 images each
    sample_dataset, top_cats = create_focused_sample_no_cat90(
        input_json=train_json,
        input_images_dir=train_images,
        output_dir=output_dir,
        top_n_categories=15,
        images_per_category=150,
        seed=42
    )
    
    print("\n" + "=" * 70)
    print("DONE! Clean sample created without category 90.")
    print("Use the 'clean_sample' directory for training.")
    print("=" * 70)
