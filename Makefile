.PHONY: docker-lint docker-build docker-run clean build run

docker-lint:
    docker run --rm -i hadolint/hadolint < Dockerfile

docker-build:
    docker buildx build -t stockyard:latest .

docker-run: docker-build
    docker run -it --rm --env-file ./.env stockyard:latest

clean:
    docker system prune -af --volumes
    docker builder prune -af

build: docker-build

run: docker-run
