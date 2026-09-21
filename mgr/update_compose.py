import yaml
import requests
import os
import shutil
import sys

REMOTE_URL = "https://raw.githubusercontent.com/Alfresco/acs-deployment/master/docker-compose/community-compose.yaml"
LOCAL_FILE = "docker-compose.yaml"
BACKUP_FILE = "docker-compose.yaml.bak"
CUSTOM_MARKER_START = "##########CUSTOM SERVICES BELOW##########"
CUSTOM_MARKER_END = "#" # This is a bit ambiguous, we'll look for the comment

def get_remote_yaml():
    print(f"Fetching remote YAML from {REMOTE_URL}...")
    response = requests.get(REMOTE_URL)
    response.raise_for_status()
    return yaml.safe_load(response.text)

def load_local_yaml():
    if not os.path.exists(LOCAL_FILE):
        raise FileNotFoundError(f"{LOCAL_FILE} not found.")
    with open(LOCAL_FILE, 'r') as f:
        return yaml.safe_load(f)

def backup_local_file():
    print(f"Creating backup: {BACKUP_FILE}")
    shutil.copy2(LOCAL_FILE, BACKUP_FILE)

def update_compose():
    try:
        backup_local_file()
        remote_data = get_remote_yaml()
        local_data = load_local_yaml()

        # We want to update the 'services' section of the local file
        # based on the remote 'services' section.
        # However, we must preserve local-only services and custom settings.
        
        remote_services = remote_data.get('services', {})
        local_services = local_data.get('services', {})

        # Identify services in local that are NOT in remote (potential custom services)
        custom_services_keys = [k for k in local_services.keys() if k not in remote_services]
        
        # Start building the new services dictionary
        new_services = {}

        # 1. Add/Update services from remote
        for service_name, remote_config in remote_services.items():
            if service_name in local_services:
                # Merge remote config into local config to preserve local specific tweaks
                # if they aren't being overwritten by remote.
                # A simple way is to take the remote config as base and update with local.
                # But the user wants to "update based on online version", 
                # implying the online version is the truth for these services.
                
                # Let's take the remote config but try to preserve local 'environment' or 'volumes' 
                # if they are highly customized. This is tricky.
                # For now, let's follow the instruction: "update the local... based on an online version"
                # which usually means the remote version's settings for that service take precedence.
                new_services[service_name] = remote_config
                print(f"Updated service: {service_name}")
            else:
                # This service is in remote but not in local. 
                # Should we add it? The prompt says "update the local... based on an online version".
                # Usually, this means if it's new in remote, we add it.
                new_services[service_name] = remote_config
                print(f"Added new service from remote: {service_name}")

        # 2. Add back the local-only (custom) services
        for service_name in custom_services_keys:
            new_services[service_name] = local_services[service_name]
            print(f"Preserved custom service: {service_name}")

        # Construct the new docker-compose structure
        new_data = local_data.copy()
        new_data['services'] = new_services
        
        # Note: This might lose top-level keys that were only in local but not in remote.
        # But the remote is the source of truth for the deployment.
        
        # Write the updated content back to the file
        with open(LOCAL_FILE, 'w') as f:
            yaml.dump(new_data, f, sort_keys=False)
        
        print("Successfully updated docker-compose.yaml")
        return True, "Update successful"

    except Exception as e:
        print(f"Error during update: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    success, message = update_compose()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
