FROM alpine:latest

RUN echo "fs.file-max = 65535" > /etc/sysctl.conf \
    && apk add --update --no-cache nginx nginx-mod-http-fancyindex \
    && sed -i "s/user nginx;/user root;/g" /etc/nginx/nginx.conf \
    && ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log \
    && rm -rf /etc/nginx/http.d/* \
    && mkdir /www \
    && mkdir -p /usr/share/nginx/.theme

WORKDIR /www

COPY file.conf /etc/nginx/http.d/file.conf
COPY .theme /usr/share/nginx/.theme

EXPOSE 80
VOLUME ["/www"]

CMD ["/usr/sbin/nginx", "-g", "daemon off;"]