
PYTHON_SOURCE=$(NAME)-$(VERSION)

$(RPM): | $(PYTHON_SOURCE)
	cd $(PYTHON_SOURCE) && python setup.py bdist_rpm
	cp $(PYTHON_SOURCE)/dist/$(NAME)-$(VERSION)-$(RELEASE).$(ARCH).rpm $(RPM)

clean:
	rm -rf $(PYTHON_SOURCE) $(RPM) 

