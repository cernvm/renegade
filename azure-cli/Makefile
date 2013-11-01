
include $(TOP)/config.mk
include $(TOP)/generic.mk

npm-$(NAME)-$(VERSION): source
	wget -O npm-$(NAME)-$(VERSION).tar.gz `cat source`
	touch npm-$(NAME)-$(VERSION).tar.gz
	mkdir npm-$(NAME)-$(VERSION)
	cd npm-$(NAME)-$(VERSION) && tar xvfz ../npm-$(NAME)-$(VERSION).tar.gz
	touch npm-$(NAME)-$(VERSION)

include $(TOP)/from-npm.mk

