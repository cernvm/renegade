
$(RPM): $(SOURCE_TARBALL) $(EXTRA_SOURCES) $(SPEC_FILE)
	rpmbuild --define "%_topdir $(RPMTOP)" --define "%cernvm_epoch $(CERNVM_EPOCH)" -ba $(SPEC_FILE)

clean:
	rm -f \
	  $(SOURCE_TARBALL) $(EXTRA_SOURCES) \
	  $(SPEC_FILE) \
	  $(RPM)
