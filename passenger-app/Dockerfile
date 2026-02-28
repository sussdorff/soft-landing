# syntax=docker/dockerfile:1
# Passenger App Dockerfile — serve pre-built WASM/JS output with nginx
#
# The WASM build happens locally (./gradlew :composeApp:wasmJsBrowserDistribution)
# and this Dockerfile just packages the static output into an nginx image.

FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY composeApp/build/dist/wasmJs/productionExecutable /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
