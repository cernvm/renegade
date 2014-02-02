
PYTHON_SOURCE=$(NAME)-$(VERSION)
PYTHON_INST_SCRIPT=$(shell if [ -f custom_install ]; then echo '--install-script custom_install'; fi)

$(RPM): | $(PYTHON_SOURCE)
	cd $(PYTHON_SOURCE) && python setup.py bdist_rpm --release $(RELEASE) $(PYTHON_INST_SCRIPT)
	cp $(PYTHON_SOURCE)/dist/$(NAME)-$(VERSION)-$(RELEASE).$(ARCH).rpm $(RPM) 

clean:
	rm -rf $(PYTHON_SOURCE) $(RPM) 

