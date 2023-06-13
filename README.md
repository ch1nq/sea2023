# SEA
See a preview here: https://sea-2023.fly.dev/

## Deploy locally
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


## Deploy to fly.io
Configure the app
```
flyctl launch
```
Attach storage and deploy where `<REGION>` is the same region the configured the app in.
```
flyctl volumes create data --region <REGION> --size 1
flyctl deploy
```

## Test
We use pytest for unit testing. To run tests
```bash
pytest
```
