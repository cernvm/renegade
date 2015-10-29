
include $(TOP)/config.mk

EXTRA_SOURCES = prepared

CCTOOLS_NAME = $(NAME)-$(VERSION)-$(HOSTARCH)-redhat$(UPSTREAM_VERSION)

dist:
	mkdir -p dist

prepared: version release | $(CCTOOLS_NAME) dist
	rm -rf dist/* dist/.prepared
	mkdir -p dist/usr/share/doc dist/usr/include
	cp -av $(CCTOOLS_NAME)/bin dist/usr/
	cp -av $(CCTOOLS_NAME)/lib dist/usr/lib64
	mv dist/usr/lib64/lib64/* dist/usr/lib64/
	rmdir dist/usr/lib64/lib64
	cp -av $(CCTOOLS_NAME)/doc dist/usr/share/doc/$(NAME)-$(VERSION)
	cp -av $(CCTOOLS_NAME)/include/cctools dist/usr/include
	cp -av $(CCTOOLS_NAME)/share/cctools dist/usr/share/
	cp -av $(CCTOOLS_NAME)/share/man dist/usr/share/
	touch prepared

$(CCTOOLS_NAME): $(CCTOOLS_NAME).tar.gz
	tar xvfz $(CCTOOLS_NAME).tar.gz
	touch $(CCTOOLS_NAME)

$(CCTOOLS_NAME).tar.gz:
	curl http://ccl.cse.nd.edu/software/files/$(CCTOOLS_NAME).tar.gz > $(CCTOOLS_NAME).tar.gz

include $(TOP)/generic.mk
include $(TOP)/template-spec.mk
include $(TOP)/from-svn.mk
