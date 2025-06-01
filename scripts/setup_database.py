#!/usr/bin/env python3
"""
Database setup script for Athena Digital Executive Assistant.
"""

import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.settings import get_settings
from supabase import create_client

def read_sql_file(filename):
    """Read SQL commands from a file."""
    sql_path = Path(__file__).parent.parent / "database" / filename
    if not sql_path.exists():
        print(f"❌ SQL file not found: {sql_path}")
        return None
    
    with open(sql_path, 'r') as f:
        return f.read()

def execute_sql_commands(supabase, sql_content):
    """Execute SQL commands using Supabase."""
    if not sql_content:
        return False
    
    # Split by semicolon and execute each command
    commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
    
    for i, command in enumerate(commands):
        if command.lower().startswith('select'):
            # Skip SELECT statements in setup
            continue
            
        try:
            print(f"Executing command {i+1}/{len(commands)}...")
            # Use rpc for DDL commands
            result = supabase.rpc('exec_sql', {'sql': command}).execute()
            print(f"✅ Command {i+1} executed successfully")
        except Exception as e:
            print(f"⚠️  Command {i+1} failed: {e}")
            # Continue with other commands
    
    return True

def check_table_structure(supabase):
    """Check if tables have the required structure."""
    try:
        # Try to query contacts table
        result = supabase.table("contacts").select("*").limit(1).execute()
        print("✅ Contacts table is accessible")
        
        # Try to query messages table  
        result = supabase.table("messages").select("*").limit(1).execute()
        print("✅ Messages table is accessible")
        
        return True
    except Exception as e:
        print(f"❌ Table structure check failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up Athena database schema...")
    
    try:
        # Get settings
        settings = get_settings()
        
        # Create Supabase client
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key or settings.supabase_anon_key
        )
        
        print(f"📡 Connected to Supabase: {settings.supabase_url}")
        
        # Option 1: Try to fix existing schema
        print("\n🔧 Applying schema fixes...")
        fix_sql = read_sql_file("fix_schema.sql")
        if fix_sql:
            execute_sql_commands(supabase, fix_sql)
        
        # Check if tables work now
        print("\n🔍 Checking table structure...")
        if check_table_structure(supabase):
            print("\n✅ Database setup completed successfully!")
            print("\n📋 What to do next:")
            print("1. Deploy your updated code to Render")
            print("2. Test your bot by sending '/start' on Telegram")
            print("3. Check Render logs for successful message processing")
        else:
            print("\n❌ Tables still have issues. You may need to:")
            print("1. Run the SQL commands manually in Supabase dashboard")
            print("2. Check database permissions")
            print("3. Verify your Supabase service role key")
            
            print(f"\n📄 Manual SQL to run in Supabase:")
            print("Go to: https://app.supabase.com/project/[your-project]/sql")
            print("And run the contents of: database/fix_schema.sql")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print("\n🛠️  Manual fix required:")
        print("1. Go to your Supabase dashboard")
        print("2. Navigate to SQL Editor")
        print("3. Run the SQL commands from database/fix_schema.sql")
        return False

if __name__ == "__main__":
    main() 