FROM alpine:latest

RUN echo "fs.file-max = 65535" > /etc/sysctl.conf \
    && apk add --update --no-cache nginx nginx-mod-http-fancyindex \
    && sed -i "s/user nginx;/user root;/g" /etc/nginx/nginx.conf \
    && ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log \
    && mkdir /www

WORKDIR /www

COPY file.conf /etc/nginx/http.d/
COPY .theme /usr/share/nginx/theme

EXPOSE 80

ENTRYPOINT ["/usr/sbin/nginx"]
CMD ["-g", "daemon off;"]