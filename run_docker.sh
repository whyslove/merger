docker stop nvr_merger
docker rm nvr_merger
docker build -t nvr_merger .
docker run -idt --name nvr_merger --net=host --env-file ../.env_nvr -v /home/recorder/creds:/merger/creds nvr_merger
