# syntax=docker/dockerfile:1
# Landing page — static HTML served by nginx

FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY landing-nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/
COPY images/ /usr/share/nginx/html/images/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
