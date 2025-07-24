from google_auth_oauthlib.flow import InstalledAppFlow

# The scope for uploading to YouTube (must be exactly this for upload permissions)
SCOPES = ["https://www.googleapis.com/auth/youtube"]
# Start the OAuth flow
flow = InstalledAppFlow.from_client_secrets_file(
    'gadaffi.json', SCOPES)
creds = flow.run_local_server(port=0)


# Print your refresh token
print('\nYour refresh_token is:', creds.refresh_token)
print('\nCopy this value and add it to your credentials JSON for use in the app.') 