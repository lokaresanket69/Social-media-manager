#!/usr/bin/env python3
"""
Test script for simplified YouTube authentication
Usage: python test_youtube_simple.py path/to/credentials.json "Channel Name"
"""

import sys
import os
from youtube_auth_simple import create_youtube_account_from_json_simple

def main():
    credentials_file = 'firoz.json'
    account_name = 'Firoz Channel'

    if not os.path.exists(credentials_file):
        print(f"Error: Credentials file '{credentials_file}' not found")
        return

    try:
        print(f"Processing YouTube credentials from: {credentials_file}")
        print(f"Account name: {account_name}")
        print("-" * 50)
        result = create_youtube_account_from_json_simple(credentials_file, account_name)
        print("✅ SUCCESS!")
        print(f"Channel name: {result['channel_info']['name']}")
        print(f"Channel ID: {result['channel_info']['id']}")
        print(f"Account name: {result['name']}")
        print(f"Credentials encrypted and ready for use!")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    main() 