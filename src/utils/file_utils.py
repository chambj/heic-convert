def list_heic_files(directory):
    import os
    heic_files = [f for f in os.listdir(directory) if f.lower().endswith('.heic')]
    return heic_files

def save_image(image, output_path, format='PNG'):
    image.save(output_path, format=format, quality=95)