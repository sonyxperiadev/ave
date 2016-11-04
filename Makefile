# Makefile for AVE

PWD := $(shell pwd)

PIP := $(shell which pip)
ifeq ($(wildcard $(PIP)),)
  $(error pip must be available)
endif

# You can set these variables from the command line.
GH_PAGES_SOURCES = broker common documentation gerrit handset relay utils vcsjob workspace Makefile

all: sdist

sdist:
	python setup.py sdist

build:
	python setup.py build

install:
	python setup.py install

install-requires: sdist
	pip install -r ave.egg-info/requires.txt

install-all: install-requires install

debian:
	./mkdeb

gh-pages:
	git reset --soft github/gh-pages || \
	(git remote add github git@github.com:sonyxperiadev/ave.git && \
	git fetch github) && git reset --soft github/gh-pages # gh-pages already exists
	cd documentation && \
	make html && \
	cd $(PWD) && \
	mv documentation/_build/html ./ && \
	rm -rf $(GH_PAGES_SOURCES) && \
	rsync -a ./html/ ./ && \
	rm -rf ./html
	touch .nojekyll
	git add -A && \
	git commit -m \
	"Generated gh-pages for `git log master -1 --pretty=short --abbrev-commit`" \
	&& git push --dry-run github HEAD:refs/heads/gh-pages && \
	echo "Push the branch by git push github HEAD:refs/heads/gh-pages"

clean:
	rm -rf build
	rm -rf ave.egg-info/
	rm -rf common/src/ave/apk.py
	rm -rf common/src/ave/ftpclient.py
	rm -rf common/src/ave/git.py
	rm -rf common/src/ave/jenkins.py
	rm -rf common/src/ave/workspace.py
	rm -rf dist
	rm -rf common/src/ave/base_workspace.py
	git checkout *__init__.py
