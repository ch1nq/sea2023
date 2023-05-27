FROM node:16-alpine as builder

# Install TypeScript
RUN npm install -g typescript

# Compile typescript
COPY script.ts .
RUN tsc script.ts --outDir ./dist --target ES6

FROM python:3.11-slim-buster

# Install python dependencies
WORKDIR /python-docker
RUN pip3 install pip --upgrade
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copy python source
COPY static static
COPY templates templates
COPY src src

# Copy compiled typescript
RUN mkdir -p static/js
COPY --from=builder /dist ./static/js

# Create models directory
RUN mkdir models 
COPY models models

CMD [ "python3", "-m" , "gunicorn", "src.server:app", "-b=0.0.0.0:5000"]
