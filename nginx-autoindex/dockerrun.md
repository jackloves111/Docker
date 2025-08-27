docker run -d \
 --restart=always \
 --name="01-nginx-file" \
 --hostname=nginx-autoindex \
 -p 6008:80 \
 -v /root/vitepress/file.conf:/etc/nginx/http.d/file.conf \
 -v /root/vitepress/file:/www \
nobody114/nginx-fancyindex:latest