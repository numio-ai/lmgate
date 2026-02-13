FROM nginx:alpine

RUN apk add --no-cache nginx-module-njs

COPY nginx.conf /etc/nginx/nginx.conf
COPY scripts/ /etc/nginx/scripts/

EXPOSE 80
