FROM node as builder

# Install TypeScript
RUN npm install -g typescript

# Compile typescript
WORKDIR /app
COPY script.ts script.ts
RUN tsc script.ts --outDir ./dist --target ES6

FROM python:3.11-slim-buster

# Install python dependencies
WORKDIR /python-docker
RUN pip3 install pip --upgrade
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copy python source
COPY src src
COPY templates templates
COPY static static

# Copy compiled typescript
RUN mkdir -p static/js
COPY --from=builder /app/dist ./static/js

# Create models directory
RUN mkdir models 

CMD [ "python3", "-m" , "gunicorn", "src.server:app", "-b=0.0.0.0:5000", "-w=4"]
