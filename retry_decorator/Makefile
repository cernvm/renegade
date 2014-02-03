
include $(TOP)/config.mk

$(NAME)-$(VERSION):
	wget https://pypi.python.org/packages/source/r/retry_decorator/retry_decorator-1.0.0.tar.gz --no-check-certificate
	tar xvfz $(NAME)-$(VERSION).tar.gz

include $(TOP)/from-python.mk

