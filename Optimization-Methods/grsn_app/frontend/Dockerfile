# Сборка клиентской части
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

# Nginx: раздача статики, обратное проксирование /api, HTTP или HTTPS
FROM nginx:1.27-alpine
RUN apk add --no-cache openssl
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/app.inc nginx/http.conf nginx/https.conf /etc/nginx/grsn/
COPY nginx/10-select-config.sh /docker-entrypoint.d/10-select-config.sh
RUN chmod +x /docker-entrypoint.d/10-select-config.sh
EXPOSE 80 443
