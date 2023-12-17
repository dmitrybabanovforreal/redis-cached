# Running the tests

I use [poetry](https://python-poetry.org) to handle dependencies, so you have to use it too if you want to contribute to the project.

```shell
# install the dependencies, if you haven't before
poetry install --with test

# launch a KeyDB instance
docker run --name keydb -p 6379:6379 -d eqalpha/keydb:latest keydb-server /etc/keydb/keydb.conf --bind "0.0.0.0" --protected-mode "no" --port "6379"

# run the tests (replace zsh to sh if you are on Linux)
zsh -f ./maintenance/test.sh
```
