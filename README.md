# SpartyTime
SpartyTime is a replacement of the Spotify's Jam system made using FastAPI to make listening with friends on Spotify easier! SpartyTime uses the [Spotify OAuth](https://developer.spotify.com/documentation/web-api/) to connect the users. Users can create parties and invite their friends to join the party.

## Features
- Party Queue and History is available.
- Genre matching to allow users to join others with matching music taste!
- Website doesn't need to stay open!
- Works on mobile too.

## Requirements
- Python 3.10+
- Spotify Premium

## Installation
Clone the repository:
```sh
git clone https://github.com/SockYeh/SpartyTime
```

To install necessary dependencies, run the following commands:
```sh
pip install -r requirements.txt
```
## Setup
- Create a [MongoDB](https://www.mongodb.com/) database and copy the connection string.
- Create a Spotify Developer Application with a callback url and copy the Client ID and Client Secret.
- Create a secret key.
- Add them to the [.env](.env) file and save.

## Usage
To run the code use the command
```python
uvicorn spartytime.backend.main:app --reload
```
To create the database schema, make a request to the root `/` endpoint.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
