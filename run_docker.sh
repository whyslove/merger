docker stop nvr_merger
docker rm nvr_merger
docker build -t nvr_merger .
docker run -d \
 -it \
 --name nvr_merger \
 --net=host \
 --env-file ../.env_nvr \
 -v $HOME/creds:/merger/creds \
 nvr_merger
