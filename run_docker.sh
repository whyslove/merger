docker stop nvr_merger
docker rm nvr_merger
docker build -t nvr_merger .
docker run -idt --name nvr_merger --net=host --env-file ../.env_nvr nvr_merger
