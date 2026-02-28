# syntax=docker/dockerfile:1
# Docs Dockerfile — build MkDocs site, serve with nginx

# ---------- Stage 1: build ----------
FROM python:3.12-slim AS build

WORKDIR /docs

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mkdocs.yml .
COPY content/ content/

RUN mkdocs build

# ---------- Stage 2: serve ----------
FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY docs-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /docs/site /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
