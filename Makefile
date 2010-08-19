all:
	@echo "Commands:"
	@echo "  release    prepare source for release"
	@echo "  tgz        build a source tarball"
	@echo "  doc        build API documentation"
	@echo "  dput       build and upload Ubuntu packages"
	@echo "  clean      delete some garbage files"
	@echo "  test       run tests through supported Python implementations"
	@echo "  next-deb   increments debian/VERSION"
	@echo "  next-ppa   increments debian/PPA"

committed:
	hg summary|grep -q '^commit: (clean)$$'

next-deb:
	echo 1 > debian/PPA
	echo $$((1+$$(cat debian/VERSION))) > debian/VERSION

next-ppa:
	echo $$((1+$$(cat debian/PPA))) > debian/PPA

release: committed test doc tgz
	hg tag version-$$(cat VERSION)
	echo 1 > debian/PPA
	echo 1 > debian/VERSION
	hg commit -m "version $$(cat VERSION)"
	hg push

tgz: committed
	hg archive snakes-$$(cat VERSION)-$$(cat debian/VERSION)
	cd snakes-$$(cat VERSION)-$$(cat debian/VERSION) && make doc
	tar cf snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar snakes-$$(cat VERSION)-$$(cat debian/VERSION)
	rm -rf snakes-$$(cat VERSION)-$$(cat debian/VERSION)
	gzip -9 snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar
	gpg --armor --sign --detach-sig snakes-$$(cat VERSION)-$$(cat debian/VERSION).tar.gz

doc: snakes/*.py snakes/plugins/*.py snakes/utils/*.py snakes/compyler/*.py
	make -C doc

dput.sh: VERSION debian/*
	python mkdeb.py

dput: committed dput.sh
	sh dput.sh

clean:
	rm -f $$(find . -name ",*")
	rm -f $$(find . -name "*.pyc")
	rm -f $$(find . -name "*~")
	rm -f $$(find . -name "*.class")

test:
	python2.5 test.py
	python2.6 test.py
	unladen test.py
	pypy test.py
	spypy test.py
	stackless test.py
	jython test.py
