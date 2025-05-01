FROM nginx:alpine

# Копируем конфигурационный файл
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем директорию для страниц ошибок
RUN mkdir -p /usr/share/nginx/error

# Копируем страницу с ошибкой
COPY 50x.html /usr/share/nginx/error/50x.html 