FROM node:16-alpine as builder

# Install TypeScript
RUN npm install -g typescript

# Compile typescript
COPY script.ts .
RUN tsc script.ts --outDir ./dist --target ESNext 

FROM python:3.11-slim-buster

# Install and configure supervisor and NGINX
RUN apt-get update && apt-get install -y supervisor nginx
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Configure NGINX
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Install python dependencies
RUN pip3 install pip --upgrade
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# Copy python source
COPY static static
COPY templates templates
COPY src src
COPY main_ws.py .

# Copy compiled typescript
RUN mkdir -p static/js
COPY --from=builder /dist ./static/js

# Create models directory
RUN mkdir data
RUN mkdir data/models 
COPY models data/models

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
