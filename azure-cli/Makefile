
include $(TOP)/config.mk
include $(TOP)/generic.mk

npm-$(NAME)-$(VERSION): source
	wget -O npm-$(NAME)-$(VERSION).tar.gz `cat source`
	touch npm-$(NAME)-$(VERSION).tar.gz
	mkdir npm-$(NAME)-$(VERSION)
	cd npm-$(NAME)-$(VERSION) && tar xvfz ../npm-$(NAME)-$(VERSION).tar.gz
	rm -f npm-$(NAME)-$(VERSION)/node_modules/azure-storage/node_modules/xml2js/node_modules/sax/examples/switch-bench.js
	rm -f npm-$(NAME)-$(VERSION)/node_modules/azure-common/node_modules/xml2js/node_modules/sax/examples/switch-bench.js
	rm -f npm-$(NAME)-$(VERSION)/node_modules/azure/node_modules/azure-storage/node_modules/xml2js/node_modules/sax/examples/switch-bench.js
	rm -f npm-$(NAME)-$(VERSION)/node_modules/azure-cli/node_modules/azure-storage-legacy/node_modules/azure-common/node_modules/xml2js/node_modules/sax/examples/switch-bench.js
	rm -f npm-$(NAME)-$(VERSION)/azure
	touch npm-$(NAME)-$(VERSION)

include $(TOP)/from-npm.mk

