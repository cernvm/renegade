
include $(TOP)/config.mk

$(NAME)-$(VERSION):
	wget -O $(VERSION).zip https://github.com/hep-gc/$(NAME)/archive/$(VERSION).zip
	unzip $(VERSION).zip

include $(TOP)/from-python.mk

