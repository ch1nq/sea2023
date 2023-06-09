# SEA


## Deploy
```bash
docker build . -t sea2023
docker run --name sea2023 -d -p=5000:5000 sea2023:latest
```
The application is now running on http://0.0.0.0:5000

### Stop server
```bash
docker stop sea2023
docker rm sea2023
```


## Develop
```bash
pip install -r requirements.txt
brew install typescript
mkdir models
```

Then run the following in one terminal
```
python main.py
```
in another terminal
```
tsc --watch script.ts --outFile static/js/script.js --target ESNext
```

## Test
We use oytest for unit testing. To run tests
```bash
pytest
```
