docker run -d \
 --restart=always \
 --name="01-nginx-file" \
 -p 6008:80 \
 # -v /已经预设:/etc/nginx/http.d/file.conf \
 -v /path/to/your/www:/www \
nobody114/nginx-fancyindex:latest