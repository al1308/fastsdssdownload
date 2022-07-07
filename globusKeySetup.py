import globus_sdk
import os
import sys
import json

def getProperties():
    # Properties are retrieved from the properties.json file and are assigned to the corresponding variables
    with open(os.path.join(sys.path[0], "properties.json"), 'r') as f:
        data = json.load(f)

    return (data['globus-credentials']['client-id'])

CLIENT_ID = getProperties()

client = globus_sdk.NativeAppAuthClient(CLIENT_ID)
client.oauth2_start_flow(refresh_tokens = True)

authorize_url = client.oauth2_get_authorize_url()
print("Please go to this URL and login: {0}".format(authorize_url))

auth_code = input("Please enter the code you get after login here: ").strip()
token_response = client.oauth2_exchange_code_for_tokens(auth_code)

print(str(token_response.by_resource_server))

globus_auth_data = token_response.by_resource_server["auth.globus.org"]
globus_transfer_data = token_response.by_resource_server["transfer.api.globus.org"]

# Gets tokens

transfer_rt = globus_transfer_data["refresh_token"]
transfer_at = globus_transfer_data["access_token"]
expires_at_s = globus_transfer_data["expires_at_seconds"]

print("Refresh Token")
print(transfer_rt)
print("Access Token")
print(transfer_at)
print("Expires at")
print(expires_at_s)