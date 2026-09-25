# ThunderAPI  
ThunderAPI is an API that interfaces with Gaijin's backend used by War Thunder, [warthunder.com](https://warthunder.com/), and the [Gaijin marketplace](https://trade.gaijin.net/).  
It handles the authentication and token refreshing automatically, so the user only has to worry about a single ThunderAPI token.  
> [!IMPORTANT]  
> Due to unused token cleanup, tokens are cleared after 24 hours of inactivity, so tokens have to be used at least once per day, to be kept active.  
> This can be done by calling any endpoint or the dedicated `/v1/refresh-token` endpoint.  
> Refreshing is handled internally, so your existing ThunderAPI token remains valid afterward.  

The API also handles the conversion from Gaijin's compressed binary `BLK` format into usable JSON.  

> [!WARNING]  
> ThunderAPI is an unofficial project and is not affiliated with or endorsed by Gaijin Entertainment.  

## About  
This project is meant to be a spiritual successor to [Thunderinsights](https://github.com/djandDK/thunderinsights).  
After it was completely shut down around May 2026, I decided to continue this API and make it something even better.  
The Thunderinsights source code was used as a reference for some endpoints in the beginning. However, the majority of the endpoint logic was reverse-engineered using [HTTP Toolkit](https://httptoolkit.com/), Firefox DevTools, and my custom scripts (found in the `manual_extract` directory) that converted the raw hex to readable JSON.  

This API uses a different design philosophy from `Thunderinsights`: each user authenticates using their own Gaijin account. This allows the API to support functionality that the original project could not, including squadron management, marketplace access, and replay searching.  

Automatically generated API documentation is available at `/docs` (by default, `http://127.0.0.1:8001/docs`).  

## Authentication  
Almost all endpoints outside of the `Authentication` category require an `Authorization: Bearer` header to be sent alongside the request, using a valid token obtained from `/v1/login`.  
Example:  
```bash  
curl -X GET \  
	'http://127.0.0.1:8001/v1/clans/1061551/applicants' \  
	-H 'accept: application/json' \  
	-H 'Authorization: Bearer YOUR_THUNDERAPI_TOKEN'  
```  
### Limitations  
Currently, two-step authentication has only been tested using Gaijin Pass.  
If you use other forms of 2FA, logging in might not work properly.  

## Hosting  
Feel free to host this for yourself, if you feel up to the task. Otherwise the API can also be used through `[PLACEHOLDER]`.  
Setup instructions can be found in the [Self-hosting](#self-hosting) section.  

## Features  
- Squadron management  
- Marketplace access  
- Replay searching and parsing  
- Player lookup  
- Squadron lookup  
- News and changelogs feed  
- Vehicle lookup *(in development)*  

## Privacy Policy  
ThunderAPI stores some security-sensitive account data, including Gaijin session tokens, because they are required to interact with Gaijin's services.  

> [!IMPORTANT]  
> A ThunderAPI instance handles authentication credentials and session tokens on your behalf.  
> Only use instances operated by someone you trust.  
> Self-hosting is recommended if you do not want to provide account credentials to a third-party ThunderAPI operator.  

> [!WARNING]  
> ThunderAPI is a FOSS project, and anyone can modify or redistribute their own version.  
> Third-party ThunderAPI instances may therefore run modified code and should only be used if you trust their operator.  

Your password, however, is never stored. It is used temporarily for operations that require it and is immediately discarded afterward.  
As a result, operations that require an `identity_sid`, for example, require the user to re-enter their account password.  

The following data is stored about the user:  
- A hash of the randomly generated authentication token  
- Email address  
- Session token (needed for use on Gaijin's end), and its expiration date  
- User token (needed for token refreshing)  
- UID (the ID found at https://store.gaijin.net/user.php, needed for use on Gaijin's end)  
- Request count (for statistics and for monitoring abuse)  
- Last used time (used for automatic refreshing of the user's token)  
- Creation timestamp (the time of creation of the user's entry)  
  
The official ThunderAPI instance does not sell or share your personal data with third parties.  

## Self-hosting  
### Prerequisites  
- Python 3.14  
- `wt_ext_cli` binary (if not in the `tools` folder, specify its path in the `.env`)  
- `binBlk` binary (if not in the `tools` folder, specify its path in the `.env`)  
### Setup  
1. Clone the repo  
```bash  
git clone https://github.com/Order-Of-The-Birb/ThunderAPI.git  
```  
2. Move into the repository directory  
```bash  
cd ./ThunderAPI  
```  
3. Make a `.env`  
```bash  
cp ./.example.env ./.env  
```  
4. Edit the `.env` to fit your needs  
5. Add execution permissions, if needed  
```bash  
chmod +x ./run ./setup  
```  
6. Run the `setup` script - This sets up the Python virtual environment (`.venv`)  
```bash  
./setup  
```  
7. Start the server by using the `run` script  
```bash  
./run  
```  

## Contributions  
Contributions are welcome.  
Pull requests that improve ThunderAPI without breaking existing functionality are encouraged  

## License  

ThunderAPI is licensed under the Apache License 2.0.  
See the [LICENSE](LICENSE) file for details.  
