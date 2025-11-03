#!/usr/bin/env python3
"""
Redis Enterprise Agent Permissions Management Script
This script can create new agents or update existing permissions

Environment Variable Interpolation:
The script supports environment variable interpolation in YAML config files using the ${ENV_VAR} syntax.
For example, you can use ${ADMIN_USER}:${ADMIN_PASSWORD} in your basic_auth configuration.
If an environment variable is not set, a warning will be printed and the original pattern preserved.
"""

import json
import sys
import argparse
import warnings
import re
import time
import yaml
import os
from typing import Optional, Dict, List, Tuple, Any
import requests
from urllib.parse import urlparse

# Note: SSL warnings are suppressed conditionally based on --skip-ssl-verify argument


def interpolate_env_vars(data: Any) -> Any:
    """
    Recursively interpolate environment variables in data structures.
    Replaces ${ENV_VAR} patterns with actual environment variable values.
    
    Args:
        data: The data to process (can be string, dict, list, or other types)
    
    Returns:
        The data with environment variables interpolated
    """
    if isinstance(data, str):
        # Use regex to find all ${ENV_VAR} patterns
        pattern = r'\$\{([^}]+)\}'
        
        def replace_env_var(match):
            env_var_name = match.group(1)
            env_var_value = os.getenv(env_var_name)
            if env_var_value is None:
                print(f"⚠ Warning: Environment variable '{env_var_name}' is not set")
                return match.group(0)  # Return original pattern if env var not found
            return env_var_value
        
        return re.sub(pattern, replace_env_var, data)
    
    elif isinstance(data, dict):
        return {key: interpolate_env_vars(value) for key, value in data.items()}
    
    elif isinstance(data, list):
        return [interpolate_env_vars(item) for item in data]
    
    else:
        # Return as-is for other types (int, float, bool, etc.)
        return data


