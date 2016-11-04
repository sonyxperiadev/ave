# Makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
BUILDDIR      = _build

# Internal variables.
ALLSPHINXOPTS = -d $(BUILDDIR)/doctrees $(SPHINXOPTS) .

html: check_symlinks
	sphinx-apidoc -f -o source .
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) $(BUILDDIR)/html
	chmod -R g+w $(BUILDDIR)/html

check_symlinks:
	@if [ ! -d "../broker" ]; then \
		echo "ERROR: broker symlink is broken"; \
		exit 1; \
	fi
	@if [ ! -d "../common" ]; then \
		echo "ERROR: common symlink is broken"; \
		exit 1; \
	fi
	@if [ ! -d "../handset" ]; then \
		echo "ERROR: handset symlink is broken"; \
		exit 1; \
	fi
	@if [ ! -d "../relay" ]; then \
		echo "ERROR: relay symlink is broken"; \
		exit 1; \
	fi
	@if [ ! -d "../utils" ]; then \
		echo "ERROR: utils symlink is broken"; \
		exit 1; \
	fi
	@if [ ! -d "../vcsjob" ]; then \
		echo "ERROR: vcsjob symlink is broken"; \
		exit 1; \
	fi
	@if [ ! -d "../workspace" ]; then \
		echo "ERROR: workspace symlink is broken"; \
		exit 1; \
	fi

clean:
	-rm -rf $(BUILDDIR)/*
