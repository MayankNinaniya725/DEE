import json
import os
import logging

logger = logging.getLogger('extractor')

def load_vendor_config(vendor_path):
    """
    Load a vendor configuration from the given path.
    
    Args:
        vendor_path: The full path to the vendor config file
        
    Returns:
        The loaded JSON configuration
        
    Raises:
        FileNotFoundError: If the config file does not exist
    """
    if not os.path.exists(vendor_path):
        raise FileNotFoundError(f"Config for vendor '{vendor_path}' not found.")
    
    with open(vendor_path, 'r') as file:
        return json.load(file)

def find_vendor_config(vendor, settings):
    """
    Find vendor configuration by trying multiple locations.
    
    Args:
        vendor: The Vendor model instance
        settings: Django settings module
        
    Returns:
        A tuple (config_dict, config_path) with the loaded config and the path it was found at,
        or (None, None) if no config was found
    """
    # 1. First try the media path (for uploaded configs)
    media_config_path = os.path.join(settings.MEDIA_ROOT, vendor.config_file.name)
    
    # 2. Also try the direct path from vendor.config_file
    direct_config_path = vendor.config_file.path if hasattr(vendor.config_file, 'path') else None
    
    # 3. Try a path with just the base filename (without random suffix)
    base_name = os.path.basename(vendor.config_file.name)
    if '_' in base_name:
        # Remove random suffix (e.g., citic_steel_0VwOwk2.json -> citic_steel.json)
        parts = base_name.split('_')
        if len(parts) > 1 and '.' in parts[-1]:
            # Check if last part contains random characters and extension
            last_part = parts[-1]
            ext_idx = last_part.rfind('.')
            if ext_idx > 0:
                clean_name = '_'.join(parts[:-1]) + last_part[ext_idx:]
                template_config_path = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', clean_name)
            else:
                template_config_path = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', base_name)
        else:
            template_config_path = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', base_name)
    else:
        template_config_path = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', base_name)
    
    # Try each path in order
    config_paths = [
        media_config_path,
        direct_config_path,
        template_config_path,
        # Final fallback - try base template
        os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', base_name)
    ]
    
    for path in config_paths:
        if path and os.path.exists(path):
            try:
                config = load_vendor_config(path)
                logger.info(f"Successfully loaded vendor config from {path}")
                return config, path
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {str(e)}")
    
    # If no config found, create a simple one
    logger.warning(f"No config found for vendor {vendor.name}, creating placeholder")
    # Create minimal config
    placeholder_config = {
        "vendor_name": vendor.name,
        "key_fields": ["PLATE_NO", "HEAT_NO", "TEST_CERT_NO"],
        "extraction_rules": {"PLATE_NO": {}, "HEAT_NO": {}, "TEST_CERT_NO": {}}
    }
    
    # Save this config for future use
    try:
        placeholder_path = os.path.join(settings.BASE_DIR, 'extractor', 'vendor_configs', base_name)
        with open(placeholder_path, 'w') as f:
            json.dump(placeholder_config, f, indent=2)
        logger.info(f"Created placeholder config at {placeholder_path}")
        return placeholder_config, placeholder_path
    except Exception as e:
        logger.error(f"Failed to save placeholder config: {str(e)}")
        return placeholder_config, None