class RedisEnterpriseAPI:
    """Client for Redis Enterprise REST API"""
    
    def __init__(self, endpoint: str, username: str, password: str, skip_ssl_verify: bool = True):
        self.endpoint = endpoint.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.verify = not skip_ssl_verify  # Skip SSL verification by default
        self.session.headers.update({'Content-Type': 'application/json'})
        
        # Only suppress warnings if SSL verification is disabled
        if skip_ssl_verify:
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    
    def test_connectivity(self) -> bool:
        """Test API connectivity"""
        try:
            response = self.session.get(f"{self.endpoint}/v1/bdbs")
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def get_acls(self) -> List[Dict]:
        """Get all ACLs"""
        response = self.session.get(f"{self.endpoint}/v1/redis_acls")
        response.raise_for_status()
        return response.json()
    
    def get_roles(self) -> List[Dict]:
        """Get all roles"""
        response = self.session.get(f"{self.endpoint}/v1/roles")
        response.raise_for_status()
        return response.json()
    
    def get_users(self) -> List[Dict]:
        """Get all users"""
        response = self.session.get(f"{self.endpoint}/v1/users")
        response.raise_for_status()
        return response.json()
    
    def get_databases(self) -> List[Dict]:
        """Get all databases with their permissions"""
        response = self.session.get(f"{self.endpoint}/v1/bdbs")
        response.raise_for_status()
        return response.json()
    
    def create_acl(self, name: str, acl_rules: str) -> Dict:
        """Create a new ACL"""
        data = {"name": name, "acl": acl_rules}
        response = self.session.post(f"{self.endpoint}/v1/redis_acls", json=data)
        response.raise_for_status()
        return response.json()
    
    def create_role(self, name: str, management: str = "cluster_member") -> Dict:
        """Create a new role"""
        data = {"name": name, "management": management}
        response = self.session.post(f"{self.endpoint}/v1/roles", json=data)
        response.raise_for_status()
        return response.json()
    
    def create_user(self, email: str, password: str, name: str, role_uids: List[int]) -> Dict:
        """Create a new user"""
        data = {
            "email": email,
            "password": password,
            "name": name,
            "role_uids": role_uids
        }
        response = self.session.post(f"{self.endpoint}/v1/users", json=data)
        response.raise_for_status()
        return response.json()
    
    def update_database_permissions(self, db_uid: int, roles_permissions: List[Dict]) -> bool:
        """Update database permissions"""
        data = {"roles_permissions": roles_permissions}
        try:
            response = self.session.put(f"{self.endpoint}/v1/bdbs/{db_uid}", json=data)
            if response.status_code == 200:
                return True
            else:
                print(f"    API Error: Status {response.status_code}, Response: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"    Request Error: {e}")
            return False
    
    def delete_acl(self, acl_uid: int) -> bool:
        """Delete an ACL"""
        response = self.session.delete(f"{self.endpoint}/v1/redis_acls/{acl_uid}")
        return response.status_code == 200
    
    def delete_role(self, role_uid: int) -> bool:
        """Delete a role"""
        response = self.session.delete(f"{self.endpoint}/v1/roles/{role_uid}")
        return response.status_code == 200
    
    def delete_user(self, user_uid: int) -> bool:
        """Delete a user"""
        response = self.session.delete(f"{self.endpoint}/v1/users/{user_uid}")
        return response.status_code == 200


class AgentManager:
    """Manages Redis Enterprise agent creation and permission updates"""
    
    def __init__(self, api: RedisEnterpriseAPI):
        self.api = api
    
    def find_existing_agent(self, agent_name: str) -> Optional[Dict]:
        """Find existing agent components"""
        existing = {}
        
        # Check for existing ACL
        try:
            acls = self.api.get_acls()
            for acl in acls:
                if acl['name'] == f"{agent_name}-acl":
                    existing['acl'] = acl
                    break
        except requests.RequestException:
            pass
        
        # Check for existing role
        try:
            roles = self.api.get_roles()
            for role in roles:
                if role['name'] == f"{agent_name}-role":
                    existing['role'] = role
                    break
        except requests.RequestException:
            pass
        
        # Check for existing user
        try:
            users = self.api.get_users()
            for user in users:
                # Check by name first, then by email (since users might be created with email as name)
                # Also check if the name or email contains the agent_name
                user_name = user.get('name', '')
                user_email = user.get('email', '')
                
                if (user_name == agent_name or 
                    user_email == f"{agent_name}@example.com" or 
                    user_email == agent_name or
                    user_name == f"{agent_name}@example.com" or
                    user_name == f"{agent_name}@re.demo" or
                    user_email == f"{agent_name}@re.demo"):
                    existing['user'] = user
                    break
        except requests.RequestException:
            pass
        
        return existing if existing else None
    
    def wait_for_component_deletion(self, component_type: str, component_name: str, max_retries: int = 10, delay: float = 2.0) -> bool:
        """Wait for a component to be deleted, with retries"""
        for attempt in range(max_retries):
            try:
                if component_type == 'acl':
                    acls = self.api.get_acls()
                    if not any(acl['name'] == component_name for acl in acls):
                        return True
                elif component_type == 'role':
                    roles = self.api.get_roles()
                    if not any(role['name'] == component_name for role in roles):
                        return True
                elif component_type == 'user':
                    users = self.api.get_users()
                    if not any(user['name'] == component_name for user in users):
                        return True
                
                if attempt < max_retries - 1:
                    print(f"    Waiting for {component_type} deletion to propagate... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
            except requests.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(delay)
        
        return False
    
    def create_new_agent(self, agent_name: str, agent_password: str, acl_rules: str = None, role_management: str = "cluster_member", agent_email: str = None, database_filter: str = None, skip_existing: bool = False, force: bool = False, skip_all_databases: bool = False, skip_user_creation: bool = False) -> bool:
        """Create a new agent with ACL, role, user, and database permissions"""
        print(f"Creating new permissions for: {agent_name}")
        
        try:
            # Check for existing components
            existing_components = self.find_existing_agent(agent_name)
            
            # Handle partial component existence
            if existing_components:
                missing_components = []
                all_components = ['acl', 'role', 'user']
                for component in all_components:
                    if component not in existing_components:
                        missing_components.append(component)
                
                if missing_components:
                    print(f"\n⚠ Partial components found for agent '{agent_name}':")
                    for component, details in existing_components.items():
                        print(f"  ✓ {component.upper()}: {details['name']} (UID: {details['uid']})")
                    for component in missing_components:
                        print(f"  ✗ {component.upper()}: Missing")
                    
                    if not force:
                        print(f"\nMissing components: {', '.join(missing_components)}")
                        print("Use --force to recreate missing components or --update to update existing permissions.")
                        return False
                    else:
                        print(f"\n🔄 Force mode enabled. Will create missing components: {', '.join(missing_components)}")
                else:
                    # All components exist
                    if not force:
                        print(f"\n⚠ All components for agent '{agent_name}' already exist:")
                        for component, details in existing_components.items():
                            print(f"  - {component.upper()}: {details['name']} (UID: {details['uid']})")
                        print("\nUse --force to recreate existing components or --update to update existing permissions.")
                        return False
                    else:
                        print(f"\n🔄 Force mode enabled. Deleting all existing components for agent '{agent_name}':")
                        
                        # First, clean up database permissions for the existing role/ACL combination
                        if 'role' in existing_components and 'acl' in existing_components:
                            role_uid = existing_components['role']['uid']
                            acl_uid = existing_components['acl']['uid']
                            print(f"  Cleaning up database permissions for role UID {role_uid} and ACL UID {acl_uid}")
                            if not self.cleanup_database_permissions(role_uid, acl_uid, agent_name, database_filter):
                                print(f"    ⚠ Warning: Database permissions cleanup may have failed")
                        
                        # Delete in dependency order: user -> role -> acl
                        deletion_order = ['user', 'role', 'acl']
                        for component in deletion_order:
                            if component in existing_components:
                                details = existing_components[component]
                                print(f"  Deleting {component}: {details['name']} (UID: {details['uid']})")
                                try:
                                    if component == 'acl':
                                        self.api.delete_acl(details['uid'])
                                    elif component == 'role':
                                        self.api.delete_role(details['uid'])
                                    elif component == 'user':
                                        self.api.delete_user(details['uid'])
                                    print(f"    ✓ {component.upper()} deleted successfully")
                                    
                                    # Wait for deletion to propagate
                                    if not self.wait_for_component_deletion(component, details['name']):
                                        print(f"    ⚠ Warning: {component} deletion may not have propagated fully")
                                except requests.RequestException as e:
                                    print(f"    ✗ Failed to delete {component}: {e}")
                                    return False
                        
                        print("✓ All existing components deleted")
                        existing_components = None
            
            acl = None
            role = None
            user = None
            
            # Create or get ACL
            acl_name = f"{agent_name}-acl"
            if existing_components and 'acl' in existing_components:
                acl = existing_components['acl']
                print(f"✓ Using existing ACL: {acl_name} (UID: {acl['uid']})")
            else:
                print("Creating ACL...")
                if acl_rules is None:
                    acl_rules = "+@read +info +ping +config|get +client|list +memory +latency"
                
                # Retry creation with delay if component still exists
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        acl = self.api.create_acl(acl_name, acl_rules)
                        print(f"✓ ACL created successfully with UID: {acl['uid']}")
                        break
                    except requests.RequestException as e:
                        if "409" in str(e) and "Conflict" in str(e):
                            if attempt < max_retries - 1:
                                print(f"    ACL still exists, waiting before retry... (attempt {attempt + 1}/{max_retries})")
                                time.sleep(3.0)
                            else:
                                # Final attempt - check if ACL actually exists and try to get its UID
                                print(f"    Checking if ACL '{acl_name}' actually exists...")
                                try:
                                    acls = self.api.get_acls()
                                    existing_acl = next((a for a in acls if a['name'] == acl_name), None)
                                    if existing_acl:
                                        print(f"    ✓ Found existing ACL with UID: {existing_acl['uid']}")
                                        acl = existing_acl
                                        break
                                    else:
                                        print(f"⚠ ACL '{acl_name}' still exists after deletion. Use --force to recreate.")
                                        return False
                                except requests.RequestException:
                                    print(f"⚠ ACL '{acl_name}' still exists after deletion. Use --force to recreate.")
                                    return False
                        else:
                            raise
            
            # Create or get role
            role_name = f"{agent_name}-role"
            if existing_components and 'role' in existing_components:
                role = existing_components['role']
                print(f"✓ Using existing role: {role_name} (UID: {role['uid']})")
            else:
                print("Creating role...")
                
                # Retry creation with delay if component still exists
                for attempt in range(max_retries):
                    try:
                        role = self.api.create_role(role_name, role_management)
                        print(f"✓ Role created successfully with UID: {role['uid']}")
                        break
                    except requests.RequestException as e:
                        if "409" in str(e) and "Conflict" in str(e):
                            if attempt < max_retries - 1:
                                print(f"    Role still exists, waiting before retry... (attempt {attempt + 1}/{max_retries})")
                                time.sleep(3.0)
                            else:
                                # Final attempt - check if role actually exists and try to get its UID
                                print(f"    Checking if role '{role_name}' actually exists...")
                                try:
                                    roles = self.api.get_roles()
                                    existing_role = next((r for r in roles if r['name'] == role_name), None)
                                    if existing_role:
                                        print(f"    ✓ Found existing role with UID: {existing_role['uid']}")
                                        role = existing_role
                                        break
                                    else:
                                        print(f"⚠ Role '{role_name}' still exists after deletion. Use --force to recreate.")
                                        return False
                                except requests.RequestException:
                                    print(f"⚠ Role '{role_name}' still exists after deletion. Use --force to recreate.")
                                    return False
                        else:
                            raise
            
            # Create or get user (unless skipped)
            if not skip_user_creation:
                if existing_components and 'user' in existing_components:
                    user = existing_components['user']
                    print(f"✓ Using existing user: {agent_name} (UID: {user['uid']})")
                else:
                    print("Creating user...")
                    if agent_email is None:
                        agent_email = f"{agent_name}@example.com"
                    
                    # Retry creation with delay if component still exists
                    for attempt in range(max_retries):
                        try:
                            user = self.api.create_user(agent_email, agent_password, agent_name, [role['uid']])
                            print(f"✓ User created successfully with UID: {user['uid']}")
                            break
                        except requests.RequestException as e:
                            if "409" in str(e) and "Conflict" in str(e):
                                if attempt < max_retries - 1:
                                    print(f"    User still exists, waiting before retry... (attempt {attempt + 1}/{max_retries})")
                                    time.sleep(3.0)
                                else:
                                    # Final attempt - check if user actually exists and try to get its UID
                                    print(f"    Checking if user '{agent_name}' actually exists...")
                                    try:
                                        users = self.api.get_users()
                                        existing_user = next((u for u in users if u['name'] == agent_name), None)
                                        if existing_user:
                                            print(f"    ✓ Found existing user with UID: {existing_user['uid']}")
                                            user = existing_user
                                            break
                                        else:
                                            print(f"⚠ User '{agent_name}' still exists after deletion. Use --force to recreate.")
                                            return False
                                    except requests.RequestException:
                                        print(f"⚠ User '{agent_name}' still exists after deletion. Use --force to recreate.")
                                        return False
                            else:
                                raise
            else:
                print("Skipping user creation (using existing basic auth credentials)")
                user = None
            
            # Update database permissions (unless skipped)
            if not skip_all_databases:
                self.update_database_permissions(role['uid'], acl['uid'], agent_name, database_filter, skip_existing)
            else:
                print("Skipping database permissions (--skip-all-databases flag set)")
            
            print("\n✓ Agent permissions created successfully!")
            print(f"Permissions created for agent '{agent_name}':")
            if not skip_user_creation:
                print(f"  Email: {agent_email}")
                print(f"  Password: {agent_password}")
            else:
                print(f"  Using existing basic auth credentials")
            print(f"  Role: {role_name}")
            print(f"  ACL: {acl_name}")
            
            return True
            
        except requests.RequestException as e:
            print(f"✗ Error creating permissions for agent '{agent_name}': {e}")
            return False
    
    def update_existing_agent(self, agent_name: str, database_filter: str = None, skip_existing: bool = False) -> bool:
        """Update permissions for existing agent"""
        print(f"Updating permissions for agent '{agent_name}'...")
        
        try:
            # Find existing ACL and role
            acls = self.api.get_acls()
            roles = self.api.get_roles()
            
            acl = None
            role = None
            
            for a in acls:
                if a['name'] == f"{agent_name}-acl":
                    acl = a
                    break
            
            for r in roles:
                if r['name'] == f"{agent_name}-role":
                    role = r
                    break
            
            if not acl:
                print(f"✗ Could not find ACL for agent '{agent_name}': {agent_name}-acl")
                return False
            
            if not role:
                print(f"✗ Could not find role for agent '{agent_name}': {agent_name}-role")
                return False
            
            print(f"✓ Found existing permissions for agent '{agent_name}':")
            print(f"  ACL: {agent_name}-acl (UID: {acl['uid']})")
            print(f"  Role: {agent_name}-role (UID: {role['uid']})")
            
            # Update database permissions
            self.update_database_permissions(role['uid'], acl['uid'], agent_name, database_filter, skip_existing)
            
            return True
            
        except requests.RequestException as e:
            print(f"✗ Error updating permissions for agent '{agent_name}': {e}")
            return False
    
    def repair_missing_components(self, agent_name: str, agent_password: str, acl_rules: str = None, role_management: str = "cluster_member", agent_email: str = None, database_filter: str = None, skip_all_databases: bool = False, skip_user_creation: bool = False) -> bool:
        """Repair missing components for an existing agent"""
        print(f"Repairing missing components for agent: {agent_name}")
        
        try:
            # Check for existing components
            existing_components = self.find_existing_agent(agent_name)
            
            if not existing_components:
                print(f"✗ No components found for agent '{agent_name}'. Use create_new_agent instead.")
                return False
            
            # Identify missing components
            missing_components = []
            all_components = ['acl', 'role', 'user']
            for component in all_components:
                if component not in existing_components:
                    missing_components.append(component)
            
            if not missing_components:
                print(f"✓ All components for agent '{agent_name}' already exist. No repair needed.")
                return True
            
            print(f"Missing components: {', '.join(missing_components)}")
            
            # Create missing components using the same logic as create_new_agent
            acl = existing_components.get('acl')
            role = existing_components.get('role')
            user = existing_components.get('user')
            
            # Create missing ACL
            if 'acl' not in existing_components:
                acl_name = f"{agent_name}-acl"
                print("Creating missing ACL...")
                if acl_rules is None:
                    acl_rules = "+@read +info +ping +config|get +client|list +memory +latency"
                
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        acl = self.api.create_acl(acl_name, acl_rules)
                        print(f"✓ ACL created successfully with UID: {acl['uid']}")
                        break
                    except requests.RequestException as e:
                        if "409" in str(e) and "Conflict" in str(e):
                            if attempt < max_retries - 1:
                                print(f"    ACL still exists, waiting before retry... (attempt {attempt + 1}/{max_retries})")
                                time.sleep(3.0)
                            else:
                                print(f"⚠ ACL '{acl_name}' still exists. Skipping creation.")
                                break
                        else:
                            raise
            else:
                print(f"✓ Using existing ACL: {agent_name}-acl (UID: {acl['uid']})")
            
            # Create missing role
            if 'role' not in existing_components:
                role_name = f"{agent_name}-role"
                print("Creating missing role...")
                
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        role = self.api.create_role(role_name, role_management)
                        print(f"✓ Role created successfully with UID: {role['uid']}")
                        break
                    except requests.RequestException as e:
                        if "409" in str(e) and "Conflict" in str(e):
                            if attempt < max_retries - 1:
                                print(f"    Role still exists, waiting before retry... (attempt {attempt + 1}/{max_retries})")
                                time.sleep(3.0)
                            else:
                                print(f"⚠ Role '{role_name}' still exists. Skipping creation.")
                                break
                        else:
                            raise
            else:
                print(f"✓ Using existing role: {agent_name}-role (UID: {role['uid']})")
            
            # Create missing user
            if 'user' not in existing_components and not skip_user_creation:
                print("Creating missing user...")
                if agent_email is None:
                    agent_email = f"{agent_name}@example.com"
                
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        user = self.api.create_user(agent_email, agent_password, agent_name, [role['uid']])
                        print(f"✓ User created successfully with UID: {user['uid']}")
                        break
                    except requests.RequestException as e:
                        if "409" in str(e) and "Conflict" in str(e):
                            if attempt < max_retries - 1:
                                print(f"    User still exists, waiting before retry... (attempt {attempt + 1}/{max_retries})")
                                time.sleep(3.0)
                            else:
                                print(f"⚠ User '{agent_name}' still exists. Skipping creation.")
                                break
                        else:
                            raise
            elif 'user' in existing_components:
                print(f"✓ Using existing user: {agent_name} (UID: {user['uid']})")
            else:
                print("Skipping user creation (using existing basic auth credentials)")
                user = None
            
            # Update database permissions if we have both ACL and role
            if acl and role and not skip_all_databases:
                self.update_database_permissions(role['uid'], acl['uid'], agent_name, database_filter, False)
            else:
                print("Skipping database permissions (missing ACL/role or --skip-all-databases flag set)")
            
            print("\n✓ Agent component repair completed successfully!")
            return True
            
        except requests.RequestException as e:
            print(f"✗ Error repairing components for agent '{agent_name}': {e}")
            return False
    
    def cleanup_database_permissions(self, role_uid: int, acl_uid: int, agent_name: str, database_filter: str = None) -> bool:
        """Remove permissions for a specific role/ACL combination from all databases"""
        print("Cleaning up database permissions...")
        
        try:
            databases = self.api.get_databases()
            
            if not databases:
                print("✗ No databases found")
                return False
            
            # Filter databases if filter is provided
            if database_filter:
                try:
                    pattern = re.compile(database_filter)
                    filtered_databases = [db for db in databases if pattern.search(db['name'])]
                    print(f"Filtering databases with pattern '{database_filter}': {len(filtered_databases)}/{len(databases)} databases match")
                    databases = filtered_databases
                except re.error as e:
                    print(f"✗ Invalid regex pattern '{database_filter}': {e}")
                    return False
            
            success_count = 0
            total_count = 0
            
            for db in databases:
                db_uid = db['uid']
                db_name = db['name']
                current_permissions = db.get('roles_permissions', [])
                
                # Remove permissions that match the role_uid and acl_uid
                updated_permissions = [
                    perm for perm in current_permissions 
                    if not (perm.get('role_uid') == role_uid and perm.get('redis_acl_uid') == acl_uid)
                ]
                
                if len(updated_permissions) < len(current_permissions):
                    # Permissions were removed, update the database
                    if self.api.update_database_permissions(db_uid, updated_permissions):
                        removed_count = len(current_permissions) - len(updated_permissions)
                        print(f"  ✓ {db_name}: Removed {removed_count} permission(s)")
                        success_count += 1
                    else:
                        print(f"  ✗ {db_name}: Failed to remove permissions")
                else:
                    print(f"  - {db_name}: No matching permissions to remove")
                    success_count += 1
                
                total_count += 1
            
            print(f"\n✓ Database permissions cleanup completed: {success_count}/{total_count} databases")
            return True
            
        except requests.RequestException as e:
            print(f"✗ Error cleaning up database permissions: {e}")
            return False

    def update_database_permissions(self, role_uid: int, acl_uid: int, agent_name: str, database_filter: str = None, skip_existing: bool = False) -> bool:
        """Update database permissions for all databases"""
        print("Updating database permissions...")
        
        try:
            databases = self.api.get_databases()
            
            if not databases:
                print("✗ No databases found")
                return False
            
            # Filter databases if filter is provided
            if database_filter:
                try:
                    pattern = re.compile(database_filter)
                    filtered_databases = [db for db in databases if pattern.search(db['name'])]
                    print(f"Filtering databases with pattern '{database_filter}': {len(filtered_databases)}/{len(databases)} databases match")
                    databases = filtered_databases
                except re.error as e:
                    print(f"✗ Invalid regex pattern '{database_filter}': {e}")
                    return False
            
            success_count = 0
            total_count = 0
            
            for db in databases:
                db_uid = db['uid']
                db_name = db['name']
                current_permissions = db.get('roles_permissions', [])
                
                # Check if permission already exists
                permission_exists = any(
                    perm.get('role_uid') == role_uid and perm.get('redis_acl_uid') == acl_uid
                    for perm in current_permissions
                )
                
                if permission_exists:
                    if skip_existing:
                        print(f"  - {db_name}: Already has permission (skipping)")
                        success_count += 1
                    else:
                        print(f"  - {db_name}: Already has permission (skipping)")
                        success_count += 1
                else:
                    # Add new permission
                    new_permission = {"role_uid": role_uid, "redis_acl_uid": acl_uid}
                    updated_permissions = current_permissions + [new_permission]
                    
                    print(f"    Debug: Adding permission role_uid={role_uid}, acl_uid={acl_uid}")
                    print(f"    Debug: Current permissions count: {len(current_permissions)}, Updated permissions count: {len(updated_permissions)}")
                    
                    if self.api.update_database_permissions(db_uid, updated_permissions):
                        print(f"  ✓ {db_name}: Permission {'set' if not current_permissions else 'augmented'}")
                        success_count += 1
                    else:
                        print(f"  ✗ {db_name}: Failed to update permissions")
                
                total_count += 1
            
            print(f"\n✓ Database permissions updated: {success_count}/{total_count} databases")
            return True
            
        except requests.RequestException as e:
            print(f"✗ Error updating database permissions: {e}")
            return False


def prompt_with_default(prompt: str, default: str = "") -> str:
    """Prompt user for input with optional default value"""
    try:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            return user_input if user_input else default
        else:
            return input(f"{prompt}: ").strip()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user (Ctrl+C)")
        sys.exit(0)


def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def validate_host(host: str) -> bool:
    """Validate host format - should not contain http://, https://, ://, or :port"""
    invalid_patterns = ['http://', 'https://', '://', ':']
    for pattern in invalid_patterns:
        if pattern in host:
            return False
    return True


def parse_agent_config(config_path: str) -> List[Dict]:
    """
    Parse agent YAML config and extract ENTERPRISE deployments.
    
    This function supports environment variable interpolation using the ${ENV_VAR} syntax.
    For example, in your YAML config:
    
    deployment:
      - id: "my-cluster"
        name: "test"
        type: "ENTERPRISE"
        rest_api:
          host: "localhost"
          port: 1943
        credentials:
          enterprise_api:
            basic_auth: "${ADMIN_USER}:${ADMIN_PASSWORD}"
    
    The ${ADMIN_USER} and ${ADMIN_PASSWORD} will be replaced with the actual
    environment variable values. If an environment variable is not set, a warning
    will be printed and the original ${ENV_VAR} pattern will be preserved.
    
    The script expects the new structure with credentials.enterprise_api.basic_auth.
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"✗ Config file not found: {config_path}")
        return []
    except yaml.YAMLError as e:
        print(f"✗ Error parsing YAML config: {e}")
        return []
    
    # Interpolate environment variables in the config
    config = interpolate_env_vars(config)
    
    enterprise_deployments = []
    
    if 'deployment' not in config:
        print("⚠ No 'deployment' section found in config")
        return enterprise_deployments
    
    for deployment in config['deployment']:
        if deployment.get('type') == 'ENTERPRISE':
            enterprise_deployments.append(deployment)
    
    return enterprise_deployments


def extract_rest_api_details(deployment: Dict) -> Optional[Dict]:
    """Extract REST API details from an ENTERPRISE deployment"""
    rest_api = deployment.get('rest_api', {})
    
    # If rest_api section has explicit host and port, use those
    if 'host' in rest_api and 'port' in rest_api:
        host = rest_api['host']
        port = rest_api['port']
        
        # Validate host format
        if not validate_host(host):
            print(f"✗ Invalid host format in deployment {deployment.get('id', 'unknown')}: '{host}'")
            print(f"  Host should not contain http://, https://, ://, or :port")
            return None
        
        endpoint = f"https://{host}:{port}"
    else:
        # Derive from redis_url by removing redis-<PORT>. subdomain and replacing port with 9443
        redis_urls = deployment.get('redis_urls', [])
        if not redis_urls:
            print(f"⚠ No redis_urls found for deployment {deployment.get('id', 'unknown')}")
            return None
        
        # Handle both string and list formats for redis_urls
        if isinstance(redis_urls, str):
            redis_urls = [redis_urls]
        
        # Use the first redis_url for endpoint derivation
        redis_url = redis_urls[0]
        try:
            parsed = urlparse(redis_url)
            # Remove redis-<PORT>. subdomain from hostname
            hostname = parsed.hostname
            if hostname and 'redis-' in hostname:
                # Extract the base hostname by removing redis-<PORT>. prefix
                parts = hostname.split('.')
                if len(parts) > 1 and parts[0].startswith('redis-'):
                    # Remove the redis-<PORT> part
                    hostname = '.'.join(parts[1:])
            
            # Use port from rest_api if available, otherwise default to 9443
            port = rest_api.get('port', 9443)
            endpoint = f"https://{hostname}:{port}"
        except Exception as e:
            print(f"⚠ Error parsing redis_url '{redis_url}': {e}")
            return None
    
    # Extract basic auth from credentials.enterprise_api.basic_auth
    credentials = deployment.get('credentials', {})
    enterprise_api = credentials.get('enterprise_api', {})
    basic_auth = enterprise_api.get('basic_auth')
    
    if basic_auth:
        try:
            username, password = basic_auth.split(':', 1)
        except ValueError:
            print(f"⚠ Invalid basic_auth format in deployment {deployment.get('id', 'unknown')}")
            return None
    else:
        username = None
        password = None
    
    return {
        'deployment_id': deployment.get('id'),
        'deployment_name': deployment.get('name'),
        'endpoint': endpoint,
        'username': username,
        'password': password
    }


def provision_single_cluster(endpoint: str, username: str, password: str, agent_name: str, agent_password: str, 
                           acl_rules: str, role_management: str, agent_email: str, database_filter: str, 
                           skip_existing: bool, force: bool, skip_all_databases: bool, verify_ssl: bool, 
                           skip_user_creation: bool = False) -> bool:
    """Provision a single Redis Enterprise cluster"""
    print(f"\n{'='*60}")
    print(f"Provisioning cluster: {endpoint}")
    print(f"{'='*60}")
    
    # Initialize API client
    try:
        skip_ssl_verify = not verify_ssl
        api = RedisEnterpriseAPI(endpoint, username, password, skip_ssl_verify)
    except Exception as e:
        print(f"✗ Error initializing API client: {e}")
        return False
    
    # Test connectivity
    print("Testing API connectivity...")
    if not api.test_connectivity():
        print("✗ API connectivity test failed")
        return False
    print("✓ API connectivity test passed")
    
    # Initialize agent manager
    manager = AgentManager(api)
    
    # Check if agent permissions exist
    existing_agent = manager.find_existing_agent(agent_name)
    
    if existing_agent and not force:
        print(f"\n⚠ Permissions for agent '{agent_name}' already exist!")
        print(f"Found existing components: {', '.join(existing_agent.keys())}")
        print("Use --force to recreate existing components or --update to update existing permissions.")
        return False
    
    # Create new agent
    success = manager.create_new_agent(agent_name, agent_password, acl_rules, role_management, 
                                     agent_email, database_filter, skip_existing, force, skip_all_databases, skip_user_creation)
    
    if success:
        print(f"\n✓ Cluster {endpoint} provisioned successfully!")
    else:
        print(f"\n✗ Failed to provision cluster {endpoint}")
    
    return success


def handle_single_cluster_interactive(args, last_values: Dict) -> bool:
    """Handle single cluster interactive mode"""
    # Get connection details
    if args.endpoint:
        endpoint = args.endpoint
    else:
        endpoint = prompt_with_default("Enter Redis Enterprise REST API endpoint", last_values.get("endpoint", "https://localhost:9443"))
    
    if not validate_url(endpoint):
        print("✗ Invalid URL format. Please include protocol (http:// or https://)")
        return False
    
    if args.username:
        username = args.username
    elif os.getenv("AGENT_USER"):
        username = os.getenv("AGENT_USER")
    else:
        username = prompt_with_default("Enter admin username for provisioning", last_values.get("username", "admin@example.com"))
    
    if args.password:
        password = args.password
    elif os.getenv("ADMIN_PWD"):
        password = os.getenv("ADMIN_PWD")
    else:
        password = prompt_with_default("Enter admin password for provisioning")
    
    # Initialize API client
    try:
        # If verify_ssl is True, then skip_ssl_verify should be False
        skip_ssl_verify = not args.verify_ssl
        api = RedisEnterpriseAPI(endpoint, username, password, skip_ssl_verify)
    except Exception as e:
        print(f"✗ Error initializing API client: {e}")
        return False
    
    # Test connectivity
    print("Testing API connectivity...")
    if not api.test_connectivity():
        print("✗ API connectivity test failed")
        return False
    print("✓ API connectivity test passed")
    
    # Get agent name
    if args.agent_name:
        agent_name = args.agent_name
    elif os.getenv("AGENT_NAME"):
        agent_name = os.getenv("AGENT_NAME")
    else:
        agent_name = prompt_with_default("Enter agent name for permissions", last_values.get("agent_name", "radar-agent"))
    
    # Get agent password
    if hasattr(args, 'agent_password') and args.agent_password:
        agent_password = args.agent_password
    elif os.getenv("AGENT_PASSWORD"):
        agent_password = os.getenv("AGENT_PASSWORD")
    elif os.getenv("AGENT_PWD"):
        agent_password = os.getenv("AGENT_PWD")
    else:
        agent_password = prompt_with_default("Enter agent password")
    
    # Get agent email (user)
    if args.agent_email:
        agent_email = args.agent_email
    elif os.getenv("AGENT_USER"):
        agent_email = os.getenv("AGENT_USER")
    else:
        # Prompt for agent email/username in interactive mode
        default_email = f"{agent_name}@example.com"
        agent_email = prompt_with_default("Enter agent email/username", last_values.get("agent_email", default_email))
    
    # Initialize agent manager
    manager = AgentManager(api)
    
    # Check if agent permissions exist
    existing_agent = manager.find_existing_agent(agent_name)
    
    if existing_agent and not (args.create and args.force):
        print(f"\n⚠ Permissions for agent '{agent_name}' already exist!")
        print(f"Found existing components: {', '.join(existing_agent.keys())}")
        
        if args.update:
            # Force update mode
            success = manager.update_existing_agent(agent_name, args.database_filter, args.skip_existing)
        elif args.repair:
            # Force repair mode - skip interactive prompt
            success = manager.repair_missing_components(agent_name, agent_password, args.acl_rules, args.role_management, agent_email, args.database_filter, args.skip_all_databases, False)
        elif args.create and args.force:
            # Force create mode - skip interactive prompt
            success = manager.create_new_agent(agent_name, agent_password, args.acl_rules, args.role_management, agent_email, args.database_filter, args.skip_existing, args.force, args.skip_all_databases, False)
        else:
            # Interactive mode
            print("\nWhat would you like to do?")
            print("1) Update permissions for existing agent")
            print("2) Create permissions for a new agent with a different name")
            print("3) Repair missing components (create only missing ACL, role, user)")
            print("4) Force recreate existing components (delete and recreate ACL, role, user)")
            print("5) Exit")
            
            while True:
                try:
                    choice = input("\nEnter your choice (1-5): ").strip()
                    if choice == "1":
                        success = manager.update_existing_agent(agent_name, args.database_filter, args.skip_existing)
                        break
                    elif choice == "2":
                        new_name = prompt_with_default("Enter new agent name", f"{agent_name}-new")
                        new_password = prompt_with_default("Enter agent password")
                        new_email = prompt_with_default("Enter agent email/username", f"{new_name}@example.com")
                        success = manager.create_new_agent(new_name, new_password, args.acl_rules, args.role_management, new_email, args.database_filter, args.skip_existing, False, args.skip_all_databases, False)
                        break
                    elif choice == "3":
                        success = manager.repair_missing_components(agent_name, agent_password, args.acl_rules, args.role_management, agent_email, args.database_filter, args.skip_all_databases, False)
                        break
                    elif choice == "4":
                        success = manager.create_new_agent(agent_name, agent_password, args.acl_rules, args.role_management, agent_email, args.database_filter, args.skip_existing, True, args.skip_all_databases, False)
                        break
                    elif choice == "5":
                        print("Operation cancelled by user")
                        return False
                    else:
                        print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")
                except KeyboardInterrupt:
                    print("\n\nOperation cancelled by user (Ctrl+C)")
                    return False
    else:
        # Agent permissions don't exist or force create mode
        print(f"\nPermissions for agent '{agent_name}' do not exist. Creating new permissions...")
        success = manager.create_new_agent(agent_name, agent_password, args.acl_rules, args.role_management, agent_email, args.database_filter, args.skip_existing, args.force, args.skip_all_databases, False)
    
    if success:
        print("\n" + "=" * 50)
        print("✓ Agent permissions management completed successfully!")
        
        # Store values for next iteration
        last_values.update({
            "endpoint": endpoint,
            "username": username,
            "agent_name": agent_name,
            "agent_email": agent_email
        })
    
    return success


def handle_multi_cluster_interactive(args, last_values: Dict) -> bool:
    """Handle multi-cluster interactive mode"""
    # Get YAML config path
    config_path = prompt_with_default("Enter path to agent YAML config file", last_values.get("config_path", ""))
    if not config_path:
        print("✗ Config file path is required")
        return False
    
    # Get agent details
    if args.agent_name:
        agent_name = args.agent_name
    elif os.getenv("AGENT_NAME"):
        agent_name = os.getenv("AGENT_NAME")
    else:
        agent_name = prompt_with_default("Enter agent name for permissions", last_values.get("agent_name", "radar-agent"))
    
    # Get agent email (user)
    if args.agent_email:
        agent_email = args.agent_email
    elif os.getenv("AGENT_USER"):
        agent_email = os.getenv("AGENT_USER")
    else:
        # Prompt for agent email/username in interactive mode
        default_email = f"{agent_name}@example.com"
        agent_email = prompt_with_default("Enter agent email/username", last_values.get("agent_email", default_email))
    
    # Provision from YAML config
    success = provision_from_yaml_config(
        config_path, agent_name, args.acl_rules, args.role_management, agent_email,
        args.database_filter, args.skip_existing, args.force, args.skip_all_databases, args.verify_ssl
    )
    
    if success:
        print("\n" + "=" * 50)
        print("✓ Multi-cluster provisioning completed successfully!")
        
        # Store values for next iteration
        last_values.update({
            "config_path": config_path,
            "agent_name": agent_name,
            "agent_email": agent_email
        })
    
    return success


def provision_from_yaml_config(config_path: str, agent_name: str, acl_rules: str, 
                              role_management: str, agent_email: str, 
                              database_filter: str, skip_existing: bool, force: bool, 
                              skip_all_databases: bool, verify_ssl: bool) -> bool:
    """Provision multiple clusters from YAML config"""
    print("=" * 50)
    print("Redis Enterprise Multi-Cluster Provisioning")
    print("=" * 50)
    
    # Parse config and extract enterprise deployments
    enterprise_deployments = parse_agent_config(config_path)
    if not enterprise_deployments:
        print("✗ No ENTERPRISE deployments found in config")
        return False
    
    print(f"Found {len(enterprise_deployments)} ENTERPRISE deployment(s):")
    for deployment in enterprise_deployments:
        print(f"  - {deployment.get('name', deployment.get('id', 'unknown'))}")
    
    print("\nExtracting REST API details...")
    # Extract REST API details for each deployment
    cluster_configs = []
    for deployment in enterprise_deployments:
        print(f"\nProcessing deployment: {deployment.get('name', deployment.get('id', 'unknown'))}")
        details = extract_rest_api_details(deployment)
        if details:
            cluster_configs.append(details)
            print(f"  ✓ Endpoint: {details['endpoint']}")
            if details['username']:
                print(f"  ✓ Username: {details['username']}")
            else:
                print(f"  ⚠ Username: Will prompt during provisioning")
        else:
            print(f"  ✗ Skipping - could not extract REST API details")
    
    if not cluster_configs:
        print("✗ No valid cluster configurations found")
        return False
    
    print(f"\nReady to provision {len(cluster_configs)} cluster(s)")
    
    # Provision each cluster
    success_count = 0
    total_count = len(cluster_configs)
    
    for i, config in enumerate(cluster_configs, 1):
        print(f"\n{'='*60}")
        print(f"Cluster {i}/{total_count}: {config['deployment_name']}")
        print(f"{'='*60}")
        
        # Use config values or prompt for missing ones
        endpoint = config['endpoint']
        username = config['username'] or prompt_with_default(f"Enter admin username for provisioning {config['deployment_name']}", "admin@example.com")
        password = config['password'] or prompt_with_default(f"Enter admin password for provisioning {config['deployment_name']}")
        
        # Determine agent credentials based on basic auth presence
        if config['username'] and config['password']:
            # Use basic auth credentials as agent credentials, skip user creation
            agent_username = config['username']
            agent_password = config['password']
            skip_user_creation = True
            print(f"Using basic auth credentials for agent: {agent_username}")
        else:
            # Use provided agent credentials and create user
            # Determine agent name if not provided
            if not agent_name:
                if hasattr(args, 'agent_name') and args.agent_name:
                    agent_name = args.agent_name
                elif os.getenv("AGENT_NAME"):
                    agent_name = os.getenv("AGENT_NAME")
                else:
                    agent_name = prompt_with_default("Enter agent name for permissions", "radar-agent")
            
            # Use agent_name for both the username and the permissions
            agent_username = agent_name
            agent_password = prompt_with_default(f"Enter agent password for {config['deployment_name']}")
            skip_user_creation = False
            print(f"Will create new user: {agent_username}")
            
            # Provide notice about adding basic auth to config
            print(f"\n⚠️  NOTICE: No basic_auth found in config for deployment '{config['deployment_name']}'")
            print("   To avoid password prompts in future runs, add basic_auth to your YAML config:")
            print(f"   deployment:")
            print(f"     - id: \"{config['deployment_id']}\"")
            print(f"       name: \"{config['deployment_name']}\"")
            print(f"       type: \"ENTERPRISE\"")
            print(f"       auto_discover: true")
            print(f"       rest_api:")
            print(f"         host: \"{config['endpoint'].replace('https://', '').split(':')[0]}\"")
            print(f"         port: {config['endpoint'].split(':')[-1]}")
            print(f"       credentials:")
            print(f"         enterprise_api:")
            print(f"           basic_auth: \"{agent_username}:{agent_password}\"")
            print()
        
        # Always use the agent_name for creating ACL and role names, regardless of basic_auth presence
        agent_name_for_permissions = agent_name if agent_name else agent_username
        
        success = provision_single_cluster(
            endpoint, username, password, agent_name_for_permissions, agent_password,
            acl_rules, role_management, agent_email, database_filter,
            skip_existing, force, skip_all_databases, verify_ssl, skip_user_creation
        )
        
        if success:
            success_count += 1
    
    print(f"\n{'='*60}")
    print(f"Multi-cluster provisioning completed: {success_count}/{total_count} clusters successful")
    print(f"{'='*60}")
    
    return success_count == total_count


def main():
    parser = argparse.ArgumentParser(
        description="Redis Enterprise Agent Permissions Manager - Create and manage permissions for monitoring agents",
        epilog="""
EXAMPLES:
  # Interactive mode - choose between single and multi-cluster provisioning
  python3 enterprise_credentials.py

  # Create permissions for new agent with command line arguments
  python3 enterprise_credentials.py --endpoint https://localhost:9443 \\
    --username admin@re.demo --password redis123 \\
    --agent-name my-agent --agent-password mypass --create

  # Provision multiple clusters from agent YAML config
  python3 enterprise_credentials.py --agent-yaml-config agent-config.yaml \\
    --agent-name radar-agent --agent-password radar123 --create

  # Provision with environment variables in YAML config
  # Set environment variables: export ADMIN_USER=admin@re.demo ADMIN_PASSWORD=redis123
  # YAML config with: credentials.enterprise_api.basic_auth: "${ADMIN_USER}:${ADMIN_PASSWORD}"
  python3 enterprise_credentials.py --agent-yaml-config agent-config.yaml \\
    --agent-name radar-agent --create

  # Update permissions for existing agent
  python3 enterprise_credentials.py --agent-name radar-agent --update

  # Repair missing components for existing agent
  python3 enterprise_credentials.py --agent-name radar-agent --repair

  # Create permissions with custom ACL rules
  python3 enterprise_credentials.py --agent-name monitoring-agent \\
    --acl-rules "+@read +info +ping +config|get +client|list +memory +latency +slowlog" \\
    --create

  # Force recreation of existing components (skips interactive prompt)
  python3 enterprise_credentials.py --agent-name radar-agent \\
    --create --force

  # Update only production databases
  python3 enterprise_credentials.py --agent-name radar-agent \\
    --update --database-filter "prod-.*" --skip-existing

  # Production environment with SSL verification enabled
  python3 enterprise_credentials.py --endpoint https://redis.company.com:9443 \\
    --verify-ssl --agent-name prod-agent --create

  # Skip database permissions (only create ACL, role, user)
  python3 enterprise_credentials.py --agent-name radar-agent \\
    --create --skip-all-databases
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Connection arguments
    connection_group = parser.add_argument_group('Connection Options')
    connection_group.add_argument("--endpoint", 
                                 help="Redis Enterprise REST API endpoint (e.g., https://localhost:9443)")
    connection_group.add_argument("--username", 
                                 help="Admin username (e.g., admin@re.demo)")
    connection_group.add_argument("--password", 
                                 help="Admin password")
    connection_group.add_argument("--verify-ssl", action="store_true", 
                                 help="Enable SSL certificate verification (default: SSL verification disabled)")
    
    # Agent arguments
    agent_group = parser.add_argument_group('Agent Options')
    agent_group.add_argument("--agent-yaml-config", 
                            help="Path to agent YAML config file (will provision for all ENTERPRISE deployments)")
    agent_group.add_argument("--agent-name", 
                            help="Agent name (will create agent-name-acl and agent-name-role permissions)")
    agent_group.add_argument("--agent-password", 
                            help="Agent password (will prompt if not provided)")
    agent_group.add_argument("--agent-email", 
                            help="Agent email (default: agent-name@example.com)")
    
    # ACL arguments
    acl_group = parser.add_argument_group('ACL Options')
    acl_group.add_argument("--acl-rules", 
                          default="+@read +info +ping +config|get +client|list +memory +latency",
                          help="ACL rules for the agent (default: monitoring permissions)")
    
    # Role arguments
    role_group = parser.add_argument_group('Role Options')
    role_group.add_argument("--role-management", 
                           default="cluster_member",
                           choices=["admin", "cluster_member", "db_member", "none"],
                           help="Role management level (default: cluster_member)")
    
    # Action arguments
    action_group = parser.add_argument_group('Action Options')
    action_group.add_argument("--create", action="store_true", 
                             help="Force create new agent permissions (skip interactive prompts)")
    action_group.add_argument("--update", action="store_true", 
                             help="Force update existing agent permissions")
    action_group.add_argument("--repair", action="store_true", 
                             help="Repair missing components for existing agent (create only missing ACL, role, user)")
    action_group.add_argument("--force", action="store_true", 
                             help="Force recreation of existing components (ACL, role, user)")
    
    # Database arguments
    db_group = parser.add_argument_group('Database Options')
    db_group.add_argument("--database-filter", 
                         help="Only update databases matching this pattern (regex)")
    db_group.add_argument("--skip-existing", action="store_true", 
                         help="Skip databases that already have the permission")
    db_group.add_argument("--skip-all-databases", action="store_true", 
                         help="Skip applying permissions to all databases (only create ACL, role, user)")
    
    args = parser.parse_args()
    
    # Check if we're in YAML config mode
    if args.agent_yaml_config:
        # Multi-cluster mode from YAML config
        if args.agent_name:
            agent_name = args.agent_name
        elif os.getenv("AGENT_NAME"):
            agent_name = os.getenv("AGENT_NAME")
        else:
            agent_name = prompt_with_default("Enter agent name for permissions", "radar-agent")
        
        success = provision_from_yaml_config(
            args.agent_yaml_config, agent_name, args.acl_rules,
            args.role_management, args.agent_email,
            args.database_filter, args.skip_existing, args.force,
            args.skip_all_databases, args.verify_ssl
        )
        
        if success:
            print("\n" + "=" * 50)
            print("✓ Multi-cluster provisioning completed successfully!")
        else:
            print("\n" + "=" * 50)
            print("✗ Multi-cluster provisioning failed!")
            sys.exit(1)
        return
    
    # Check if we're in non-interactive mode (create, update, or repair)
    if args.create or args.update or args.repair:
        # Non-interactive mode - require endpoint and credentials
        if not args.endpoint:
            print("✗ --endpoint is required for non-interactive mode")
            sys.exit(1)
        
        if not args.username:
            print("✗ --username is required for non-interactive mode")
            sys.exit(1)
        
        if not args.password:
            print("✗ --password is required for non-interactive mode")
            sys.exit(1)
        
        if not args.agent_name:
            print("✗ --agent-name is required for non-interactive mode")
            sys.exit(1)
        
        # Get agent password if not provided
        agent_password = args.agent_password
        if not agent_password:
            if os.getenv("AGENT_PASSWORD"):
                agent_password = os.getenv("AGENT_PASSWORD")
            elif os.getenv("AGENT_PWD"):
                agent_password = os.getenv("AGENT_PWD")
            else:
                agent_password = prompt_with_default("Enter agent password")
        
        # Get agent email if not provided
        agent_email = args.agent_email
        if not agent_email:
            if os.getenv("AGENT_USER"):
                agent_email = os.getenv("AGENT_USER")
            else:
                agent_email = f"{args.agent_name}@example.com"
        
        # Initialize API client
        try:
            skip_ssl_verify = not args.verify_ssl
            api = RedisEnterpriseAPI(args.endpoint, args.username, args.password, skip_ssl_verify)
        except Exception as e:
            print(f"✗ Error initializing API client: {e}")
            sys.exit(1)
        
        # Test connectivity
        print("Testing API connectivity...")
        if not api.test_connectivity():
            print("✗ API connectivity test failed")
            sys.exit(1)
        print("✓ API connectivity test passed")
        
        # Initialize agent manager
        manager = AgentManager(api)
        
        # Execute the requested action
        if args.repair:
            success = manager.repair_missing_components(
                args.agent_name, agent_password, args.acl_rules, args.role_management,
                agent_email, args.database_filter, args.skip_all_databases, False
            )
        elif args.update:
            success = manager.update_existing_agent(
                args.agent_name, args.database_filter, args.skip_existing
            )
        elif args.create:
            success = manager.create_new_agent(
                args.agent_name, agent_password, args.acl_rules, args.role_management,
                agent_email, args.database_filter, args.skip_existing, args.force,
                args.skip_all_databases, False
            )
        
        if success:
            print("\n" + "=" * 50)
            print("✓ Agent permissions management completed successfully!")
        else:
            print("\n" + "=" * 50)
            print("✗ Agent permissions management failed!")
            sys.exit(1)
        return
    
    # Interactive mode - choose between single and multi-cluster
    last_values = {}  # Store values for interactive loop
    
    while True:
        print("=" * 50)
        print("Redis Enterprise Agent Permissions Manager")
        print("=" * 50)
        print()
        
        # Choose provisioning mode
        print("Choose provisioning mode:")
        print("1) Single cluster at a time (manual entry)")
        print("2) Multiple clusters at once(from YAML config)")
        print("3) Exit")
        
        while True:
            try:
                mode_choice = input("\nEnter your choice (1-3): ").strip()
                if mode_choice == "1":
                    # Single cluster mode
                    success = handle_single_cluster_interactive(args, last_values)
                    break
                elif mode_choice == "2":
                    # Multi-cluster mode
                    success = handle_multi_cluster_interactive(args, last_values)
                    break
                elif mode_choice == "3":
                    print("Operation cancelled by user")
                    sys.exit(0)
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
            except KeyboardInterrupt:
                print("\n\nOperation cancelled by user (Ctrl+C)")
                sys.exit(0)
        
        if not success:
            print("\n" + "=" * 50)
            print("✗ Agent permissions management failed!")
            sys.exit(1)
        
        # Ask if user wants to provision another cluster
        try:
            again = input("\nWould you like to provision another cluster? (y/n): ").strip().lower()
            if again != 'y':
                break
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user (Ctrl+C)")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1) 