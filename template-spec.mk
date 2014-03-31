
$(SPEC_FILE): $(TOP)/template.spec . | $(RPMTOP)/SPECS
	cat $(TOP)/template.spec | \
	  sed -e "s/^Version: AUTO/Version: $(VERSION)/" | \
	  sed -e "s/^Release: AUTO/Release: $(RELEASE).$(DISTTAG)/" | \
	  sed -e "s/^Name: AUTO/Name: $(NAME)/" | \
	  sed -e "s/^Summary: AUTO/Summary: $(NAME) package/" | \
	  sed -e "s/^BuildArch: AUTO/BuildArch: $(ARCH)/" | \
	  sed -f $(TOP)/files.sed \
	  > $(SPEC_FILE)~
	if [ -f description ]; then sed -i -f $(TOP)/description.sed $(SPEC_FILE)~; else sed -i -e "/^AUTODESC/d" $(SPEC_FILE)~; fi
	if [ -f extradepends ]; then sed -i -f $(TOP)/extradepends.sed $(SPEC_FILE)~; else sed -i -e "/^EXTRADEPENDS/d" $(SPEC_FILE)~; fi
	if [ -f extraprovides ]; then sed -i -f $(TOP)/extraprovides.sed $(SPEC_FILE)~; else sed -i -e "/^EXTRAPROVIDES/d" $(SPEC_FILE)~; fi
	if [ -f nodeps ]; then sed -i -e "s/^AUTODEPS/AutoReqProv: no/" $(SPEC_FILE)~; else sed -i -e "/^AUTODEPS/d" $(SPEC_FILE)~; fi
	mv $(SPEC_FILE)~ $(SPEC_FILE)
