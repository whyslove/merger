docker stop merger
docker rm merger
docker build -t merger .
docker run -d \
 -it \
 --restart on-failure \
 --name merger \
 --net=host \
 --env-file ./.env \
 -v $HOME/creds:/merger/creds \
 -v /var/log/merger:/var/log/merger \
 merger
