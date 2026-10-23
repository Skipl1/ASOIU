# Общая часть: статика клиента, обратное проксирование /api на backend (ТЗ 4.4: Nginx)

add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "same-origin" always;

gzip on;
gzip_types text/css application/javascript application/json image/svg+xml;
client_max_body_size 5m;

root /usr/share/nginx/html;
index index.html;

location /api/ {
    proxy_pass http://grsn_api;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 120s;  # генерация рецепта ожидает ответа модели
}

location /assets/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# SPA: все остальные маршруты отдаёт index.html
location / {
    try_files $uri /index.html;
}
